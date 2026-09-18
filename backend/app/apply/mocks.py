"""B1 mock-exam apply interfaces."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.dispatch import RuleDeps
from app.schemas.mocks import MockOut, MockResultOut, MockStartIn
from app.schemas.tasks import AnswerResult


async def start(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, body: MockStartIn
) -> MockOut:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")


async def answer(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    run_id: UUID,
    result: AnswerResult,
) -> MockOut:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")


async def finish(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, run_id: UUID
) -> MockResultOut:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")
