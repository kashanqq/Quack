"""Shared repository response types."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

ExamId = Literal["SAT_MATH", "ENT_MATH"]
Tier = Literal[1, 2, 3]
TaskMode = Literal[
    "topic", "mock_set", "mock_topic", "mock_misconception", "diagnostic", "chat"
]
TaskType = Literal["mcq4", "mcq5", "multi_select", "numeric"]
ErrorClass = Literal["computational", "conceptual", "attention", "procedural"]
Realism = Literal["impossible", "try", "possible"]
FactorStatus = Literal["below", "in_range", "above", "unknown"]
SkillLevel = Literal["low_data", "weak", "shaky", "solid", "closed"]
SetStatus = Literal["upcoming", "current", "done"]
TopicKind = Literal["topic", "check", "review"]
RunStatus = Literal["active", "completed", "abandoned"]
MockKind = Literal["mock_set", "mock_topic", "mock_misconception"]

# --- phase 4 (§14.1) ---
GeneratedTextStatus = Literal["ready", "generating", "stale", "failed"]
TextKind = Literal["guideline", "explanation", "realism", "compare"]
TextMark = Literal["generated", "saved_version"]


# --- phase 5 (§10, D03) ---
AvailabilityMode = Literal["live", "cached", "static", "unavailable"]
AvailabilityReason = Literal[
    "graph_unavailable", "projection_pending", "search_unavailable"
]
ProjectionStatus = Literal["applied", "pending"]


class AvailabilityOut(BaseModel):
    """How honest a read model is right now (phase 5, D03).

    Additive and optional everywhere it appears: a client that ignores it
    keeps working, and a client that reads it can stop presenting a static
    ordering or an unrefreshed cache as a live answer. `as_of_event_id` is
    only ever a version we actually know — never a guess at "the latest".
    """

    mode: AvailabilityMode
    reason: AvailabilityReason | None = None
    as_of_event_id: int | None = Field(default=None, ge=0)


class Source(BaseModel):
    label: str
    url: str | None
    checked_at: date | None
    is_demo: bool


class Page[T](BaseModel):
    items: list[T]
    total: int
