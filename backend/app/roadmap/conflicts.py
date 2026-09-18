"""B2 roadmap conflict interface."""

from datetime import date

from app.schemas.common import ExamId
from app.schemas.roadmap import ConflictOut


def find_conflicts(
    milestones,
    saved,
    planned_test_dates: dict[ExamId, date | None],
) -> list[ConflictOut]:
    """Contract: 00-contracts-phase2.md §7.3."""
    raise NotImplementedError("phase 2")
