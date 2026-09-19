"""Job outbox — enqueue only after the transaction has been committed (§1.4).

An event handler runs inside an uncommitted transaction. If it put an ARQ job
on the queue directly, the worker could read Postgres before the commit and
not see the event, the set or the `generating` row it was told about. So
handlers only *record* the intent here; the transport flushes the records
once `session.commit()` has returned.

The accumulate-then-flush shape is the same in the worker: the signature
`enqueue(...)` is synchronous by contract (§14.10) and handlers call it
without awaiting, so a job flushes its own outbox explicitly right after it
commits — worker transactions are short, so this is the "immediate" mode of
§1.4 in practice.

If Redis refuses the enqueue, the record goes to the `job_outbox` table and
the `outbox_replay` cron picks it up. Nothing here ever raises into the
handler: a lost job must not fail a student's request.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobOutbox as JobOutboxRow

_logger = structlog.get_logger(__name__)

Queue = Literal["interactive", "bulk"]


@dataclass(frozen=True)
class OutboxEntry:
    queue: Queue
    fn_name: str
    job_id: str
    defer_by: int
    kwargs: dict[str, Any]


@dataclass
class JobOutbox:
    """Per-request (or per-job) buffer of jobs to enqueue after the commit."""

    entries: list[OutboxEntry] = field(default_factory=list)

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
                kwargs=kwargs,
            )
        )

    def take(self) -> list[OutboxEntry]:
        entries, self.entries = self.entries, []
        return entries

    async def flush(self, session: AsyncSession | None, arq: Any) -> int:
        """Enqueue everything recorded; park what Redis would not take."""
        entries = self.take()
        if not entries:
            return 0
        enqueued = 0
        for entry in entries:
            if await _enqueue_one(arq, entry):
                enqueued += 1
            elif session is not None:
                await _park(session, entry)
        return enqueued


async def _enqueue_one(arq: Any, entry: OutboxEntry) -> bool:
    if arq is None:
        _logger.warning("outbox_enqueue_failed", fn=entry.fn_name, reason="no_pool")
        return False
    # Imported here so `app.events` stays importable without the worker deps.
    from app.workers.queue import enqueue as enqueue_job

    try:
        await enqueue_job(
            arq,
            entry.queue,
            entry.fn_name,
            _job_id=entry.job_id,
            _defer_by=entry.defer_by or None,
            **entry.kwargs,
        )
    except Exception:  # noqa: BLE001 — a missed job must not fail the request
        _logger.warning(
            "outbox_enqueue_failed",
            fn=entry.fn_name,
            job_id=entry.job_id,
            exc_info=True,
        )
        return False
    _logger.info("outbox_enqueued", fn=entry.fn_name, job_id=entry.job_id)
    return True


async def _park(session: AsyncSession, entry: OutboxEntry) -> None:
    """Persist the intent so `outbox_replay` can retry it later."""
    try:
        session.add(
            JobOutboxRow(
                queue=entry.queue,
                fn_name=entry.fn_name,
                job_id=entry.job_id,
                kwargs=_jsonable(entry.kwargs),
                defer_by=entry.defer_by,
            )
        )
        await session.commit()
    except Exception:  # noqa: BLE001
        await session.rollback()
        _logger.warning("outbox_park_failed", fn=entry.fn_name, exc_info=True)


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
    return list(
        (
            await session.scalars(
                select(JobOutboxRow)
                .where(JobOutboxRow.enqueued_at.is_(None))
                .order_by(JobOutboxRow.id)
                .limit(limit)
            )
        ).all()
    )


async def mark_enqueued(session: AsyncSession, ids: list[int]) -> None:
    if not ids:
        return
    await session.execute(
        update(JobOutboxRow)
        .where(JobOutboxRow.id.in_(ids))
        .values(enqueued_at=datetime.now(UTC))
    )
