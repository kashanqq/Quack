"""Phase 2 diagnostic contracts."""

from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ExamId, RunStatus
from app.schemas.knowledge import RootCauseOut
from app.schemas.tasks import TaskInstanceOut


class DiagnosticState(BaseModel):
    exam_id: ExamId
    budget_left: int
    reserve_left: int
    asked: list[UUID]
    answered: int
    pending_descent: list[str]
    reask_queue: list[tuple[str, int]]
    roots_found: list[RootCauseOut]
    trap_hits: list[str]
    firm: list[str]
    shaky: list[str]
    last_grade_correct: bool | None


class DiagnosticOut(BaseModel):
    run_id: UUID
    status: RunStatus
    state: DiagnosticState
    next_task: TaskInstanceOut | None


class DiagnosticResult(BaseModel):
    firm: list[str]
    shaky: list[str]
    roots: list[RootCauseOut]
    suspected: list[str]
    start_from: list[str]
    words: str


class DiagnosticStartIn(BaseModel):
    exam_id: ExamId
    n_tasks: int | None
