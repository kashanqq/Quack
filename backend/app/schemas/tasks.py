"""Task persistence contracts from the shared Phase 1 specification."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ExamId, TaskType


class ParamSpec(BaseModel):
    range: tuple[int, int] | None = None
    choices: list[Any] | None = None


class DistractorSpec(BaseModel):
    expr: str
    misconception_id: str | None = None


class OmissionTrap(BaseModel):
    omit: str
    misconception_id: str | None = None


class TaskTemplateSpec(BaseModel):
    id: str
    exam_id: ExamId
    type: TaskType
    difficulty: int
    skill_id: str
    tags: list[str]
    time_reference_sec: int
    kind: Literal["template", "manual"] = "template"
    params: dict[str, ParamSpec]
    constraints: list[str]
    stem: str
    correct: str | list[str]
    distractors: list[DistractorSpec]
    omission_traps: list[OmissionTrap] | None = None
    answer_forms: list[str] | None = None
    trap_answers: list[DistractorSpec] | None = None
    solution: list[str]
    generator: str | None = None
    figure: str | None = None


class Option(BaseModel):
    key: str
    text: str
    correct: bool
    misconception_id: str | None = None


class TaskInstance(BaseModel):
    id: UUID
    template_id: str
    seed: int
    exam_id: ExamId
    type: TaskType
    skill_id: str
    stem_rendered: str
    options: list[Option]
    answer: Any
    trap_answers: list[Option]
    solution_rendered: list[str]
    figure_url: str | None = None
    time_reference_sec: int
    difficulty: int
    tags: list[str]



class Grade(BaseModel):
    correct: bool
    matched_misconception_id: str | None = None
    partial: float | None = None
    omitted_misconception_ids: list[str] = []


class AnswerIn(BaseModel):
    instance_id: UUID
    answer: Any
    time_spent_sec: int
    mode: str
    after_guideline: bool = False
    hint_level_before: int = 0


class AnswerResult(BaseModel):
    grade: Grade
    solution: list[str]
    state_after: Any = None
    misconception_change: str | None = None