"""Infrastructure jobs: aggregates, the Quack batch, the outbox replay.

Thin wrappers over `app.apply.*` — the rules live there, these only open a
session, handle the phase-4 retry policy and write `job.failed` when the
last try is gone (§2.1). They belong to B3 because nothing in them is a
knowledge-model decision.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from arq import Retry

from app import keys
from app.config import settings
from app.events import outbox as outbox_module
from app.events import store as events_store
from app.events.dispatch import RuleDeps
from app.events.outbox import JobOutbox
from app.schemas.events import EventIn, EventType, JobFailedPayload

_logger = structlog.get_logger(__name__)

_MAX_TRIES = 3
_LOCK_RETRY_S = 10
_CRON_CATCHUP_FACTOR = 1.5


def rule_deps(ctx: dict[str, Any], jobs: JobOutbox | None = None) -> RuleDeps:
    return RuleDeps(
        graph=ctx.get("neo4j"),
        redis=ctx["redis"],
        params=settings.knowledge,
        now=lambda: datetime.now(UTC),
        jobs=jobs if jobs is not None else JobOutbox(),
    )


def uuid_of(value: Any) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


async def record_failure(
    ctx: dict[str, Any], job: str, student_id: UUID | None, args: dict, error: str
) -> None:
    """`job.failed` in its own session — the job's own may be rolled back."""
    if student_id is None:
        _logger.warning("job_failed", job=job, reason=error, **args)
        return
    try:
        async with ctx["sessionmaker"]() as session:
            await events_store.append(
                session,
                ctx["redis"],
                EventIn(
                    type=EventType.job_failed,
                    payload=JobFailedPayload(
                        job=job,
                        job_id=ctx.get("job_id"),
                        reason=error[:200],
                        args=args,
                    ).model_dump(mode="json"),
                    student_id=student_id,
                ),
                dispatch_event=False,
            )
            await session.commit()
    except Exception:  # noqa: BLE001 — nothing left to report to
        _logger.exception("job_failed_not_recorded", job=job)
    _logger.warning("job_failed", job=job, reason=error[:200], **args)


def last_try(ctx: dict[str, Any], max_tries: int = _MAX_TRIES) -> bool:
    return int(ctx.get("job_try", 1) or 1) >= max_tries


# --- daily_aggregates (§9) ---


async def daily_aggregates(
    ctx: dict[str, Any],
    request_id: str,
    student_id: str,
    day: str | None = None,
    force: bool = False,
) -> None:
    structlog.contextvars.bind_contextvars(request_id=request_id)
    from app.apply import aggregates as apply_aggregates

    student = uuid_of(student_id)
    lock = keys.lock(f"aggr:{student}")
    if not await _acquire(ctx["redis"], lock):
        return
    try:
        async with ctx["sessionmaker"]() as session:
            await apply_aggregates.run(
                session,
                rule_deps(ctx),
                student,
                date.fromisoformat(day) if day else None,
                force,
            )
            await session.commit()
    except Exception as exc:  # noqa: BLE001 — classified by the retry policy
        if last_try(ctx):
            await record_failure(
                ctx, "daily_aggregates", student, {"day": day}, str(exc)
            )
            return
        raise
    finally:
        await _release(ctx["redis"], lock)


# --- recommendations_batch (§8.2) ---


async def recommendations_batch(
    ctx: dict[str, Any], request_id: str, student_id: str, urgent: bool = False
) -> None:
    structlog.contextvars.bind_contextvars(request_id=request_id)
    from app.apply import quack as apply_quack

    student = uuid_of(student_id)
    jobs = JobOutbox()
    try:
        async with ctx["sessionmaker"]() as session:
            result = await apply_quack.run_batch(
                session, rule_deps(ctx, jobs), student, urgent
            )
            await session.commit()
    except apply_quack.BatchLocked:
        # Второй запуск не пропускаем: пропущенный крон отложил бы
        # `normal`-рекомендации на сутки (§16 item 9б).
        raise Retry(defer=_LOCK_RETRY_S) from None
    except Retry:
        raise
    except Exception as exc:  # noqa: BLE001
        if last_try(ctx):
            await record_failure(
                ctx, "recommendations_batch", student, {"urgent": urgent}, str(exc)
            )
            return
        raise
    await jobs.flush(None, ctx["redis"])
    _logger.info(
        "recommendations_batch",
        student_id=str(student),
        urgent=urgent,
        created=result.created,
        updated=result.updated,
        expired=result.expired,
    )


