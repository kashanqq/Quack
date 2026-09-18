"""Shared task-answer recording for topic, diagnostic, and mock routes."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event as EventRow
from app.db.models import TaskInstance as InstanceRow
from app.errors import Conflict, NotFound, ValidationFailed
from app.events import dispatch, handlers, store  # noqa: F401 (register B1 handlers)
from app.events.dispatch import RuleDeps
from app.events.session import current_session_id
from app.schemas.auth import StudentCtx
from app.schemas.common import TaskMode
from app.schemas.events import EventIn, EventType, TaskAnsweredPayload
from app.schemas.tasks import AnswerIn, AnswerResult


async def owned_instance(
    session: AsyncSession,
    student_id: UUID,
    instance_id: UUID,
    *,
    lock: bool = False,
) -> InstanceRow:
    statement = select(InstanceRow).where(
        InstanceRow.id == instance_id,
        InstanceRow.student_id == student_id,
    )
    if lock:
        statement = statement.with_for_update()
    row = await session.scalar(statement)
    if row is None:
        raise NotFound("task instance not found")
    return row


async def skipped_instance(
    session: AsyncSession, student_id: UUID, instance_id: UUID
) -> bool:
    event_id = await session.scalar(
        select(EventRow.id)
        .where(
            EventRow.student_id == student_id,
            EventRow.type.in_(
                (EventType.task_skipped.value, EventType.task_timed_out.value)
            ),
            EventRow.payload["instance_id"].astext == str(instance_id),
        )
        .limit(1)
    )
    return event_id is not None


async def _session_minute(
    session: AsyncSession, student_id: UUID, session_id: UUID, now: datetime
) -> int:
    first = await session.scalar(
        select(func.min(EventRow.occurred_at)).where(
            EventRow.student_id == student_id,
            EventRow.session_id == session_id,
        )
    )
    return max(0, int((now - first).total_seconds() // 60)) if first else 0


async def record_answer(
    session: AsyncSession,
    deps: RuleDeps,
    student: StudentCtx,
    instance_id: UUID,
    body: AnswerIn,
    mode: TaskMode,
) -> AnswerResult:
    """Append once, dispatch once, and return the B1 handler's result."""
    body = AnswerIn.model_validate(body)
    if body.instance_id != instance_id or body.mode != mode:
        raise ValidationFailed("answer instance or mode does not match request")
    row = await owned_instance(session, student.student_id, instance_id, lock=True)
    if row.mode is not None and row.mode != mode:
        raise ValidationFailed("task mode does not match issued instance")
    if row.answered_at is not None or await skipped_instance(
        session, student.student_id, instance_id
    ):
        raise Conflict("task already answered or skipped")

    session_id = await current_session_id(deps.redis, student.student_id)
    now = deps.now()
    minute = await _session_minute(session, student.student_id, session_id, now)
    payload = TaskAnsweredPayload(
        instance_id=instance_id,
        answer=body.answer,
        time_spent_sec=body.time_spent_sec,
        mode=mode,
        session_minute=minute,
        after_guideline=body.after_guideline,
        hint_level_before=body.hint_level_before,
    )
    event = await store.append(
        session,
        deps.redis,
        EventIn(
            type=EventType.task_answered,
            payload=payload.model_dump(mode="json"),
            student_id=student.student_id,
            session_id=session_id,
            exam_id=row.exam_id,
            topic_skill_id=row.skill_id,
            occurred_at=now,
        ),
        dispatch_event=False,
    )
    results = await dispatch.dispatch(session, event, deps)
    return AnswerResult.model_validate(results["apply_task_answered"])
