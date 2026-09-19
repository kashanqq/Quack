"""T07–T09, T27 against a live Postgres: the intent outlives the process.

These are the tests that actually prove D01. A unit test can show that the
wrapper calls the right repository function; only a real transaction shows
that the intent is committed together with the event, that the partial unique
index refuses a second live copy of the same job, and that `claim_due`
reclaims a lease whose owner never came back.
"""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.config import Settings
from app.db.engine import close_engine, create_engine, create_sessionmaker
from app.db.models import JobOutbox
from app.db.repo import outbox as outbox_repo
from app.events.outbox import LEASE_S, OUTBOX_ID_KEY
from app.events.outbox import JobOutbox as Outbox

pytestmark = [pytest.mark.integration, pytest.mark.phase5]


@pytest.fixture
async def sessionmaker():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required")
    engine = create_engine(Settings(ENV="local", DATABASE_URL=url))
    try:
        yield create_sessionmaker(engine)
    finally:
        await close_engine(engine)


@pytest.fixture
async def clean(sessionmaker):
    """Only the rows this module writes; a shared test database is shared."""
    prefix = f"phase5-{uuid4().hex[:8]}"
    yield prefix
    async with sessionmaker() as session:
        await session.execute(
            delete(JobOutbox).where(JobOutbox.job_id.like(f"{prefix}%"))
        )
        await session.commit()


class _Arq:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[tuple] = []
        self.fail = fail

    async def enqueue_job(self, fn_name, **kwargs):
        if self.fail:
            raise ConnectionError("redis is down")
        self.calls.append((fn_name, kwargs))
        return type("Job", (), {"job_id": kwargs.get("_job_id")})()


async def _row(sessionmaker, intent_id: int) -> JobOutbox:
    async with sessionmaker() as session:
        row = await session.get(JobOutbox, intent_id)
        assert row is not None
        return row


async def test_t07_a_crash_between_commit_and_enqueue_does_not_lose_the_job(
    sessionmaker, clean
):
    """Коммит прошёл, доставка — нет. Строка на месте, replay её заберёт."""
    outbox = Outbox()
    outbox.enqueue("bulk", "soft_match", job_id=f"{clean}-softmatch", student_id="s")
    async with sessionmaker() as session:
        assert await outbox.persist(session) == 1
        await session.commit()
    # Здесь процесс «умирает»: deliver не вызывается вовсе.
    [entry] = outbox.ready
    row = await _row(sessionmaker, entry.intent_id)
    assert row.status == "pending"
    assert row.enqueued_at is None

    # Следующий replay видит строку как due и доставляет её.
    async with sessionmaker() as session:
        claimed = await outbox_repo.claim_due(session, datetime.now(UTC), limit=50)
        await session.commit()
    assert entry.intent_id in {intent.id for intent in claimed}


async def test_a_delivered_intent_is_marked_enqueued_with_a_lease(sessionmaker, clean):
    outbox = Outbox()
    outbox.enqueue("bulk", "soft_match", job_id=f"{clean}-deliver", student_id="s")
    arq = _Arq()
    async with sessionmaker() as session:
        await outbox.persist(session)
        await session.commit()
    [entry] = list(outbox.ready)
    assert await outbox.deliver(sessionmaker, arq) == 1

    row = await _row(sessionmaker, entry.intent_id)
    assert row.status == "enqueued"
    assert row.enqueued_at is not None
    assert row.lease_until is not None
    assert row.lease_until > datetime.now(UTC) + timedelta(seconds=LEASE_S - 60)
    [(fn_name, kwargs)] = arq.calls
    assert fn_name == "soft_match"
    assert kwargs[OUTBOX_ID_KEY] == entry.intent_id


async def test_a_redis_refusal_leaves_the_row_claimable(sessionmaker, clean):
    outbox = Outbox()
    outbox.enqueue("bulk", "soft_match", job_id=f"{clean}-refused", student_id="s")
    async with sessionmaker() as session:
        await outbox.persist(session)
        await session.commit()
    [entry] = list(outbox.ready)
    assert await outbox.deliver(sessionmaker, _Arq(fail=True)) == 0

    row = await _row(sessionmaker, entry.intent_id)
    assert row.status == "pending"
    assert row.enqueued_at is None


async def test_only_one_live_intent_per_logical_job(sessionmaker, clean):
    """Партиальный UNIQUE — настоящая защита от второй копии задачи (§9.2)."""
    job_id = f"{clean}-once"
    first = Outbox()
    first.enqueue("bulk", "recommendations_batch", job_id=job_id, student_id="s")
    async with sessionmaker() as session:
        assert await first.persist(session) == 1
        await session.commit()

    second = Outbox()
    second.enqueue("bulk", "recommendations_batch", job_id=job_id, student_id="s")
    async with sessionmaker() as session:
        assert await second.persist(session) == 0
        await session.commit()

    async with sessionmaker() as session:
        rows = (
            await session.scalars(select(JobOutbox).where(JobOutbox.job_id == job_id))
        ).all()
    assert len(rows) == 1


