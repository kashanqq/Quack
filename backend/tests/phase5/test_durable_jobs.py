"""T06–T09, T20: an outage must cost time, not work (§13.1, AC03)."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from arq import Retry

from app.db.repo import outbox as outbox_repo
from app.errors import LLMUnavailable, SearchUnavailable
from app.events.outbox import LEASE_TOKEN_KEY, OUTBOX_ID_KEY
from app.workers.durable import RETRY_BACKOFF_S, durable

pytestmark = pytest.mark.phase5


class _Row:
    """One `job_outbox` row, as far as the wrapper is concerned."""

    def __init__(self) -> None:
        self.id = 1
        self.status = "enqueued"
        self.dependency: str | None = None
        self.attempts = 0
        self.not_before = datetime.now(UTC)
        self.lease_until: datetime | None = None
        self.lease_token = uuid4()
        self.last_error_code: str | None = None


class _Sessionmaker:
    """Records what the wrapper wrote, without a database."""

    def __init__(self, row: _Row) -> None:
        self.row = row

    def __call__(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None


@pytest.fixture
def row_and_ctx(monkeypatch):
    row = _Row()

    async def mark_started(_session, _id, *, lease_token, lease_s, now):
        if lease_token not in (None, row.lease_token):
            return False
        row.status = "running"
        row.lease_until = now + timedelta(seconds=lease_s)
        return True

    async def mark_done(_session, _id, *, lease_token, now):
        row.status = "succeeded"
        row.lease_until = None

    async def mark_waiting(_session, _id, *, lease_token, dependency, defer_s, now):
        row.status = "waiting_dependency"
        row.dependency = dependency
        row.not_before = now + timedelta(seconds=defer_s)

    async def mark_deferred(_session, _id, *, lease_token, defer_s, now):
        row.status = "pending"
        row.dependency = None
        row.not_before = now + timedelta(seconds=defer_s)

    async def mark_retry(_session, _id, *, lease_token, error_code, defer_s, now):
        row.status = "pending"
        row.attempts += 1
        row.last_error_code = error_code
        row.not_before = now + timedelta(seconds=defer_s)
        return row.attempts

    async def mark_failed(_session, _id, *, lease_token, error_code, now):
        row.status = "failed"
        row.attempts += 1
        row.last_error_code = error_code

    async def get(_session, _id):
        return outbox_repo.Intent(
            id=row.id,
            queue="bulk",
            fn_name="pregenerate_set",
            job_id="pregen:1",
            kwargs={},
            defer_by=0,
            status=row.status,
            dependency=row.dependency,
            attempts=row.attempts,
            lease_token=row.lease_token,
        )

    for name, fn in (
        ("mark_started", mark_started),
        ("mark_done", mark_done),
        ("mark_waiting", mark_waiting),
        ("mark_deferred", mark_deferred),
        ("mark_retry", mark_retry),
        ("mark_failed", mark_failed),
        ("get", get),
    ):
        monkeypatch.setattr(outbox_repo, name, fn)
    return row, {"sessionmaker": _Sessionmaker(row)}


def _meta(row: _Row) -> dict[str, Any]:
    return {OUTBOX_ID_KEY: row.id, LEASE_TOKEN_KEY: str(row.lease_token)}


async def test_a_successful_job_closes_its_intent(row_and_ctx):
    row, ctx = row_and_ctx
    seen: list[dict] = []

    async def job(_ctx, **kwargs):
        seen.append(kwargs)

    await durable(job, name="pregenerate_set", max_tries=3)(
        ctx, request_id="r", set_id="s", **_meta(row)
    )
    assert row.status == "succeeded"
    # Транспортные ключи сняты: генератор видит прежние доменные kwargs (§23).
    assert seen == [{"request_id": "r", "set_id": "s"}]


@pytest.mark.parametrize(
    ("error", "dependency"),
    [
        (LLMUnavailable("llm down"), "llm"),
        (SearchUnavailable("both providers down"), "search"),
    ],
)
async def test_t06_an_outage_parks_the_job_without_spending_an_attempt(
    row_and_ctx, error, dependency
):
    row, ctx = row_and_ctx

    async def job(_ctx, **_kwargs):
        raise Retry(defer=120) from error

    with pytest.raises(Retry):
        await durable(job, name="pregenerate_set", max_tries=3)(ctx, **_meta(row))
    assert row.status == "waiting_dependency"
    assert row.dependency == dependency
    assert row.attempts == 0


async def test_t09_an_outage_longer_than_the_retry_budget_keeps_the_work(row_and_ctx):
    """Три доставки подряд при лежащей модели не расходуют ни одной попытки."""
    row, ctx = row_and_ctx

    async def job(_ctx, **_kwargs):
        raise Retry(defer=120) from LLMUnavailable("llm down")

    wrapped = durable(job, name="pregenerate_set", max_tries=3)
    for _ in range(3):
        row.status = "enqueued"
        with pytest.raises(Retry):
            await wrapped(ctx, **_meta(row))
    assert row.attempts == 0
    assert row.status == "waiting_dependency"


async def test_a_bare_retry_only_moves_the_clock(row_and_ctx):
    """Занятый lock — не отказ зависимости и не провал задачи."""
    row, ctx = row_and_ctx

    async def job(_ctx, **_kwargs):
        raise Retry(defer=10) from None

    with pytest.raises(Retry):
        await durable(job, name="recommendations_batch", max_tries=3)(ctx, **_meta(row))
    assert (row.status, row.dependency, row.attempts) == ("pending", None, 0)


async def test_a_real_failure_backs_off_then_gives_up(row_and_ctx):
    row, ctx = row_and_ctx

    async def job(_ctx, **_kwargs):
        raise ValueError("bad template")

    wrapped = durable(job, name="pregenerate_set", max_tries=3)
    for attempt in range(2):
        row.status = "enqueued"
        with pytest.raises(ValueError):
            await wrapped(ctx, **_meta(row))
        assert row.status == "pending"
        assert row.attempts == attempt + 1
        assert row.not_before > datetime.now(UTC) + timedelta(
            seconds=RETRY_BACKOFF_S[min(attempt, len(RETRY_BACKOFF_S) - 1)] - 5
        )
    row.status = "enqueued"
    with pytest.raises(ValueError):
        await wrapped(ctx, **_meta(row))
    assert row.status == "failed"
    assert row.last_error_code == "ValueError"


async def test_a_stale_lease_cannot_overwrite_the_new_owner(row_and_ctx):
    """T08/§15: поздний воркер прежнего владельца не трогает чужую строку."""
    row, ctx = row_and_ctx
    ran = []

    async def job(_ctx, **_kwargs):
        ran.append(1)

    stale = {OUTBOX_ID_KEY: row.id, LEASE_TOKEN_KEY: str(uuid4())}
    await durable(job, name="pregenerate_set", max_tries=3)(ctx, **stale)
    assert ran == []
    assert row.status == "enqueued"


async def test_a_cron_run_without_an_intent_still_works(row_and_ctx):
    _row, ctx = row_and_ctx
    ran = []

    async def job(_ctx, **kwargs):
        ran.append(kwargs)

    await durable(job, name="outbox_replay", max_tries=1)(ctx, request_id="cron")
    assert ran == [{"request_id": "cron"}]
