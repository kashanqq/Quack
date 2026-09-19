"""Typed tool results of the selection assistant and the tutor.

Source: docs/tz/phase3-agents.md §3.3, §3.5, §5.1 (C3).

One model per tool: the registry serializes it to a dict that goes both to
the model (`role=tool`) and to the frontend (`tool_result.data`). Every
number or date the model is allowed to name must be a field here — the
postcheck (§3.6) compares the reply against exactly these values.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import FactorStatus, Realism, Source
from app.schemas.knowledge import (
    AdmissionRouteOut,
    Direction,
    EvidenceSource,
    ExamFormat,
    FactOut,
    TestDate,
    Tier,
)
from app.schemas.matching import FactorOut, ShiftOut
from app.schemas.profile import ProfileFieldMark
from app.schemas.programs import Program
from app.schemas.roadmap import ExamRequirementOut
from app.schemas.tasks import TaskInstanceOut

# --- per-turn state (ToolCtx.turn) ---


class TurnState(BaseModel):
    """Counters of one chat turn, shared by every tool call of that turn.

    Read and written dict-style by the tool bodies (`turn["task_issued"]`),
    because the tutor and the selection assistant keep different counters.
    """

    model_config = ConfigDict(extra="allow", validate_assignment=False)

    matching_calls: int = 0
    task_issued: int = 0
    gave_task_instance_id: UUID | None = None

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


# --- selection tools ---


class ProfileUpdateResult(BaseModel):
    path: str
    value: Any
    mark: ProfileFieldMark | None
    readiness: float
    unchanged: bool
    shift: list[ShiftOut] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class MatchCard(BaseModel):
    program_id: str
    university: str
    direction: str
    country: str
    city: str
    language: str
    realism: Realism
    score: float
    tuition_per_year: int | None
    living_per_year: int | None
    currency: str
    factors: list[FactorOut]
    assumptions: list[str]
    source: Source


class RunMatchingResult(BaseModel):
    count: int
    total: int
    forecast_used: bool
    empty_reason: str | None
    profile_readiness: float
    items: list[MatchCard]


class SnapshotFactor(BaseModel):
    id: str
    status: FactorStatus


class SnapshotItem(BaseModel):
    program_id: str
    university: str
    direction: str
    realism: Realism
    score: float
    factors: list[SnapshotFactor]


class MatchingSnapshot(BaseModel):
    """The last matching shown in the selection chat (Redis, 7 days)."""

    items: list[SnapshotItem]
    as_of: datetime


class SaveProgramResult(BaseModel):
    program_id: str
    saved_count: int
    exams: list[ExamRequirementOut]


class ProgramFactsResult(BaseModel):
    program: Program
    source: Source


class AdmissionRouteResult(BaseModel):
    country_id: str
    routes: list[AdmissionRouteOut]
    facts: list[FactOut]


class ExamFormatResult(BaseModel):
    format: ExamFormat
    test_dates: list[TestDate]
    facts: list[FactOut]


class TuitionStats(BaseModel):
    min: int | None
    median: float | None
    max: int | None
    currency_mix: list[str]


class ExamThreshold(BaseModel):
    min: float
    max: float


class DatasetProgram(BaseModel):
    program_id: str
    university: str
    city: str
    country: str
    tuition_per_year: int | None
    currency: str


class DatasetAggregateOut(BaseModel):
    question: str
    filters: dict[str, Any]
    count: int
    by_country: dict[str, int]
    by_direction: dict[str, int]
    tuition: TuitionStats
    free_count: int
    with_scholarship_note: int
    languages: dict[str, int]
    exam_thresholds: dict[str, ExamThreshold]
    programs: list[DatasetProgram]
    sources: list[Source]
    profile_filtered: bool


# --- tutor tools ---


class BeliefTask(BaseModel):
    instance_id: UUID
    stem: str
    student_answer: Any = None
    correct: bool | None = None


class BeliefMessage(BaseModel):
    message_id: UUID
    text_fragment: str
    created_at: datetime


class BeliefItem(BaseModel):
    evidence_id: str
    event_id: int
    kind: str
    source: EvidenceSource
    tier: Tier
    direction: Direction
    weight: float
    observed_at: datetime
    summary: str | None
    task: BeliefTask | None = None
    message: BeliefMessage | None = None


class ExplainBeliefResult(BaseModel):
    node_id: str
    node_kind: Literal["skill", "misconception"]
    items: list[BeliefItem]


class GetTaskResult(BaseModel):
    """The issued task as the student sees it: no key, no `correct`, no
    misconception behind an option (`OptionOut` has only key and text)."""

    task: TaskInstanceOut
    hint_level: int
