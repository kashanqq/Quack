"""Shared knowledge-layer contracts for Phases 1 and 2."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel

from app.schemas.common import SkillLevel

ExamId = Literal["SAT_MATH", "ENT_MATH"]
Tier = Literal[1, 2, 3]
TaskMode = Literal[
    "topic", "mock_set", "mock_topic", "mock_misconception", "diagnostic", "chat"
]
TaskType = Literal["mcq4", "mcq5", "multi_select", "numeric"]
ErrorClass = Literal["computational", "conceptual", "attention", "procedural"]
Direction = Literal[1, -1, 0]
EvidenceSource = Literal["task", "mock", "diagnostic", "chat", "self_report"]
MisconceptionStatus = Literal["suspected", "confirmed", "resolved", "disputed"]


class SkillRef(BaseModel):
    id: str
    name: str
    description: str
    exam_ids: list[ExamId]
    effort_h: float
    base_half_life_h: float | None = None


class SkillWeight(BaseModel):
    skill: SkillRef
    area_id: str
    weight: float


class AreaOut(BaseModel):
    id: str
    name: str
    score_share: float


class Prerequisite(BaseModel):
    skill_id: str
    strength: float
    depth: int


class KnowledgeStateOut(BaseModel):
    skill_id: str
    exam_id: ExamId
    p_recall: float
    p_at_obs: float
    half_life_h: float
    confidence: float
    evidence_mass: float
    n_correct: int
    n_incorrect: int
    n_partial: int
    has_strong: bool
    last_observed_at: datetime
    created_at: datetime


class EvidenceContext(BaseModel):
    task_type: TaskType | None = None
    difficulty: int | None = None
    tags: list[str] | None = None
    mode: TaskMode | None = None
    time_ratio: float | None = None
    session_minute: int | None = None
    after_guideline: bool | None = None
    hint_level_before: int | None = None
    topic_skill_id: str | None = None
    session_id: Any | None = None


class EvidenceIn(BaseModel):
    event_id: int
    skill_id: str
    exam_id: ExamId
    kind: str
    tier: Tier
    source: EvidenceSource
    weight: float
    direction: Direction
    share: float | None = None
    difficulty_factor: float = 1.0
    summary: str | None = None
    context: EvidenceContext | None = None
    observed_at: datetime
    extractor_version: str | None = None


class MisconceptionRef(BaseModel):
    id: str
    name: str
    description: str
    error_class: ErrorClass
    skill_ids: list[str]


class Section(BaseModel):
    name: str
    n_items: int
    minutes: int
    item_types: dict[str, int]
    scoring_rule: str
    calculator: bool
    adaptive: bool
    area_shares: dict[str, float]
    difficulty_shares: dict[str, float]
    answer_forms: list[str]


class ExamFormat(BaseModel):
    exam_id: ExamId
    name: str
    max_raw_score: float
    sections: list[Section]
    scale_table: dict[str, Any] | None = None
    scale_note: str | None = None
    source: str
    checked_at: date
    is_demo: bool


class TestDate(BaseModel):
    exam_id: ExamId
    date: date
    registration_deadline: date
    late_deadline: date | None = None
    source: str
    checked_at: date
    is_demo: bool


class AdmissionRouteOut(BaseModel):
    id: str
    name: str
    description: str
    country_id: str
    requirements: list[dict[str, Any]]
    source: str | None = None
    is_demo: bool


class FactOut(BaseModel):
    text: str
    source: str | None = None
    checked_at: date | None = None
    is_demo: bool


class MisconceptionStateOut(BaseModel):
    """State of one misconception for one student — memory-architecture §5."""

    misconception_id: str
    name: str
    status: MisconceptionStatus
    occurrence_count: int
    strong_count: int
    consecutive_avoided: int
    triggers: dict[str, Any]
    first_seen_at: AwareDatetime
    updated_at: AwareDatetime
    skill_ids: list[str]
    visible_label: str = ""


class EvidenceOut(BaseModel):
    evidence_id: str
    event_id: int
    skill_id: str
    kind: str
    tier: Tier
    source: EvidenceSource
    weight: float
    direction: Direction
    observed_at: AwareDatetime
    summary: str | None
    instance_id: UUID | None
    message_id: UUID | None


class RootCauseOut(BaseModel):
    """One edge from evidence to a root skill — memory-architecture §6."""

    from_skill_id: str
    root_skill_id: str
    confidence: float
    source: Literal["diagnostic", "observer", "rule"]
    created_at: AwareDatetime


class SkillStateView(BaseModel):
    skill_id: str
    name: str
    area_id: str
    exam_id: ExamId
    weight: float
    p_target: float
    level: SkillLevel
    p_recall: float
    confidence: float
    trend: Literal["up", "flat", "down"]
    due_at: AwareDatetime | None
    is_root: bool
    n_evidence: int


class ForecastOut(BaseModel):
    exam_id: ExamId
    predicted_raw: float
    predicted_scaled: float | None
    coverage: float
    hours_needed: float
    ready_by: date | None
    test_date: date | None
    on_track: bool | None
    as_of_event_id: int
    note: str


class MisconceptionChange(BaseModel):
    misconception_id: str
    from_status: MisconceptionStatus | None
    to_status: MisconceptionStatus
    counters: dict[str, Any]


class ReconcileResult(BaseModel):
    evidence: list[EvidenceIn]
    state_after: KnowledgeStateOut
    cross_exam_state: KnowledgeStateOut | None
    misconception_change: MisconceptionChange | None
    root_causes: list[RootCauseOut]
    words: str
