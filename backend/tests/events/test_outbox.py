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
    def __init__(self) -> None:
        self.added: list = []
        self.commits = 0

    def add(self, row):
        self.added.append(row)

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


async def test_a_redis_failure_parks_the_job_in_postgres():
    outbox = JobOutbox()
    outbox.enqueue("bulk", "soft_match", job_id="softmatch:1", student_id=uuid4())
    session = _Session()
    assert await outbox.flush(session, _Recorder(fail=True)) == 0
    [row] = session.added
    assert row.fn_name == "soft_match"
    assert row.job_id == "softmatch:1"
    assert isinstance(row.kwargs["student_id"], str)
    assert session.commits == 1


async def test_without_a_pool_the_job_is_parked_too():
    outbox = JobOutbox()
    outbox.enqueue("bulk", "outbox_replay", job_id="replay")
    session = _Session()
    assert await outbox.flush(session, None) == 0
    assert len(session.added) == 1
