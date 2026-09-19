"""Shared repository response types."""

from datetime import date
from typing import Literal

from pydantic import BaseModel

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


class Source(BaseModel):
    label: str
    url: str | None
    checked_at: date | None
    is_demo: bool


class Page[T](BaseModel):
    items: list[T]
    total: int
