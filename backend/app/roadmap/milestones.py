"""B2 roadmap milestone interface."""

from datetime import datetime

from app.schemas.knowledge import TestDate
from app.schemas.roadmap import MilestoneOut


def build_milestones(
    saved,
    requirements,
    test_dates,
    calendars: list[TestDate],
    marks: dict[str, datetime],
    today,
) -> list[MilestoneOut]:
    """Contract: 00-contracts-phase2.md §7.3."""
    raise NotImplementedError("phase 2")
