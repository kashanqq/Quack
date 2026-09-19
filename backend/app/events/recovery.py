"""Which unprocessed events may be replayed into the graph, and how to find them.

Phase 5, §12 and D02. `events.processed_at` is not a general-purpose "some
consumer has seen this" flag: phase 3 also uses `NULL` to mark the observer's
open window over `message.*`, and `job.failed` is never dispatched at all.
Replaying every `processed_at IS NULL` row would therefore call the observer
over raw chat messages a second time and count service records as knowledge
backlog.

So recovery works from an explicit allowlist — the event types that have a
registered graph-mutating handler — and every read here is bounded and keyset
paginated over `ix_events_unprocessed` (§18). Nothing in this module calls a
model or writes: it only says *what* is outstanding. The application itself
stays in `app.apply` through the ordinary dispatcher.
"""

from __future__ import annotations

from typing import Final
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event as EventRow
from app.schemas.events import Event, EventType

_logger = structlog.get_logger(__name__)

#: Event types whose handlers write the personal graph. `message.*`,
#: `observer.requested`, `job.failed`, the text-opened records and the Quack
#: decisions are deliberately absent: they either have no graph handler or are
#: an input to a job that must not be re-run from here.
RECOVERABLE: Final[tuple[EventType, ...]] = (
    EventType.task_answered,
    EventType.diagnostic_completed,
    EventType.mock_completed,
    EventType.observation_extracted,
    EventType.misconception_canonized,
    EventType.misconception_personal_created,
    EventType.misconception_disputed,
    EventType.misconception_undisputed,
)

_VALUES: Final[list[str]] = [event_type.value for event_type in RECOVERABLE]


def is_recoverable(event_type: EventType | str) -> bool:
    value = event_type.value if isinstance(event_type, EventType) else event_type
    return value in _VALUES


async def backlog(
    session: AsyncSession,
    student_id: UUID,
    *,
    through_event_id: int,
    after_id: int = 0,
    limit: int = 50,
) -> list[Event]:
    """One student's outstanding graph events, oldest first.

    `through_event_id` is a watermark taken once when the job starts: without
    it a student who keeps answering would hold the job open forever (§13.3).
    """
    rows = await session.scalars(
        select(EventRow)
        .where(
            EventRow.student_id == student_id,
            EventRow.processed_at.is_(None),
            EventRow.id > after_id,
            EventRow.id <= through_event_id,
            EventRow.type.in_(_VALUES),
        )
        .order_by(EventRow.id)
        .limit(limit)
    )
    return [Event.model_validate(row) for row in rows]


async def oldest_pending_id(session: AsyncSession, student_id: UUID) -> int | None:
    """The first event this student is blocked on, or `None`."""
    return await session.scalar(
        select(func.min(EventRow.id)).where(
            EventRow.student_id == student_id,
            EventRow.processed_at.is_(None),
            EventRow.type.in_(_VALUES),
        )
    )


async def is_pending(session: AsyncSession, student_id: UUID) -> bool:
    """`oldest_pending_id`, but a read model never fails over this label.

    The flag is decoration on an answer the route has already computed; if
    the probe itself cannot run, the honest fallback is "nothing known to be
    pending", not a 500.
    """
    try:
        return await oldest_pending_id(session, student_id) is not None
    except Exception:  # noqa: BLE001
        _logger.warning("pending_probe_failed", student_id=str(student_id))
        return False


async def watermark(session: AsyncSession, student_id: UUID) -> int:
    """The newest recoverable event id of this student; 0 when there is none."""
    value = await session.scalar(
        select(func.max(EventRow.id)).where(
            EventRow.student_id == student_id,
            EventRow.processed_at.is_(None),
            EventRow.type.in_(_VALUES),
        )
    )
    return int(value or 0)


async def pending_count(session: AsyncSession) -> int:
    """The whole recoverable backlog — what `/health.graph_pending` reports.

    Not "the last hour" and not the observer's open window: an event stuck
    since yesterday is exactly the one an operator needs to see (§19).
    """
    value = await session.scalar(
        select(func.count())
        .select_from(EventRow)
        .where(EventRow.processed_at.is_(None), EventRow.type.in_(_VALUES))
    )
    return int(value or 0)


async def students_with_backlog(
    session: AsyncSession, limit: int = 100
) -> list[tuple[UUID, int]]:
    """(student, oldest pending id) for the startup sweep, oldest first."""
    rows = await session.execute(
        select(EventRow.student_id, func.min(EventRow.id))
        .where(EventRow.processed_at.is_(None), EventRow.type.in_(_VALUES))
        .group_by(EventRow.student_id)
        .order_by(func.min(EventRow.id))
        .limit(limit)
    )
    return [(student_id, int(oldest)) for student_id, oldest in rows]


async def has_backlog_before(
    session: AsyncSession, student_id: UUID, event_id: int
) -> bool:
    """Is there an older unapplied event of this student?

    The live dispatch path asks this before projecting a fresh answer: a new
    event must not overtake an older pending one, or the state the newer
    event is computed from is the wrong one (§11 A2).
    """
    found = await session.scalar(
        select(EventRow.id)
        .where(
            EventRow.student_id == student_id,
            EventRow.processed_at.is_(None),
            EventRow.id < event_id,
            EventRow.type.in_(_VALUES),
        )
        .limit(1)
    )
    return found is not None
