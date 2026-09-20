"""Shared event and Phase 1 payload contracts."""

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ErrorClass, ExamId, MockKind, TaskMode
from app.schemas.diagnostic import DiagnosticResult, DiagnosticState
from app.schemas.observer import Observation
from app.schemas.quack import RecKind, RecommendationAction


class EventType(StrEnum):
    message_user = "message.user"
    message_assistant = "message.assistant"
    task_issued = "task.issued"
    task_answered = "task.answered"
    task_skipped = "task.skipped"
    task_timed_out = "task.timed_out"
    mock_started = "mock.started"
    mock_completed = "mock.completed"
    diagnostic_progress = "diagnostic.progress"
    diagnostic_completed = "diagnostic.completed"
    observation_extracted = "observation.extracted"
    observer_requested = "observer.requested"
    set_opened = "set.opened"
    set_completed = "set.completed"
    set_switched_by_user = "set.switched_by_user"
    set_deadline_changed = "set.deadline_changed"
    topic_opened = "topic.opened"
    topic_completed = "topic.completed"
    misconception_disputed = "misconception.disputed"
    misconception_undisputed = "misconception.undisputed"
    skill_personal_created = "skill.personal_created"
    misconception_personal_created = "misconception.personal_created"
    misconception_canonized = "misconception.canonized"
    profile_updated = "profile.updated"
    program_saved = "program.saved"
    program_removed = "program.removed"
    milestone_done = "milestone.done"
    recommendation_accepted = "recommendation.accepted"
    recommendation_declined = "recommendation.declined"
    guideline_opened = "guideline.opened"
    explanation_opened = "explanation.opened"
    job_failed = "job.failed"


class EventIn(BaseModel):
    type: EventType
    payload: dict[str, Any]
    student_id: UUID
    session_id: UUID | None = None
    exam_id: ExamId | None = None
    set_id: UUID | None = None
    topic_skill_id: str | None = None
    chat_id: UUID | None = None
    occurred_at: datetime | None = None
    extractor_version: str | None = None
    source_event_ids: list[int] | None = None


class Event(EventIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    ingested_at: datetime
    processed_at: datetime | None = None


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MessageUserPayload(_Payload):
    text: str


class MessageAssistantPayload(_Payload):
    text: str
    mode: Literal["explain", "review", "task"] | None = None
    gave_task_instance_id: UUID | None = None
    hint_level: int | None = None
    referenced_skill_ids: list[str]


class TaskIssuedPayload(_Payload):
    instance_id: UUID
    template_id: str
    skill_id: str
    mode: TaskMode
    via: Literal["topic", "mock", "diagnostic", "chat"]


class TaskAnsweredPayload(_Payload):
    instance_id: UUID
    answer: Any
    time_spent_sec: int
    mode: TaskMode
    session_minute: int
    after_guideline: bool
    hint_level_before: int


class ProfileUpdatedPayload(_Payload):
    field: str
    value: Any
    by: Literal["assistant", "user"]


class ProgramSavedPayload(_Payload):
    program_id: str


class TaskSkippedPayload(_Payload):
    instance_id: UUID
    mode: TaskMode
    time_spent_sec: int


class DiagnosticProgressPayload(_Payload):
    run_id: UUID
    state: DiagnosticState


class DiagnosticCompletedPayload(_Payload):
    run_id: UUID
    result: DiagnosticResult


class MockStartedPayload(_Payload):
    run_id: UUID
    kind: MockKind
    exam_id: ExamId
    predicted_before: float | None


class MockCompletedPayload(_Payload):
    run_id: UUID
    raw_score: float
    scaled_score: float | None
    predicted_before: float | None


class SetOpenedPayload(_Payload):
    set_id: UUID
    skill_ids: list[str]


class SetCompletedPayload(_Payload):
    set_id: UUID


class SetSwitchedByUserPayload(_Payload):
    from_set_id: UUID | None
    to_set_id: UUID


class SetDeadlineChangedPayload(_Payload):
    set_id: UUID
    old: date
    new: date


class TopicOpenedPayload(_Payload):
    set_id: UUID
    skill_id: str


class TopicCompletedPayload(_Payload):
    set_id: UUID
    skill_id: str


class MisconceptionDisputedPayload(_Payload):
    misconception_id: str


class MilestoneDonePayload(_Payload):
    milestone_key: str
    done: bool


# --- phase 3: observer, canonization, job failures (phase3-agents §5.1 C5) ---


class ObservationExtractedPayload(_Payload):
    """The observer's output, whole — including observations the rule will
    later skip (low confidence, unknown ids): the event records what the model
    said, the rule decides what to apply."""

    observations: list[Observation]
    window_from_event_id: int | None
    window_to_event_id: int | None
    topic_skill_id: str | None
    set_id: UUID
    exam_id: ExamId
    model: str
    raw_count: int


class ObserverRequestedPayload(_Payload):
    reason: Literal["button"] = "button"


class JobFailedPayload(_Payload):
    job: str
    job_id: str | None
    reason: str
    args: dict[str, Any]


class MisconceptionCanonizedPayload(_Payload):
    source_event_id: int
    ordinal: int
    skill_id: str
    canonical_id: str
    similarity: float
    decided_by: Literal["threshold", "model"]
    name: str
    description: str
    error_class: ErrorClass


class MisconceptionPersonalCreatedPayload(_Payload):
    misconception_id: str
    source_event_id: int
    ordinal: int
    skill_id: str
    name: str
    description: str
    error_class: ErrorClass
    embedding: list[float]
    best_similarity: float | None


# --- phase 4: recommendations and generated texts (§14.8) ---


class RecommendationAcceptedPayload(_Payload):
    recommendation_id: UUID
    reason_hash: str
    kind: RecKind
    action: RecommendationAction


class RecommendationDeclinedPayload(_Payload):
    recommendation_id: UUID
    reason_hash: str
    kind: RecKind
    reason: str | None = None


class TextOpenedPayload(_Payload):
    """`guideline.opened` / `explanation.opened` — §3.5."""

    set_id: UUID
    skill_id: str
    kind: Literal["guideline", "explanation"]
    text_hash: str
