"""Shared repository response types."""

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


class Page[T](BaseModel):
    items: list[T]
    total: int
