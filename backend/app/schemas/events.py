"""Shared event and Phase 1 payload contracts."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ExamId

TaskMode = Literal[
    "topic", "mock_set", "mock_topic", "mock_misconception", "diagnostic", "chat"
]


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
