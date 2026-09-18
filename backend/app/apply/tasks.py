"""B1 task issuing apply interface."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.dispatch import RuleDeps
from app.schemas.tasks import TaskInstanceOut, TaskRequestIn


async def issue(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, req: TaskRequestIn
) -> TaskInstanceOut:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")
