"""Phase 2 set and topic contracts."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field

from app.schemas.common import AvailabilityOut, ExamId, SetStatus, SkillLevel, TopicKind
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
    # Phase 5 (D03): additive and optional. `mode="static"` says the plan is
    # the persisted one and the graph could not be asked; `forecast` is then
    # `None`, never a zero dressed up as a prediction (§11 A3).
    availability: AvailabilityOut | None = None


class SetSwitchIn(BaseModel):
    set_id: UUID


class SetEditIn(BaseModel):
    skill_ids: list[str] | None
    deadline: date | None


# --- phase 4: the end-of-set report (§4.2, §14.3) ---


class SkillDelta(BaseModel):
    skill_id: str
    name: str
    level_before: SkillLevel
    level_after: SkillLevel
    p_before: float
    p_after: float
    delta_p: float


class MisconceptionBrief(BaseModel):
    id: str
    name: str


class NextSetBrief(BaseModel):
    set_id: UUID
    deadline: date
    topic_names: list[str]


class SetStats(BaseModel):
    """Facts the summary prompt is allowed to speak about — nothing else."""

    set_id: UUID
    exam_id: ExamId
    kind: Literal["regular", "review", "consolidation"]
    opened_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    deadline: date
    days_in_set: int = 0
    # +2 — закрыт на два дня раньше дедлайна, −3 — на три позже.
    days_vs_deadline: int = 0
    tasks_answered: int = 0
    tasks_correct: int = 0
    mocks_completed: int = 0
    skills_total: int = 0
    skills_closed: int = 0
    skills: list[SkillDelta] = Field(default_factory=list)
    top_growth: list[str] = Field(default_factory=list)
    misconceptions_resolved: list[MisconceptionBrief] = Field(default_factory=list)
    misconceptions_still_watching: list[MisconceptionBrief] = Field(
        default_factory=list
    )
    misconceptions_new_confirmed: list[MisconceptionBrief] = Field(default_factory=list)
    forecast_before: ForecastOut | None = None
    forecast_after: ForecastOut | None = None
    on_track_after: bool | None = None
    ready_by_shift_days: int | None = None
    next_set: NextSetBrief | None = None
    previous_summary_id: UUID | None = None
