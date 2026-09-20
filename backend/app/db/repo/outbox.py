"""Durable job intents — the `job_outbox` lifecycle (§9.2, §13.1).

This is the only module that writes `job_outbox.status`. Everything else
talks to it through `app.events.outbox` (recording and delivery) or through
the job wrapper in `app.workers.durable` (execution).

Two rules shape the signatures:

- **Attempts count executions, not waiting.** `mark_waiting` is what an
  outage does; it moves `not_before` and leaves `attempts` alone, so an LLM
  that is down for an hour cannot exhaust a text's three tries.
- **A lease is fenced.** `mark_*` for a running job takes the token it was
  handed; a worker that was declared dead and whose row was already reclaimed
  cannot overwrite the state of the new owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobOutbox as JobOutboxRow

Status = Literal[
    "pending",
    "enqueued",
    "running",
    "waiting_dependency",
    "succeeded",
    "failed",
    "cancelled",
]
Dependency = Literal["llm", "graph", "search", "redis"]

ACTIVE: tuple[str, ...] = ("pending", "enqueued", "running", "waiting_dependency")
DUE: tuple[str, ...] = ("pending", "waiting_dependency")


@dataclass(frozen=True)
class Intent:
    """One durable row, as the dispatcher and the wrapper see it."""

    id: int
    queue: str
    fn_name: str
    job_id: str
    kwargs: dict[str, Any]
    defer_by: int
    status: str
    dependency: str | None
    attempts: int
    lease_token: UUID | None


def _intent(row: JobOutboxRow) -> Intent:
    return Intent(
        id=row.id,
        queue=row.queue,
        fn_name=row.fn_name,
        job_id=row.job_id,
        kwargs=dict(row.kwargs or {}),
        defer_by=int(row.defer_by or 0),
        status=row.status,
        dependency=row.dependency,
        attempts=int(row.attempts or 0),
        lease_token=row.lease_token,
    )


async def record(
    session: AsyncSession,
    *,
    queue: str,
    fn_name: str,
    job_id: str,
    kwargs: dict[str, Any],
    defer_by: int = 0,
    now: datetime | None = None,
) -> Intent | None:
    """Write one `pending` intent in the caller's transaction.

    Returns `None` when this logical job is already live: the partial unique
    index is the real guard, but checking first keeps the caller's
    transaction from being poisoned by an `IntegrityError` it cannot handle
    (the event write it is sharing the transaction with must still commit).
    """
    moment = now or datetime.now(UTC)
    existing = await session.scalar(
        select(JobOutboxRow.id).where(
            JobOutboxRow.queue == queue,
            JobOutboxRow.job_id == job_id,
            JobOutboxRow.status.in_(ACTIVE),
        )
    )
    if existing is not None:
        return None
    row = JobOutboxRow(
        queue=queue,
        fn_name=fn_name,
        job_id=job_id,
        kwargs=kwargs,
        defer_by=defer_by,
        created_at=moment,
        status="pending",
        attempts=0,
        not_before=moment + timedelta(seconds=defer_by),
        updated_at=moment,
        # A token from the start, not only from the first claim: the delivery
        # that follows this commit carries it, so a worker whose row has since
        # been reclaimed is fenced out on its very first write.
        lease_token=uuid4(),
    )
    session.add(row)
    await session.flush()
    return _intent(row)


async def claim_due(
    session: AsyncSession, now: datetime, limit: int = 100
) -> list[Intent]:
    """Rows the dispatcher may deliver: due work plus expired leases.

    `SKIP LOCKED` so two replays never fight over the same row. The token is
    *not* rotated here: rotating it before we know a delivery will happen
    fences an ARQ retry that is still perfectly valid, and the row then sits
    in `enqueued` until its lease expires. The new token is stamped by
    `mark_enqueued`, once ARQ has actually taken a job.
    """
    rows = (
        await session.scalars(
            select(JobOutboxRow)
            .where(
                or_(
                    JobOutboxRow.status.in_(DUE) & (JobOutboxRow.not_before <= now),
                    JobOutboxRow.status.in_(("enqueued", "running"))
                    & JobOutboxRow.lease_until.is_not(None)
                    & (JobOutboxRow.lease_until <= now),
                )
            )
            .order_by(JobOutboxRow.not_before, JobOutboxRow.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    ).all()
    claimed: list[Intent] = []
    for row in rows:
        row.updated_at = now
        claimed.append(_intent(row))
    return claimed


async def mark_enqueued(
    session: AsyncSession,
    intent_id: int,
    *,
    lease_s: int,
    now: datetime,
    lease_token: UUID | None = None,
) -> None:
    """ARQ accepted a delivery: start the lease, and adopt its token.

    `lease_token` is the token that went out *with* that delivery, so the
    worker which receives it owns the row and any older in-flight copy is
    fenced. It is written only now, after the enqueue succeeded — see
    `claim_due`.
    """
    values: dict[str, Any] = {
        "status": "enqueued",
        "enqueued_at": now,
        "lease_until": now + timedelta(seconds=lease_s),
        "updated_at": now,
        "last_error_code": None,
    }
    if lease_token is not None:
        values["lease_token"] = lease_token
    await session.execute(
        update(JobOutboxRow).where(JobOutboxRow.id == intent_id).values(**values)
    )


async def mark_started(
    session: AsyncSession,
    intent_id: int,
    *,
    lease_token: UUID | None,
    lease_s: int,
    now: datetime,
) -> bool:
    """Take ownership of the row. `False` — someone else owns it now."""
    result = await session.execute(
        _fenced(intent_id, lease_token).values(
            status="running",
            lease_until=now + timedelta(seconds=lease_s),
            updated_at=now,
        )
    )
    return result.rowcount > 0


async def mark_done(
    session: AsyncSession, intent_id: int, *, lease_token: UUID | None, now: datetime
) -> None:
    await session.execute(
        _fenced(intent_id, lease_token).values(
            status="succeeded",
            dependency=None,
            lease_until=None,
            updated_at=now,
            last_error_code=None,
        )
    )


async def mark_waiting(
    session: AsyncSession,
    intent_id: int,
    *,
    lease_token: UUID | None,
    dependency: Dependency,
    defer_s: int,
    now: datetime,
) -> None:
    """Park on an outage: no attempt is spent and the row stays claimable."""
    await session.execute(
        _fenced(intent_id, lease_token).values(
            status="waiting_dependency",
            dependency=dependency,
            not_before=now + timedelta(seconds=defer_s),
            lease_until=None,
            updated_at=now,
            last_error_code=f"{dependency}_unavailable",
        )
    )


async def mark_deferred(
    session: AsyncSession,
    intent_id: int,
    *,
    lease_token: UUID | None,
    defer_s: int,
    now: datetime,
) -> None:
    """Come back later without blaming anything: a busy lock, a cron skew.

    Like `mark_waiting` it spends no attempt, but it names no dependency —
    the replay is free to deliver it as soon as `not_before` passes.
    """
    await session.execute(
        _fenced(intent_id, lease_token).values(
            status="pending",
            dependency=None,
            not_before=now + timedelta(seconds=defer_s),
            lease_until=None,
            updated_at=now,
        )
    )


async def mark_retry(
    session: AsyncSession,
    intent_id: int,
    *,
    lease_token: UUID | None,
    error_code: str,
    defer_s: int,
    now: datetime,
) -> int:
    """A real failure of this job: spend one attempt and back off."""
    result = await session.execute(
        _fenced(intent_id, lease_token)
        .values(
            status="pending",
            dependency=None,
            attempts=JobOutboxRow.attempts + 1,
            not_before=now + timedelta(seconds=defer_s),
            lease_until=None,
            updated_at=now,
            last_error_code=error_code[:100],
        )
        .returning(JobOutboxRow.attempts)
    )
    attempts = result.scalar()
    return int(attempts or 0)


async def mark_failed(
    session: AsyncSession,
    intent_id: int,
    *,
    lease_token: UUID | None,
    error_code: str,
    now: datetime,
) -> None:
    await session.execute(
        _fenced(intent_id, lease_token).values(
            status="failed",
            dependency=None,
            attempts=JobOutboxRow.attempts + 1,
            lease_until=None,
            updated_at=now,
            last_error_code=error_code[:100],
        )
    )


async def mark_cancelled(
    session: AsyncSession,
    intent_id: int,
    *,
    lease_token: UUID | None,
    reason: str,
    now: datetime,
) -> None:
    """The target is gone or superseded — not a failure, and not a retry."""
    await session.execute(
        _fenced(intent_id, lease_token).values(
            status="cancelled",
            dependency=None,
            lease_until=None,
            updated_at=now,
            last_error_code=reason[:100],
        )
    )


def _fenced(intent_id: int, lease_token: UUID | None):
    statement = update(JobOutboxRow).where(JobOutboxRow.id == intent_id)
    if lease_token is not None:
        statement = statement.where(
            or_(
                JobOutboxRow.lease_token == lease_token,
                JobOutboxRow.lease_token.is_(None),
            )
        )
    return statement


async def get(session: AsyncSession, intent_id: int) -> Intent | None:
    row = await session.get(JobOutboxRow, intent_id)
    return _intent(row) if row is not None else None


async def backlog(session: AsyncSession) -> list[tuple[str, str, int, datetime | None]]:
    """(status, queue, count, oldest `not_before`) — the §19 operator view."""
    from sqlalchemy import func

    rows = await session.execute(
        select(
            JobOutboxRow.status,
            JobOutboxRow.queue,
            func.count(),
            func.min(JobOutboxRow.not_before),
        )
        .where(JobOutboxRow.status.in_(ACTIVE))
        .group_by(JobOutboxRow.status, JobOutboxRow.queue)
        .order_by(JobOutboxRow.status, JobOutboxRow.queue)
    )
    return [
        (status, queue, int(count), oldest) for status, queue, count, oldest in rows
    ]