async def test_a_finished_job_does_not_block_tomorrows_batch(sessionmaker, clean):
    """Завершённая строка не держит ключ: суточный батч должен повториться."""
    job_id = f"{clean}-daily"
    outbox = Outbox()
    outbox.enqueue("bulk", "recommendations_batch", job_id=job_id, student_id="s")
    async with sessionmaker() as session:
        await outbox.persist(session)
        await session.commit()
    [entry] = list(outbox.ready)
    async with sessionmaker() as session:
        await outbox_repo.mark_done(
            session, entry.intent_id, lease_token=None, now=datetime.now(UTC)
        )
        await session.commit()

    again = Outbox()
    again.enqueue("bulk", "recommendations_batch", job_id=job_id, student_id="s")
    async with sessionmaker() as session:
        assert await again.persist(session) == 1
        await session.commit()


async def test_t08_an_expired_lease_is_reclaimed_and_the_old_owner_is_fenced(
    sessionmaker, clean
):
    """Токен меняется только вместе с состоявшейся доставкой.

    Пока новой доставки нет, старый воркер — единственный владелец и имеет
    право дописать результат. Как только replay отдал задачу заново, прежний
    токен перестаёт подходить (§15).
    """
    outbox = Outbox()
    outbox.enqueue("bulk", "soft_match", job_id=f"{clean}-lease", student_id="s")
    async with sessionmaker() as session:
        await outbox.persist(session)
        await session.commit()
    [entry] = list(outbox.ready)
    past = datetime.now(UTC) - timedelta(minutes=5)
    async with sessionmaker() as session:
        await outbox_repo.mark_enqueued(session, entry.intent_id, lease_s=1, now=past)
        await session.commit()

    async with sessionmaker() as session:
        claimed = await outbox_repo.claim_due(session, datetime.now(UTC), limit=50)
        await session.commit()
    reclaimed = next(item for item in claimed if item.id == entry.intent_id)
    # Сам по себе claim токен не крутит: доставки ещё не было.
    assert reclaimed.lease_token == entry.lease_token

    # Повторная доставка принята — и вот теперь владелец сменился.
    new_token = uuid4()
    async with sessionmaker() as session:
        await outbox_repo.mark_enqueued(
            session,
            entry.intent_id,
            lease_s=60,
            now=datetime.now(UTC),
            lease_token=new_token,
        )
        await session.commit()

    async with sessionmaker() as session:
        assert (
            await outbox_repo.mark_started(
                session,
                entry.intent_id,
                lease_token=entry.lease_token,
                lease_s=60,
                now=datetime.now(UTC),
            )
            is False
        )
        assert (
            await outbox_repo.mark_started(
                session,
                entry.intent_id,
                lease_token=new_token,
                lease_s=60,
                now=datetime.now(UTC),
            )
            is True
        )
        await session.commit()


async def test_a_duplicate_arq_job_is_not_counted_as_delivered(sessionmaker, clean):
    """`enqueue_job` вернул None — работа не поставлена, строка остаётся due."""

    class _Busy:
        async def enqueue_job(self, _fn_name, **_kwargs):
            return None  # ARQ уже держит этот job_id

    outbox = Outbox()
    outbox.enqueue("bulk", "soft_match", job_id=f"{clean}-busy", student_id="s")
    async with sessionmaker() as session:
        await outbox.persist(session)
        await session.commit()
    [entry] = list(outbox.ready)
    assert await outbox.deliver(sessionmaker, _Busy()) == 0

    row = await _row(sessionmaker, entry.intent_id)
    assert row.status == "pending"
    assert row.enqueued_at is None


async def test_an_outage_never_spends_an_attempt(sessionmaker, clean):
    outbox = Outbox()
    outbox.enqueue("bulk", "pregenerate_set", job_id=f"{clean}-wait", student_id="s")
    async with sessionmaker() as session:
        await outbox.persist(session)
        await session.commit()
    [entry] = list(outbox.ready)

    for _ in range(5):
        async with sessionmaker() as session:
            await outbox_repo.mark_waiting(
                session,
                entry.intent_id,
                lease_token=None,
                dependency="llm",
                defer_s=120,
                now=datetime.now(UTC),
            )
            await session.commit()

    row = await _row(sessionmaker, entry.intent_id)
    assert row.status == "waiting_dependency"
    assert row.dependency == "llm"
    assert row.attempts == 0
    assert row.last_error_code == "llm_unavailable"


async def test_t27_a_poison_job_ends_as_failed_and_stays_visible(sessionmaker, clean):
    outbox = Outbox()
    outbox.enqueue("bulk", "extract_program", job_id=f"{clean}-poison", url="u")
    async with sessionmaker() as session:
        await outbox.persist(session)
        await session.commit()
    [entry] = list(outbox.ready)

    async with sessionmaker() as session:
        assert (
            await outbox_repo.mark_retry(
                session,
                entry.intent_id,
                lease_token=None,
                error_code="ValueError",
                defer_s=30,
                now=datetime.now(UTC),
            )
            == 1
        )
        await outbox_repo.mark_failed(
            session,
            entry.intent_id,
            lease_token=None,
            error_code="ValueError",
            now=datetime.now(UTC),
        )
        await session.commit()

    row = await _row(sessionmaker, entry.intent_id)
    assert row.status == "failed"
    assert row.attempts == 2
    assert row.last_error_code == "ValueError"
    # Не исчезла и не притворилась успешной: оператор её видит.
    async with sessionmaker() as session:
        active = await outbox_repo.backlog(session)
    assert all(status != "failed" for status, *_ in active)
