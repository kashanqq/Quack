"""Cron schedules and the missed-run catch-up — §13.3 `test_cron.py`."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app import keys
from app.config import settings
from app.workers import jobs_infra
from app.workers import main as workers_main

pytestmark = pytest.mark.phase4


class _Redis:
    def __init__(self, values: dict | None = None) -> None:
        self.values = dict(values or {})

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, **kwargs):
        self.values[key] = value
        return True

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)


class _Sessionmaker:
    def __init__(self, students):
        self.students = students

    def __call__(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None


def _ctx(students, redis=None):
    return {"redis": redis or _Redis(), "sessionmaker": _Sessionmaker(students)}


@pytest.fixture
def active_students(monkeypatch):
    students = [uuid4(), uuid4()]

    async def list_active_students(_session, _since, limit=200):
        return students

    monkeypatch.setattr(
        jobs_infra.events_store, "list_active_students", list_active_students
    )
    return students


@pytest.fixture
def enqueued(monkeypatch):
    calls: list[tuple] = []

    async def enqueue(_redis, queue, fn_name, **kwargs):
        calls.append((queue, fn_name, kwargs))
        return kwargs.get("_job_id")

    import app.workers.queue as queue_module

    monkeypatch.setattr(queue_module, "enqueue", enqueue)
    return calls


def test_three_crons_on_the_bulk_worker():
    names = [job.name for job in workers_main.WorkerBulk.cron_jobs]
    assert names == [
        "cron:daily_aggregates_cron",
        "cron:recommendations_batch_cron",
        "cron:outbox_replay_cron",
    ]


async def test_aggregate_cron_queues_one_job_per_active_student(
    active_students, enqueued
):
    ctx = _ctx(active_students)
    await jobs_infra.daily_aggregates_cron(ctx)
    assert len(enqueued) == len(active_students)
    queue, fn_name, kwargs = enqueued[0]
    assert (queue, fn_name) == ("bulk", "daily_aggregates")
    # Дневной `_job_id` — не чаще раза в сутки из крона (§1.3).
    assert kwargs["_job_id"].startswith(f"aggr:{active_students[0]}:")
    assert ctx["redis"].values[keys.cron_last("daily_aggregates")]


async def test_recommendation_cron_writes_its_timestamp(active_students, enqueued):
    ctx = _ctx(active_students)
    await jobs_infra.recommendations_batch_cron(ctx)
    assert {fn_name for _q, fn_name, _k in enqueued} == {"recommendations_batch"}
    assert all(kwargs["urgent"] is False for _q, _f, kwargs in enqueued)
    assert ctx["redis"].values[keys.cron_last("recommendations_batch")]


async def test_startup_compensates_a_cron_that_never_fired(active_students, enqueued):
    stale = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
    ctx = _ctx(active_students, _Redis({keys.cron_last("daily_aggregates"): stale}))
    await jobs_infra.catch_up(ctx)
    assert {fn_name for _q, fn_name, _k in enqueued} == {"daily_aggregates"}


async def test_a_fresh_cron_timestamp_triggers_nothing(active_students, enqueued):
    fresh = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    ctx = _ctx(active_students, _Redis({keys.cron_last("daily_aggregates"): fresh}))
    await jobs_infra.catch_up(ctx)
    assert enqueued == []


def test_bulk_worker_limits_come_from_settings():
    assert workers_main.WorkerBulk.max_jobs == settings.BULK_MAX_JOBS
    assert workers_main.WorkerBulk.keep_result == settings.JOB_KEEP_RESULT_S
    assert workers_main.WorkerInteractive.keep_result == settings.JOB_KEEP_RESULT_S


async def test_fan_out_survives_a_failing_enqueue(monkeypatch, active_students):
    """Крон не падает из-за одной непоставленной задачи: следующий запуск
    поставит её снова, а сейчас важнее обойти остальных учеников."""
    import app.workers.queue as queue_module

    async def boom(*_args, **_kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr(queue_module, "enqueue", boom)
    ctx = _ctx(active_students)
    await jobs_infra.daily_aggregates_cron(ctx)
    assert ctx["redis"].values[keys.cron_last("daily_aggregates")]
