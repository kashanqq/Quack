"""Observer contracts — structured output, window, rule result, button diff.

Source: docs/tz/phase3-agents.md §3.8–§3.12, §5.1 (C1, C2);
memory-architecture-quack.md §8.1.

`Observation` / `ObservationOut` moved here from `app/agents/observer.py`
(which re-exports them): the `observation.extracted` payload is validated by
`events.store`, and `schemas` may not import `agents`. The fields are the
phase-1 contract, unchanged.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.chat import AssistantMarkup
from app.schemas.common import ErrorClass, ExamId, SkillLevel, TaskType
from app.schemas.knowledge import (
    MisconceptionChange,
    MisconceptionStateOut,
    MisconceptionStatus,
    SkillStateView,
)
from app.schemas.tasks import OptionOut

ObservationKind = Literal[
    "solution_step",
    "task_in_chat",
    "applied",
    "confusion",
    "question",
    "avoided_trap",
    "root_hint",
    "proposed_misconception",
    "pace_signal",
]

# Fields each kind must fill, beyond `kind` itself — mirrors the promises
# made to the model in app/agents/prompts/observer_v1.md ("Виды наблюдений
# (kind) и что для каждого обязательно заполнить"), which is the source of
# truth here: ТЗ §5.4's own list of examples is not exhaustive (it says
# "например"), so this table also covers applied/confusion/question/
# avoided_trap, which the ТЗ examples don't mention but the prompt does.
_REQUIRED_FIELDS: dict[ObservationKind, tuple[str, ...]] = {
    "solution_step": ("outcome", "skill_id"),
    "task_in_chat": ("instance_id", "answer"),
    "applied": ("skill_id",),
    "confusion": ("skill_id",),
    "question": ("skill_id",),
    "avoided_trap": ("skill_id", "misconception_id"),
    "root_hint": ("skill_id", "root_skill_id"),
    "proposed_misconception": ("name", "description", "error_class"),
    "pace_signal": ("signal",),
}


class Observation(BaseModel):
    kind: ObservationKind
    outcome: Literal["correct", "incorrect"] | None = None
    skill_id: str | None = None
    misconception_id: str | None = None
    root_skill_id: str | None = None
    instance_id: str | None = None
    answer: str | None = None
    name: str | None = None
    description: str | None = None
    error_class: ErrorClass | None = None
    signal: str | None = None
    summary: str | None = Field(default=None, max_length=300)
    event_ids: list[int]
    # `pace_signal` is the one kind the memory-architecture §8.1 example
    # emits without a confidence field at all (payload has only `signal`
    # and `event_ids`) — that example must validate byte-for-byte, so
    # confidence can't be flatly required. But §8.1's own rule ("при
    # сомнении низкий confidence, а не пропуск") means a *missing*
    # confidence on any other kind is a modeling mistake, not a shrug —
    # defaulting it to 1.0 silently made a forgotten field read as
    # maximum certainty and sail through `observer_min_confidence`. So
    # the omission is accepted only for `pace_signal` (which never gates
    # evidence weight downstream, §8.1's kind table has "—" for it); for
    # the other eight kinds, a missing confidence is now a validation
    # error. Narrowed from the earlier blanket default=1.0 — see
    # docs/sync-log.md.
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def _check_required_for_kind(self) -> Observation:
        missing = [
            field_name
            for field_name in _REQUIRED_FIELDS[self.kind]
            if getattr(self, field_name) is None
        ]
        if self.confidence is None and self.kind != "pace_signal":
            missing.append("confidence")
        if missing:
            raise ValueError(
                f"observation kind {self.kind!r} is missing required "
                f"field(s): {', '.join(missing)}"
            )
        return self


class ObservationOut(BaseModel):
    observations: list[Observation]


# --- observer input (§3.8) ---


class WindowMessage(BaseModel):
    event_id: int
    message_id: UUID | None = None
    role: Literal["user", "assistant"]
    text: str
    markup: AssistantMarkup | None = None
    occurred_at: datetime
    session_id: UUID | None = None


class WindowTask(BaseModel):
    """A task handed over in the chat — without the key, `correct` or the
    misconception behind each option: the observer must not know them."""

    instance_id: UUID
    issued_event_id: int
    skill_id: str
    stem: str
    options: list[OptionOut]
    type: TaskType


class ObserverWindow(BaseModel):
    chat_id: UUID
    student_id: UUID
    exam_id: ExamId
    set_id: UUID
    topic_skill_id: str | None
    messages: list[WindowMessage]
    tasks: list[WindowTask]


class SkillForObserver(BaseModel):
    id: str
    name: str
    description: str
    level: SkillLevel


class MisconceptionForObserver(BaseModel):
    id: str
    name: str
    description: str
    status: MisconceptionStatus | None
    scope: Literal["library", "personal"]


class ObserverContext(BaseModel):
    skills: list[SkillForObserver]
    misconceptions: list[MisconceptionForObserver]
    previous_summary: str | None = None


class ObserverResult(BaseModel):
    out: ObservationOut
    extractor_version: str
    model: str
    raw_count: int


# --- rule result (§3.10) ---


class ObservationApplyResult(BaseModel):
    event_id: int
    applied: int = 0
    skipped: list[tuple[int, str]] = Field(default_factory=list)
    skills_changed: list[str] = Field(default_factory=list)
    misconceptions_changed: list[MisconceptionChange] = Field(default_factory=list)
    task_answered_event_ids: list[int] = Field(default_factory=list)
    pending_canonizations: list[int] = Field(default_factory=list)
    knowledge_version: int = 0


# --- canonization (§3.11) ---


class CanonDecision(BaseModel):
    same: bool
    reason: str = Field(default="", max_length=200)


# --- «обновить модель знаний» (§3.12) ---


class ObservationView(BaseModel):
    event_id: int
    ordinal: int
    kind: ObservationKind
    skill_id: str | None
    skill_name: str | None
    misconception_id: str | None
    summary: str | None
    confidence: float | None
    applied: bool
    message_ids: list[UUID]


class ObservationsDiffOut(BaseModel):
    status: Literal["pending", "done", "failed"]
    observations: list[ObservationView]
    skills: list[SkillStateView]
    misconceptions: list[MisconceptionStateOut]
    knowledge_version: int
    # Машинная причина `failed` (`job.failed.reason`): без неё фронт не
    # отличит «модель недоступна» от «ответ модели не разобран».
    failed_reason: str | None = None


class ObserveRequestIn(BaseModel):
    set_id: UUID
    topic_skill_id: str | None = None


class ObserveRequestedOut(BaseModel):
    job_id: str | None
    since_event_id: int
    knowledge_version: int
