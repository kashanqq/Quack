"""B1 set apply interfaces."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.dispatch import RuleDeps
from app.schemas.common import ExamId
from app.schemas.events import Event
from app.schemas.sets import SetOut, SetsByExam


async def rebuild_sets(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    exam_id: ExamId,
) -> SetsByExam:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")


async def open_set(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, set_id: UUID
) -> SetOut:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")


async def on_program_change(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> None:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")


async def on_set_change(session: AsyncSession, event: Event, deps: RuleDeps) -> None:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")


async def on_run_completed(session: AsyncSession, event: Event, deps: RuleDeps) -> None:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")
