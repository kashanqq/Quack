"""Shared repository response types."""

from typing import Literal

from pydantic import BaseModel

ExamId = Literal["SAT_MATH", "ENT_MATH"]
TaskType = Literal["mcq4", "mcq5", "multi_select", "numeric"]


class Page[T](BaseModel):
    items: list[T]
    total: int
