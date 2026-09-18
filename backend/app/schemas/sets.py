"""Phase 2 set and topic contracts."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel

from app.schemas.common import ExamId, SetStatus, SkillLevel, TopicKind
from app.schemas.knowledge import ForecastOut


class TopicOut(BaseModel):
    skill_id: str
    name: str
    kind: TopicKind
    position: int
    status: Literal["open", "closed"]
    level: SkillLevel
    is_root: bool
    misconception_labels: list[str]
    subtitle: str | None


class SetProgress(BaseModel):
    topics_closed: int
    topics_total: int
    tasks_answered: int
    tasks_correct: int


class SetOut(BaseModel):
    id: UUID
    exam_id: ExamId
    area_ids: list[str]
    status: SetStatus
    kind: Literal["regular", "review", "consolidation"]
    position: int
    deadline: date
    reason: str
    topics: list[TopicOut]
    progress: SetProgress
    opened_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None


class SetsByExam(BaseModel):
    exam_id: ExamId
    forecast: ForecastOut | None
    current: SetOut | None
    upcoming: list[SetOut]
    done: list[SetOut]


class SetSwitchIn(BaseModel):
    set_id: UUID


class SetEditIn(BaseModel):
    skill_ids: list[str] | None
    deadline: date | None
