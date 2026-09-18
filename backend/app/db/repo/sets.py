"""Phase 2 set repository interfaces; derived SetOut needs graph data."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import ExamId, SetStatus
from app.schemas.sets import SetOut, SetProgress

if TYPE_CHECKING:
    from app.sets.assemble import SetPlan


async def list_sets(
    session: AsyncSession, student_id: UUID, exam_id: ExamId
) -> list[SetOut]:
    """Return student-owned sets once SetOut enrichment is agreed."""
    raise NotImplementedError("phase 2")


async def get_set(
    session: AsyncSession, student_id: UUID, set_id: UUID
) -> SetOut | None:
    """Return a student-owned set once SetOut enrichment is agreed."""
    raise NotImplementedError("phase 2")


async def replace_plan(
    session: AsyncSession,
    student_id: UUID,
    exam_id: ExamId,
    plans: list[SetPlan],
    keep_current: bool,
) -> list[SetOut]:
    """Replace a plan atomically under the Phase 2 set rules."""
    raise NotImplementedError("phase 2")


async def set_status(
    session: AsyncSession, student_id: UUID, set_id: UUID, status: SetStatus
) -> None:
    """Set status for a student-owned set."""
    raise NotImplementedError("phase 2")


async def set_topic_status(
    session: AsyncSession,
    set_id: UUID,
    skill_id: str,
    status: Literal["open", "closed"],
) -> None:
    """Set the status of one topic."""
    raise NotImplementedError("phase 2")


async def update_set(
    session: AsyncSession,
    student_id: UUID,
    set_id: UUID,
    skill_ids: list[str] | None,
    deadline: date | None,
) -> None:
    """Update the editable fields of a student-owned set."""
    raise NotImplementedError("phase 2")


async def count_progress(
    session: AsyncSession, student_id: UUID, set_id: UUID
) -> SetProgress:
    """Count topic and task progress for a student-owned set."""
    raise NotImplementedError("phase 2")
