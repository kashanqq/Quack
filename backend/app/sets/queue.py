"""Queue of skills to study — memory-architecture-quack.md §10.1.

Phase 2: rank skills by need × urgency, prerequisites first.
Phase 1: signature only.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.config import KnowledgeParams
from app.schemas.knowledge import KnowledgeStateOut, Prerequisite, SkillWeight


class QueueItem(BaseModel):
    skill_id: str
    exam_id: str
    need: float
    urgency: float
    is_root: bool = False


def build_queue(
    states: list[KnowledgeStateOut],
    skill_weights: list[SkillWeight],
    prerequisites: list[Prerequisite],
    days_to_test: int,
    params: KnowledgeParams,
) -> list[QueueItem]:
    """Phase 2: rank skills (weight × gap) and (test proximity), prerequisites first."""
    raise NotImplementedError("phase 2")
