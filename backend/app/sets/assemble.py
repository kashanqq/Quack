"""Assemble a Set from the queue — memory-architecture-quack.md §10.1.

Phase 1: signature only.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.config import KnowledgeParams
from app.sets.queue import QueueItem


class SetPlan(BaseModel):
    skill_ids: list[str]
    deadline: date
    reason: str


def assemble_set(
    queue: list[QueueItem],
    hours_per_week: int,
    next_test_date: date | None,
    params: KnowledgeParams,
) -> SetPlan:
    """Phase 2: pick top-N skills, set deadline from effort and hours."""
    raise NotImplementedError("phase 2")
