"""B2 roadmap requirement interface."""

from app.config import KnowledgeParams
from app.schemas.common import ExamId
from app.schemas.knowledge import ExamFormat, ForecastOut, TestDate
from app.schemas.profile import Profile
from app.schemas.programs import Program
from app.schemas.roadmap import ExamRequirementOut


def build_requirements(
    saved: list[Program],
    profile: Profile,
    exam_formats: dict[ExamId, ExamFormat],
    test_dates: dict[ExamId, list[TestDate]],
    forecasts: dict[ExamId, ForecastOut | None],
    params: KnowledgeParams,
) -> list[ExamRequirementOut]:
    """Contract: 00-contracts-phase2.md §7.3."""
    raise NotImplementedError("phase 2")
