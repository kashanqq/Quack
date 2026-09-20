"""The job outbox — §13.3 `test_outbox.py`."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.events.outbox import JobOutbox, OutboxEntry

pytestmark = pytest.mark.phase4


class _Recorder:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[tuple] = []
        self.fail = fail

    async def enqueue_job(self, fn_name, **kwargs):
        if self.fail:
            raise ConnectionError("redis is down")
        self.calls.append((fn_name, kwargs))
        return SimpleNamespace(job_id=kwargs.get("_job_id"))


class _Session:
    """Enough of an `AsyncSession` for `outbox_repo.record` to write a row."""

    def __init__(self) -> None:
        self.added: list = []
        self.commits = 0
        self._next_id = 1

    def add(self, row):
        row.id = self._next_id
        self._next_id += 1
        self.added.append(row)

    async def scalar(self, _statement):
        return None

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        return None


def test_the_outbox_only_accumulates():
    outbox = JobOutbox()
    outbox.enqueue("bulk", "soft_match", job_id="softmatch:1", student_id="s")
    assert outbox.entries == [
        OutboxEntry(
            queue="bulk",
            fn_name="soft_match",
            job_id="softmatch:1",
            defer_by=0,
            kwargs={"student_id": "s"},
        )
    ]


def test_the_same_job_id_is_recorded_once_per_request():
    outbox = JobOutbox()
    outbox.enqueue("bulk", "recommendations_batch", job_id="recs:1", urgent=True)
    outbox.enqueue("bulk", "recommendations_batch", job_id="recs:1", urgent=True)
    assert len(outbox.entries) == 1


async def test_flush_passes_job_id_and_defer_to_arq():
    outbox = JobOutbox()
    outbox.enqueue(
        "bulk", "soft_match", job_id="softmatch:1", defer_by=30, student_id="s"
    )
    arq = _Recorder()
    assert await outbox.flush(None, arq) == 1
    [(fn_name, kwargs)] = arq.calls
    assert fn_name == "soft_match"
    assert kwargs["_job_id"] == "softmatch:1"
    assert kwargs["_defer_by"] == 30
    assert kwargs["_queue_name"] == "bulk"
    # Опустошается: повторный flush ничего не ставит.
    assert await outbox.flush(None, arq) == 0


async def test_the_intent_is_written_before_it_is_delivered():
    """Фаза 5 (D01): строка пишется всегда, а не только при отказе Redis —
    иначе падение между коммитом и enqueue теряет задачу навсегда."""
    outbox = JobOutbox()
    outbox.enqueue("bulk", "soft_match", job_id="softmatch:1", student_id=uuid4())
    session = _Session()
    assert await outbox.flush(session, _Recorder()) == 1
    [row] = session.added
    assert row.fn_name == "soft_match"
    assert row.job_id == "softmatch:1"
    assert row.status == "pending"
    assert row.attempts == 0
    assert isinstance(row.kwargs["student_id"], str)


async def test_a_redis_failure_leaves_the_intent_for_the_replay():
    outbox = JobOutbox()
    outbox.enqueue("bulk", "soft_match", job_id="softmatch:1", student_id=uuid4())
    session = _Session()
    assert await outbox.flush(session, _Recorder(fail=True)) == 0
    [row] = session.added
    assert row.status == "pending"


async def test_without_a_pool_the_intent_is_still_recorded():
    outbox = JobOutbox()
    outbox.enqueue("bulk", "outbox_replay", job_id="replay")
    session = _Session()
    assert await outbox.flush(session, None) == 0
    assert len(session.added) == 1


async def test_delivery_carries_the_transport_metadata():
    """Обёртка получает `outbox_id`/lease, генератор — прежние kwargs (§23)."""
    from app.events.outbox import LEASE_TOKEN_KEY, OUTBOX_ID_KEY

    outbox = JobOutbox()
    outbox.enqueue("bulk", "soft_match", job_id="softmatch:1", student_id="s")
    session, arq = _Session(), _Recorder()
    assert await outbox.flush(session, arq) == 1
    [(_fn_name, kwargs)] = arq.calls
    assert kwargs[OUTBOX_ID_KEY] == 1
    assert LEASE_TOKEN_KEY in kwargs
    assert kwargs["student_id"] == "s"


async def test_a_job_outside_the_registry_is_not_recorded():
    """§17: kwargs пользователя не называют произвольную Python-функцию."""
    outbox = JobOutbox()
    outbox.enqueue("bulk", "rm_rf", job_id="nope")
    session, arq = _Session(), _Recorder()
    assert await outbox.flush(session, arq) == 0
    assert session.added == [] and arq.calls == []
