"""B1 task answer apply interfaces."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.dispatch import RuleDeps
from app.schemas.events import Event
from app.schemas.tasks import AnswerResult


async def apply_task_answered(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> AnswerResult:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")


async def apply_task_skipped(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> None:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")
