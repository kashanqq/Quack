"""Task persistence contracts from the shared Phase 1 specification."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ExamId, ProjectionStatus, TaskMode, TaskType
from app.schemas.knowledge import MisconceptionChange


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


class OptionOut(BaseModel):
    key: str
    text: str


class TaskInstanceOut(BaseModel):
    id: UUID
    template_id: str
    exam_id: ExamId
    type: TaskType
    skill_id: str
    stem_rendered: str
    options: list[OptionOut]
    figure_url: str | None
    time_reference_sec: int
    difficulty: int
    tags: list[str]
    mode: TaskMode
    provenance: Literal["template", "manual"]


class TaskRequestIn(BaseModel):
    skill_id: str | None
    set_id: UUID | None
    mode: TaskMode = "topic"
    with_trap: str | None
    exclude_seen: bool = True
    # Запрошенная сложность по шкале экзамена (1–5). Её заполняет репетитор
    # через `get_task(GetTaskArgs.difficulty)`; пусто — сложность выбирается
    # по последним ответам ученика (tasks.select).
    difficulty: int | None = None


class TaskSkipIn(BaseModel):
    instance_id: UUID
    reason: Literal["skipped", "timed_out"]
    time_spent_sec: int


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
    misconception_change: MisconceptionChange | None = None
    state_words: str
    knowledge_version: int
    # Phase 5 (D03), additive with a default so no existing client breaks.
    # `pending` means the answer and its grade are stored and final, and only
    # the knowledge projection is still owed — `state_after` is `None` and
    # `state_words` says nothing rather than something invented.
    projection_status: ProjectionStatus = "applied"
