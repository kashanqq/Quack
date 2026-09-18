"""B1 diagnostic apply interfaces."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.dispatch import RuleDeps
from app.schemas.common import ExamId
from app.schemas.diagnostic import DiagnosticOut, DiagnosticResult
from app.schemas.tasks import AnswerResult


async def start(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    exam_id: ExamId,
    n_tasks: int | None,
) -> DiagnosticOut:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")


async def answer(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    run_id: UUID,
    result: AnswerResult,
) -> DiagnosticOut:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")


async def finish(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, run_id: UUID
) -> DiagnosticResult:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")
