"""B2 roadmap progress interface."""

from app.schemas.knowledge import SkillStateView
from app.schemas.roadmap import ExamProgress


def exam_progress(
    requirement,
    states: list[SkillStateView],
    forecast,
    milestones,
) -> ExamProgress:
    """Contract: 00-contracts-phase2.md §7.3."""
    raise NotImplementedError("phase 2")