# --- outbox_replay (§1.4) ---


async def outbox_replay(ctx: dict[str, Any], request_id: str) -> None:
    """Re-enqueue what Redis refused while it was down."""
    structlog.contextvars.bind_contextvars(request_id=request_id)
    async with ctx["sessionmaker"]() as session:
        rows = await outbox_module.pending(session)
        if not rows:
            return
        done: list[int] = []
        for row in rows:
            entry = outbox_module.OutboxEntry(
                queue=row.queue,  # type: ignore[arg-type]
                fn_name=row.fn_name,
                job_id=row.job_id,
                defer_by=row.defer_by,
                kwargs=dict(row.kwargs or {}),
            )
            if await outbox_module._enqueue_one(ctx["redis"], entry):
                done.append(row.id)
        await outbox_module.mark_enqueued(session, done)
        await session.commit()
    _logger.info("outbox_replay", pending=len(rows), enqueued=len(done))


# --- crons (§1.2) ---


async def daily_aggregates_cron(ctx: dict[str, Any]) -> None:
    await _fan_out(ctx, "daily_aggregates", _aggregate_kwargs)


async def recommendations_batch_cron(ctx: dict[str, Any]) -> None:
    await _fan_out(ctx, "recommendations_batch", _recs_kwargs)


def _aggregate_kwargs(student_id: UUID) -> tuple[str, dict[str, Any]]:
    today = datetime.now(UTC).date().isoformat()
    return f"aggr:{student_id}:{today}", {"student_id": str(student_id)}


def _recs_kwargs(student_id: UUID) -> tuple[str, dict[str, Any]]:
    return f"recs:{student_id}", {"student_id": str(student_id), "urgent": False}


async def _fan_out(ctx: dict[str, Any], fn_name: str, make) -> None:
    """One job per active student, deduplicated by a deterministic id."""
    from app.workers.queue import enqueue

    since = datetime.now(UTC) - timedelta(days=settings.knowledge.aggregate_window_days)
    async with ctx["sessionmaker"]() as session:
        students = await events_store.list_active_students(session, since)
    for student_id in students:
        job_id, kwargs = make(student_id)
        try:
            await enqueue(ctx["redis"], "bulk", fn_name, _job_id=job_id, **kwargs)
        except Exception:  # noqa: BLE001 — the next cron run will retry
            _logger.warning("cron_enqueue_failed", fn=fn_name, job_id=job_id)
    await _note_cron(ctx["redis"], fn_name)
    _logger.info("cron_fan_out", fn=fn_name, students=len(students))


async def _note_cron(redis: Any, name: str) -> None:
    try:
        await redis.set(keys.cron_last(name), datetime.now(UTC).isoformat())
    except Exception:  # noqa: BLE001
        return


async def catch_up(ctx: dict[str, Any]) -> None:
    """A cron that never fired while the worker was down runs at startup.

    The window of `daily_aggregates` is fourteen days, so one immediate run
    covers any sane outage (§9.5).
    """
    checks = (
        ("daily_aggregates", daily_aggregates_cron, 24),
        (
            "recommendations_batch",
            recommendations_batch_cron,
            settings.knowledge.recs_interval_h,
        ),
    )
    for name, runner, interval_h in checks:
        try:
            raw = await ctx["redis"].get(keys.cron_last(name))
        except Exception:  # noqa: BLE001
            continue
        if raw is None:
            continue
        value = raw.decode() if isinstance(raw, bytes) else raw
        try:
            last = datetime.fromisoformat(value)
        except ValueError:
            continue
        overdue = timedelta(hours=interval_h * _CRON_CATCHUP_FACTOR)
        if datetime.now(UTC) - last > overdue:
            _logger.info("cron_catch_up", cron=name)
            await runner(ctx)


# --- locks ---


async def _acquire(redis: Any, key: str, ttl: int = 120) -> bool:
    try:
        return bool(await redis.set(key, "1", nx=True, ex=ttl))
    except Exception:  # noqa: BLE001
        _logger.warning("lock_redis_unavailable", key=key)
        return True


async def _release(redis: Any, key: str) -> None:
    try:
        await redis.delete(key)
    except Exception:  # noqa: BLE001
        return


async def outbox_replay_cron(ctx: dict[str, Any]) -> None:
    """Cron wrapper: `outbox_replay` takes a `request_id`, a cron does not."""
    await outbox_replay(ctx, request_id="cron")
