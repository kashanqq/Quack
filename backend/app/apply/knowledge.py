"""B1 knowledge view apply interfaces."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.dispatch import RuleDeps
from app.schemas.common import ExamId
from app.schemas.knowledge import (
    EvidenceOut,
    MisconceptionStateOut,
    SkillStateView,
)


async def states_view(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, exam_id: ExamId
) -> list[SkillStateView]:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")


async def misconceptions_view(
    deps: RuleDeps, student_id: UUID, exam_id: ExamId
) -> list[MisconceptionStateOut]:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")


async def explain(deps: RuleDeps, student_id: UUID, node_id: str) -> list[EvidenceOut]:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")
