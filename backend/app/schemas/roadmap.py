"""Phase 2 roadmap presentation contracts."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel

from app.schemas.common import ExamId, Source
from app.schemas.knowledge import ForecastOut, TestDate
from app.schemas.sets import SetStats


class ExamRequirementOut(BaseModel):
    exam_id: ExamId
    target_score: float
    target_source: Literal["programs", "manual"]
    max_raw_score: float
    program_ids: list[str]
    test_dates: list[TestDate]
    has_knowledge_model: bool
    current_estimate: float | None
    estimate_note: str


class MilestoneOut(BaseModel):
    key: str
    kind: Literal[
        "registration", "test", "application", "document", "scholarship", "window"
    ]
    date: date
    title: str
    exam_id: ExamId | None
    program_id: str | None
    source: Source
    done: bool
    done_at: AwareDatetime | None = None


class ConflictOut(BaseModel):
    kind: Literal["same_day_applications", "exclusive_rounds", "exam_after_deadline"]
    milestone_keys: list[str]
    text: str
    options: list[str]


class ExamProgress(BaseModel):
    exam_id: ExamId
    readiness: float
    forecast: ForecastOut | None
    milestones_done: int
    milestones_total: int


class SetSummaryOut(BaseModel):
    """Phase 4 (§14.3): `stats` is typed and the row carries its status."""

    set_id: UUID
    exam_id: ExamId | None = None
    status: Literal["generating", "ready", "failed"] = "ready"
    text: str | None
    stats: SetStats
    prompt_version: str | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime | None = None


class OverviewOut(BaseModel):
    requirements: list[ExamRequirementOut]
    milestones: list[MilestoneOut]
    conflicts: list[ConflictOut]
    progress: list[ExamProgress]
    last_set_summary: SetSummaryOut | None
