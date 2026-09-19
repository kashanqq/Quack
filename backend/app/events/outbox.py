"""Job outbox — a durable intent first, delivery to ARQ after the commit.

An event handler runs inside an uncommitted transaction. If it put an ARQ job
on the queue directly, the worker could read Postgres before the commit and
not see the event, the set or the `generating` row it was told about. So
handlers only *record* the intent here.

Phase 5 (§9.2, D01) makes that record durable. Phase 4 wrote a `job_outbox`
row only when Redis refused the enqueue, which leaves the window between
`COMMIT` and `enqueue_job` uncovered — a crash there loses the job with
nothing left to replay. Now the intent is written **in the same transaction**
as the authoritative write (`persist`), and only afterwards is it handed to
ARQ (`deliver`). Delivery may be duplicated, may fail, may be lost; none of
that loses the work, because the row is still `pending` in Postgres and the
`outbox_replay` cron claims it.

Nothing here ever raises into the handler: a lost job must not fail a
student's request.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobOutbox as JobOutboxRow
from app.db.repo import outbox as outbox_repo

_logger = structlog.get_logger(__name__)

Queue = Literal["interactive", "bulk"]

# Transport metadata the wrapper strips before the generator sees its kwargs
# (§23 "Job transport"): the domain signature of every job is unchanged.
OUTBOX_ID_KEY = "_outbox_id"
LEASE_TOKEN_KEY = "_lease_token"

# How long a delivered-but-not-yet-finished row is considered owned. Longer
# than the longest job budget (`JOB_TIMEOUT_MAX_S`) plus queue wait, so a slow
# job is not reclaimed underneath itself (D09).
LEASE_S = 900


@dataclass(frozen=True)
class OutboxEntry:
    queue: Queue
    fn_name: str
    job_id: str
    defer_by: int
    kwargs: dict[str, Any]
    intent_id: int | None = None
    lease_token: UUID | None = None


@dataclass
class JobOutbox:
    """Per-request (or per-job) buffer of jobs to enqueue after the commit."""

    entries: list[OutboxEntry] = field(default_factory=list)
    # Rows already written to `job_outbox` and waiting to be handed to ARQ.
    ready: list[OutboxEntry] = field(default_factory=list)

    def enqueue(
        self,
        queue: Queue,
        fn_name: str,
        *,
        job_id: str,
        defer_by: int = 0,
        **kwargs: Any,
    ) -> None:
        """Record one job. Same `job_id` twice in one request — recorded once."""
        if any(entry.job_id == job_id for entry in self.entries):
            return
        self.entries.append(
            OutboxEntry(
                queue=queue,
                fn_name=fn_name,
                job_id=job_id,
                defer_by=defer_by,
                kwargs=_jsonable(kwargs),
            )
        )

    def take(self) -> list[OutboxEntry]:
        entries, self.entries = self.entries, []
        return entries

    async def persist(self, session: AsyncSession) -> int:
        """Write the recorded intents in the caller's open transaction.

        Must be called *before* that transaction commits — that is the whole
        point: either the event and its follow-up work are both durable, or
        neither is. A duplicate of a live logical job is dropped here, not
        later by the queue.
        """
        entries = self.take()
        if not entries:
            return 0
        now = datetime.now(UTC)
        written = 0
        for entry in entries:
            if not _known_job(entry.fn_name, entry.queue):
                _logger.warning(
                    "outbox_unknown_job", fn=entry.fn_name, queue=entry.queue
                )
                continue
            try:
                intent = await outbox_repo.record(
                    session,
                    queue=entry.queue,
                    fn_name=entry.fn_name,
                    job_id=entry.job_id,
                    kwargs=entry.kwargs,
                    defer_by=entry.defer_by,
                    now=now,
                )
            except Exception:  # noqa: BLE001 — a lost job must not fail the write
                # No durable row, but dropping the job outright is strictly
                # worse: deliver it best-effort, the phase-4 way.
                _logger.warning("outbox_record_failed", fn=entry.fn_name, exc_info=True)
                self.ready.append(entry)
                continue
            if intent is None:
                _logger.info(
                    "outbox_duplicate_skipped",
                    fn=entry.fn_name,
                    job_id=entry.job_id,
                )
                continue
            self.ready.append(
                replace(entry, intent_id=intent.id, lease_token=intent.lease_token)
            )
            written += 1
        return written

    async def deliver(self, sessionmaker: Any, arq: Any) -> int:
        """Hand the persisted intents to ARQ. Only after the commit."""
        entries, self.ready = self.ready, []
        if not entries:
            return 0
        delivered: list[OutboxEntry] = []
        for entry in entries:
            if await _enqueue_one(arq, entry):
                delivered.append(entry)
        if delivered and sessionmaker is not None:
            await _confirm(sessionmaker, delivered)
        return len(delivered)

    async def flush(
        self,
        session: AsyncSession | None,
        arq: Any,
        sessionmaker: Any = None,
    ) -> int:
        """Persist (if a session is available) and deliver in one step.

        The worker path: a job commits its own transaction and then flushes,
        so "after the commit" holds there as well. Without a session there is
        nothing durable to write — the entries are delivered best-effort and
        the caller is warned, because that is the phase-4 behaviour D01
        replaces, not a supported mode.
        """
        if self.entries:
            if session is None:
                _logger.warning("outbox_persist_skipped", entries=len(self.entries))
                self.ready.extend(self.take())
            else:
                try:
                    await self.persist(session)
                    await session.commit()
                except Exception:  # noqa: BLE001
                    _logger.warning("outbox_persist_failed", exc_info=True)
                    self.ready.extend(self.take())
        return await self.deliver(sessionmaker, arq)


def _known_job(fn_name: str, queue: str) -> bool:
    """Registry allowlist (§17): user input never names a Python function."""
    from app.workers.registry import JOB_QUEUES

    expected = JOB_QUEUES.get(fn_name)
    return expected is not None and expected == queue


async def _confirm(sessionmaker: Any, entries: list[OutboxEntry]) -> None:
    now = datetime.now(UTC)
    try:
        async with sessionmaker() as session:
            for entry in entries:
                if entry.intent_id is None:
                    continue
                await outbox_repo.mark_enqueued(
                    session, entry.intent_id, lease_s=LEASE_S, now=now
                )
            await session.commit()
    except Exception:  # noqa: BLE001 — the replay re-checks the row anyway
        _logger.warning("outbox_confirm_failed", exc_info=True)


async def _enqueue_one(arq: Any, entry: OutboxEntry) -> bool:
    if arq is None:
        _logger.warning("outbox_enqueue_failed", fn=entry.fn_name, reason="no_pool")
        return False
    # Imported here so `app.events` stays importable without the worker deps.
    from app.workers.queue import enqueue as enqueue_job

    metadata: dict[str, Any] = {}
    if entry.intent_id is not None:
        metadata[OUTBOX_ID_KEY] = entry.intent_id
        metadata[LEASE_TOKEN_KEY] = (
            str(entry.lease_token) if entry.lease_token else None
        )
    try:
        accepted = await enqueue_job(
            arq,
            entry.queue,
            entry.fn_name,
            _job_id=entry.job_id,
            _defer_by=entry.defer_by or None,
            **entry.kwargs,
            **metadata,
        )
    except Exception:  # noqa: BLE001 — a missed job must not fail the request
        _logger.warning(
            "outbox_enqueue_failed",
            fn=entry.fn_name,
            job_id=entry.job_id,
            exc_info=True,
        )
        return False
    if accepted is None:
        # ARQ still holds this `job_id` (a live copy, or a result inside
        # `keep_result`). Nothing new was queued, so the row must stay due
        # rather than be marked delivered — §9.2: a `None` from `enqueue_job`
        # is not proof the work happened.
        _logger.info("outbox_enqueue_duplicate", fn=entry.fn_name, job_id=entry.job_id)
        return False
    _logger.info(
        "outbox_enqueued",
        fn=entry.fn_name,
        job_id=entry.job_id,
        outbox_id=entry.intent_id,
    )
    return True


def _jsonable(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {key: _value(value) for key, value in kwargs.items()}


def _value(value: Any) -> Any:
    if isinstance(value, list):
        return [_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _value(item) for key, item in value.items()}
    if isinstance(value, str | int | float | bool | None):
        return value
    return str(value)


async def pending(session: AsyncSession, limit: int = 100) -> list[JobOutboxRow]:
    """Undelivered rows, oldest first — kept for the phase-4 read path."""
    return list(
        (
            await session.scalars(
                select(JobOutboxRow)
                .where(JobOutboxRow.status.in_(outbox_repo.DUE))
                .order_by(JobOutboxRow.id)
                .limit(limit)
            )
        ).all()
    )


async def mark_enqueued(session: AsyncSession, ids: list[int]) -> None:
    if not ids:
        return
    now = datetime.now(UTC)
    await session.execute(
        update(JobOutboxRow)
        .where(JobOutboxRow.id.in_(ids))
        .values(status="enqueued", enqueued_at=now, updated_at=now)
    )
