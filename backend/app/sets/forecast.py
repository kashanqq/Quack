"""Forecast readiness — memory-architecture-quack.md §4.7.

Phase 1: signature only.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.config import KnowledgeParams
from app.schemas.knowledge import ExamFormat, KnowledgeStateOut, SkillWeight


class Forecast(BaseModel):
    predicted_raw: float
    coverage: float
    ready_by: date | None = None
    on_track: bool = False


def forecast(
    states: list[KnowledgeStateOut],
    skill_weights: list[SkillWeight],
    exam_format: ExamFormat,
    params: KnowledgeParams,
) -> Forecast:
    """Phase 2: predicted_raw = Σ weight × p_recall; ready_by from hours_needed."""
    raise NotImplementedError("phase 2")