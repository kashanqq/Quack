"""Set summaries — the "previous set" slot of the tutor context (§9.2).

Phase 3 only reads: `set_summary` (the job that writes the table) is phase 4,
so `get_latest_text` returns None until then; the field is wired through so
the context and the observer do not change when it lands.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SetSummary


async def get_latest_text(
    session: AsyncSession, student_id: UUID, before_set_id: UUID | None = None
) -> str | None:
    """Text of the student's latest set summary other than `before_set_id`."""
    statement = select(SetSummary.text).where(SetSummary.student_id == student_id)
    if before_set_id is not None:
        statement = statement.where(SetSummary.set_id != before_set_id)
    return await session.scalar(
        statement.order_by(SetSummary.created_at.desc()).limit(1)
    )
