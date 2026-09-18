"""Mock-exam run transport; B1 owns scoring, progress, and completion events."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._answer import owned_instance, record_answer
from app.api.deps import get_current_student, get_rule_deps, get_session
from app.apply import mocks as apply_mocks
from app.db.models import MockRun
from app.errors import Conflict, NotFound
from app.events import version
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical
from app.schemas.auth import StudentCtx
from app.schemas.mocks import MockOut, MockResultOut, MockStartIn
from app.schemas.tasks import AnswerIn, TaskInstanceOut

router = APIRouter(prefix="/mocks", tags=["mocks"])


async def _version(response: Response, deps: RuleDeps, student: StudentCtx) -> None:
    response.headers["X-Knowledge-Version"] = str(
        await version.get(deps.redis, student.student_id)
    )


async def _run(session: AsyncSession, student: StudentCtx, run_id: UUID) -> MockRun:
    row = await session.get(MockRun, run_id)
    if row is None or row.student_id != student.student_id:
        raise NotFound("mock run not found")
    return row


async def _out(
    session: AsyncSession, student: StudentCtx, deps: RuleDeps, row: MockRun
) -> MockOut:
    tasks = []
    answered = 0
    for instance_id in row.instance_ids:
        instance = await owned_instance(session, student.student_id, instance_id)
        answered += instance.answered_at is not None
        tasks.append(
            TaskInstanceOut.model_validate(
                {
                    **{
                        name: getattr(instance, name)
                        for name in TaskInstanceOut.model_fields
                        if name not in {"options", "mode", "provenance"}
                    },
                    "options": instance.options or [],
                    "mode": row.kind,
                    "provenance": "template",
                }
            )
        )
    exam_format = (
        await canonical.get_exam_format(deps.graph, row.exam_id)
        if deps.graph is not None
        else None
    )
    section = (
        next(
            (item for item in exam_format.sections if item.name == row.section_name),
            None,
        )
        if exam_format is not None
        else None
    )
    if section is None:
        raise NotFound("mock exam section not found")
    return MockOut(
        run_id=row.id,
        kind=row.kind,
        exam_id=row.exam_id,
        section_name=row.section_name,
        status=row.status,
        tasks=tasks,
        minutes=section.minutes,
        answered=answered,
        predicted_before=row.predicted_before,
    )


@router.post("", status_code=201, response_model=MockOut)
async def start_mock(
    body: MockStartIn,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> MockOut:
    result = await apply_mocks.start(session, deps, student.student_id, body)
    await _version(response, deps, student)
    return result


@router.get("/{run_id}", response_model=MockOut)
async def get_mock(
    run_id: UUID,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> MockOut:
    result = await _out(session, student, deps, await _run(session, student, run_id))
    await _version(response, deps, student)
    return result


@router.post("/{run_id}/answer", response_model=MockOut)
async def answer_mock(
    run_id: UUID,
    body: AnswerIn,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> MockOut:
    row = await _run(session, student, run_id)
    if row.status != "active":
        raise Conflict("mock run is not active")
    if body.instance_id not in row.instance_ids:
        raise NotFound("task instance not found in mock run")
    result = await record_answer(
        session, deps, student, body.instance_id, body, row.kind
    )
    updated = await apply_mocks.answer(
        session, deps, student.student_id, run_id, result
    )
    await _version(response, deps, student)
    return updated


@router.post("/{run_id}/finish", response_model=MockResultOut)
async def finish_mock(
    run_id: UUID,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> MockResultOut:
    row = await _run(session, student, run_id)
    if row.status != "active":
        raise Conflict("mock run is not active")
    result = await apply_mocks.finish(session, deps, student.student_id, run_id)
    await _version(response, deps, student)
    return result
