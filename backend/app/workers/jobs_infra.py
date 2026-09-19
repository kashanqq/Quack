"""Infrastructure jobs: aggregates, the Quack batch, the outbox replay.

Thin wrappers over `app.apply.*` — the rules live there, these only open a
session, handle the phase-4 retry policy and write `job.failed` when the
last try is gone (§2.1). They belong to B3 because nothing in them is a
knowledge-model decision.

Phase 5 adds the two recovery jobs, and they keep the same shape: the outbox
replay only *delivers* durable intents, and `recover_graph_events` only
re-runs the ordinary dispatcher in the right order. Neither decides anything
about a student's knowledge.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import structlog
from arq import Retry

from app import keys
from app.apply._lock import student_lock
from app.config import settings
from app.db.repo import outbox as outbox_repo
from app.events import dispatch as dispatcher
from app.events import (
    handlers,  # noqa: F401 — registers the B1 rules
    recovery,
)
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


# --- outbox_replay (§1.4; phase 5 §13.2) ---

_DEPENDENCY_RECHECK_S = 60
_GRAPH_RETRY_S = 60


async def outbox_replay(ctx: dict[str, Any], request_id: str) -> None:
    """Deliver every durable intent that is due, and reclaim dead leases.

    Phase 5 makes this the single recovery path for background work. It
    claims `pending` rows, `waiting_dependency` rows whose `not_before` has
    passed, and rows whose worker lease expired (a crashed worker). If the
    dependency a row waits on is still down the row is parked again rather
    than delivered, and no attempt is spent — an outage costs time, not work
    (AC03).

    It generates no content of its own. Duplicate deliveries are fine, the
    consumers are idempotent; duplicate *effects* are not.
    """
    structlog.contextvars.bind_contextvars(request_id=request_id)
    now = datetime.now(UTC)
    statuses = await _dependency_status(ctx)
    delivered = 0
    async with ctx["sessionmaker"]() as session:
        claimed = await outbox_repo.claim_due(
            session, now, limit=settings.OUTBOX_REPLAY_BATCH
        )
        for intent in claimed:
            if intent.dependency and statuses.get(intent.dependency) is False:
                await outbox_repo.mark_waiting(
                    session,
                    intent.id,
                    lease_token=intent.lease_token,
                    dependency=intent.dependency,  # type: ignore[arg-type]
                    defer_s=_DEPENDENCY_RECHECK_S,
                    now=now,
                )
                continue
            # A fresh token goes out *with* this delivery and is adopted only
            # if ARQ takes it. Rotating it first would fence a retry of the
            # previous delivery that is still perfectly valid.
            token = uuid4()
            entry = outbox_module.OutboxEntry(
                queue=intent.queue,  # type: ignore[arg-type]
                fn_name=intent.fn_name,
                job_id=intent.job_id,
                defer_by=0,
                kwargs=dict(intent.kwargs),
                intent_id=intent.id,
                lease_token=token,
            )
            if await outbox_module._enqueue_one(ctx["redis"], entry):
                await outbox_repo.mark_enqueued(
                    session,
                    intent.id,
                    lease_s=outbox_module.LEASE_S,
                    now=now,
                    lease_token=token,
                )
                delivered += 1
        await session.commit()
    _logger.info("outbox_replay", claimed=len(claimed), enqueued=delivered)


async def _dependency_status(ctx: dict[str, Any]) -> dict[str, bool]:
    """Is each dependency back? Bounded probes only — never a generation."""
    status: dict[str, bool] = {"redis": True}
    llm = ctx.get("llm")
    if llm is not None:
        try:
            status["llm"] = await llm.status() != "down"
        except Exception:  # noqa: BLE001
            status["llm"] = False
    graph = ctx.get("neo4j")
    if graph is None:
        status["graph"] = False
    else:
        try:
            async with graph.session() as session:
                await (await session.run("RETURN 1")).consume()
            status["graph"] = True
        except Exception:  # noqa: BLE001
            status["graph"] = False
    try:
        status["search"] = not await ctx["redis"].get(keys.search_last_error())
    except Exception:  # noqa: BLE001
        status["search"] = True
    return status


# --- recover_graph_events (§13.3) ---


async def recover_graph_events(
    ctx: dict[str, Any],
    request_id: str,
    student_id: str,
    through_event_id: int,
) -> None:
    """Project one student's pending events into the graph, oldest first.

    Not new business logic: every event goes through the ordinary dispatcher,
    so the B1 rules decide exactly what they would have decided at the time.
    What this adds is order, a bounded batch and a watermark — without one, a
    student who keeps answering would hold the job open forever.

    A poison event stops *this student* with its id in the log and in
    `job.failed`; it is not skipped with a pretend `processed_at`, and the
    events behind it keep waiting, because their state depends on it (§16).
    Other students are unaffected.
    """
    structlog.contextvars.bind_contextvars(request_id=request_id)
    student = uuid_of(student_id)
    watermark = int(through_event_id)
    if watermark <= 0:
        return
    if ctx.get("neo4j") is None:
        raise Retry(defer=_GRAPH_RETRY_S)

    applied = 0
    after_id = 0
    async with student_lock(ctx["redis"], student) as got_lock:
        if not got_lock:
            # D10: a graph mutation without the student lock can interleave
            # with a live answer. Waiting is always the safe direction.
            raise Retry(defer=_LOCK_RETRY_S)
        # After a Redis restart the version counter may read an old value; a
        # context cached under that number would look current (D04).
        await _drop_personal_caches(ctx, student)
        while applied < settings.RECOVERY_MAX_PER_JOB:
            async with ctx["sessionmaker"]() as session:
                batch = await recovery.backlog(
                    session,
                    student,
                    through_event_id=watermark,
                    after_id=after_id,
                    limit=settings.RECOVERY_BATCH,
                )
                if not batch:
                    break
                blocked = None
                for event in batch:
                    try:
                        await dispatcher.dispatch(session, event, rule_deps(ctx))
                    except Exception as exc:  # noqa: BLE001 — poison event
                        await session.rollback()
                        await record_failure(
                            ctx,
                            "recover_graph_events",
                            student,
                            {"event_id": event.id, "type": event.type.value},
                            str(exc),
                        )
                        raise
                    if event.processed_at is None:
                        # The graph refused this one. Stop before the events
                        # whose state depends on it.
                        blocked = event.id
                        break
                    after_id = event.id
                    applied += 1
                await session.commit()
            if blocked is not None:
                _logger.warning(
                    "recovery_blocked", event_id=blocked, student_id=str(student)
                )
                raise Retry(defer=_GRAPH_RETRY_S)
    _logger.info(
        "recover_graph_events",
        student_id=str(student),
        applied=applied,
        through_event_id=watermark,
    )


async def _drop_personal_caches(ctx: dict[str, Any], student_id: UUID) -> None:
    """D04: drop this student's derived caches instead of trusting a counter.

    `knowledge_version` lives in Redis. If Redis came back from an older
    snapshot the counter can repeat a value some cached context was tagged
    with, and that context would then be served as current. Deleting the
    personal keys is the cheap, always-correct answer — every one of them is
    rebuildable from Postgres and the graph.
    """
    doomed = [
        keys.knowledge_version(str(student_id)),
        keys.pace(str(student_id)),
        keys.matching_snapshot(str(student_id)),
        *(keys.forecast(str(student_id), exam) for exam in ("SAT_MATH", "ENT_MATH")),
    ]
    try:
        await ctx["redis"].delete(*doomed)
        async for key in ctx["redis"].scan_iter(
            match=keys.ctx_topic(str(student_id), "*"), count=100
        ):
            await ctx["redis"].delete(key)
    except Exception:  # noqa: BLE001 — Redis down: the caches are gone anyway
        _logger.warning("cache_invalidation_failed", student_id=str(student_id))


async def recovery_sweep(ctx: dict[str, Any]) -> None:
    """Startup and cron sweep: one recovery job per student with a backlog."""
    from app.workers.queue import enqueue

    async with ctx["sessionmaker"]() as session:
        marks = [
            (student_id, await recovery.watermark(session, student_id))
            for student_id, _oldest in await recovery.students_with_backlog(session)
        ]
    queued = 0
    for student_id, mark in marks:
        if mark <= 0:
            continue
        try:
            await enqueue(
                ctx["redis"],
                "bulk",
                "recover_graph_events",
                _job_id=f"graph-recover:{student_id}",
                student_id=str(student_id),
                through_event_id=mark,
            )
            queued += 1
        except Exception:  # noqa: BLE001 — the next sweep retries
            _logger.warning("recovery_enqueue_failed", student_id=str(student_id))
    if marks:
        _logger.info("recovery_sweep", students=len(marks), queued=queued)


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


async def recovery_sweep_cron(ctx: dict[str, Any]) -> None:
    """Cron wrapper: `recovery_sweep` takes no `request_id`, a cron does not."""
    await recovery_sweep(ctx)
