"""Authenticated Phase 2 task routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._answer import owned_instance, record_answer, skipped_instance
from app.api.deps import get_current_student, get_rule_deps, get_session
from app.apply import tasks as apply_tasks
from app.errors import Conflict, ValidationFailed
from app.events import dispatch, store, version
from app.events.dispatch import RuleDeps
from app.schemas.auth import StudentCtx
from app.schemas.events import EventIn, EventType, TaskSkippedPayload
from app.schemas.tasks import (
    AnswerIn,
    AnswerResult,
    TaskInstanceOut,
    TaskRequestIn,
    TaskSkipIn,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", status_code=201, response_model=TaskInstanceOut)
async def issue_task(
    body: TaskRequestIn,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> TaskInstanceOut:
    return await apply_tasks.issue(session, deps, student.student_id, body)


@router.post("/{instance_id}/answer", response_model=AnswerResult)
async def answer_task(
    instance_id: UUID,
    body: AnswerIn,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> AnswerResult:
    row = await owned_instance(session, student.student_id, instance_id)
    result = await record_answer(
        session, deps, student, instance_id, body, row.mode or body.mode
    )
    response.headers["X-Knowledge-Version"] = str(
        await version.get(deps.redis, student.student_id)
    )
    return result


@router.post("/{instance_id}/skip")
async def skip_task(
    instance_id: UUID,
    body: TaskSkipIn,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> dict:
    if body.instance_id != instance_id:
        raise ValidationFailed("instance_id does not match request")
    row = await owned_instance(session, student.student_id, instance_id, lock=True)
    if row.answered_at is not None or await skipped_instance(
        session, student.student_id, instance_id
    ):
        raise Conflict("task already answered or skipped")
    event_type = (
        EventType.task_skipped if body.reason == "skipped" else EventType.task_timed_out
    )
    payload = TaskSkippedPayload(
        instance_id=instance_id,
        mode=row.mode or "topic",
        time_spent_sec=body.time_spent_sec,
    )
    event = await store.append(
        session,
        deps.redis,
        EventIn(
            type=event_type,
            payload=payload.model_dump(mode="json"),
            student_id=student.student_id,
            exam_id=row.exam_id,
            topic_skill_id=row.skill_id,
        ),
        dispatch_event=False,
    )
    await dispatch.dispatch(session, event, deps)
    return {}


@router.get("/{instance_id}/solution")
async def get_solution(
    instance_id: UUID,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, list[str]]:
    row = await owned_instance(session, student.student_id, instance_id)
    if row.answered_at is None and not await skipped_instance(
        session, student.student_id, instance_id
    ):
        raise Conflict("solution unavailable before answer or skip")
    return {"solution": row.solution_rendered}
