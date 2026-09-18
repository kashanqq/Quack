"""Phase 2 mock-exam contracts."""

from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ExamId, MockKind, RunStatus
from app.schemas.knowledge import SkillStateView
from app.schemas.tasks import TaskInstanceOut


class MockStartIn(BaseModel):
    kind: MockKind
    exam_id: ExamId
    set_id: UUID | None
    skill_id: str | None
    misconception_id: str | None


class MockOut(BaseModel):
    run_id: UUID
    kind: MockKind
    exam_id: ExamId
    section_name: str
    status: RunStatus
    tasks: list[TaskInstanceOut]
    minutes: int
    answered: int
    predicted_before: float | None


class MockResultOut(BaseModel):
    run_id: UUID
    raw_score: float
    max_raw: float
    scaled_score: float | None
    scale_note: str | None
    per_skill: list[SkillStateView]
    brier_point: float | None
