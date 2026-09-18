"""Diagnostic run transport; B1 owns the diagnostic state machine and events."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._answer import owned_instance, record_answer
from app.api.deps import get_current_student, get_rule_deps, get_session
from app.apply import diagnostic as apply_diagnostic
from app.db.models import DiagnosticRun
from app.errors import Conflict, NotFound, ValidationFailed
from app.events import version
from app.events.dispatch import RuleDeps
from app.schemas.auth import StudentCtx
from app.schemas.common import ExamId
from app.schemas.diagnostic import (
    DiagnosticOut,
    DiagnosticResult,
    DiagnosticStartIn,
    DiagnosticState,
)
from app.schemas.tasks import AnswerIn, TaskInstanceOut

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


async def _version(response: Response, deps: RuleDeps, student: StudentCtx) -> None:
    response.headers["X-Knowledge-Version"] = str(
        await version.get(deps.redis, student.student_id)
    )


async def _run(
    session: AsyncSession, student: StudentCtx, run_id: UUID
) -> DiagnosticRun:
    row = await session.get(DiagnosticRun, run_id)
    if row is None or row.student_id != student.student_id:
        raise NotFound("diagnostic run not found")
    return row


async def _out(
    session: AsyncSession, student: StudentCtx, row: DiagnosticRun
) -> DiagnosticOut:
    state = DiagnosticState.model_validate(row.state)
    next_task = None
    if row.status == "active" and state.asked:
        instance = await owned_instance(session, student.student_id, state.asked[-1])
        if instance.answered_at is None:
            next_task = TaskInstanceOut.model_validate(
                {
                    **{
                        name: getattr(instance, name)
                        for name in TaskInstanceOut.model_fields
                        if name not in {"options", "mode", "provenance"}
                    },
                    "options": instance.options or [],
                    "mode": "diagnostic",
                    "provenance": "template",
                }
            )
    return DiagnosticOut(
        run_id=row.id, status=row.status, state=state, next_task=next_task
    )


@router.post("", status_code=201, response_model=DiagnosticOut)
async def start_diagnostic(
    body: DiagnosticStartIn,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> DiagnosticOut:
    if body.n_tasks is not None and not 1 <= body.n_tasks <= deps.params.diag_max:
        raise ValidationFailed(f"n_tasks must be between 1 and {deps.params.diag_max}")
    active = await session.scalar(
        select(DiagnosticRun).where(
            DiagnosticRun.student_id == student.student_id,
            DiagnosticRun.exam_id == body.exam_id,
            DiagnosticRun.status == "active",
        )
    )
    if active is not None:
        raise Conflict(f"diagnostic run already active: {active.id}")
    result = await apply_diagnostic.start(
        session, deps, student.student_id, body.exam_id, body.n_tasks
    )
    await _version(response, deps, student)
    return result


@router.get("/active", response_model=DiagnosticOut)
async def active_diagnostic(
    exam_id: ExamId,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> DiagnosticOut:
    row = await session.scalar(
        select(DiagnosticRun).where(
            DiagnosticRun.student_id == student.student_id,
            DiagnosticRun.exam_id == exam_id,
            DiagnosticRun.status == "active",
        )
    )
    if row is None:
        raise NotFound("active diagnostic run not found")
    result = await _out(session, student, row)
    await _version(response, deps, student)
    return result


@router.post("/{run_id}/answer", response_model=DiagnosticOut)
async def answer_diagnostic(
    run_id: UUID,
    body: AnswerIn,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> DiagnosticOut:
    row = await _run(session, student, run_id)
    if row.status != "active":
        raise Conflict("diagnostic run is not active")
    state = DiagnosticState.model_validate(row.state)
    if body.instance_id not in state.asked:
        raise NotFound("task instance not found in diagnostic run")
    result = await record_answer(
        session, deps, student, body.instance_id, body, "diagnostic"
    )
    updated = await apply_diagnostic.answer(
        session, deps, student.student_id, run_id, result
    )
    await _version(response, deps, student)
    return updated


@router.post("/{run_id}/finish", response_model=DiagnosticResult)
async def finish_diagnostic(
    run_id: UUID,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> DiagnosticResult:
    row = await _run(session, student, run_id)
    if row.status != "active":
        raise Conflict("diagnostic run is not active")
    result = await apply_diagnostic.finish(session, deps, student.student_id, run_id)
    await _version(response, deps, student)
    return result
