"""Authenticated Phase 2 preparation-set routes."""

from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app import keys
from app.api.chat import chat_id_for
from app.api.deps import get_arq, get_current_student, get_rule_deps, get_session
from app.apply import sets as apply_sets
from app.db.repo import forecast as forecast_repo
from app.db.repo import sets as set_repo
from app.errors import Conflict, NotFound, ValidationFailed
from app.events import dispatch, store, version
from app.events.dispatch import RuleDeps
from app.schemas.auth import StudentCtx
from app.schemas.common import ExamId
from app.schemas.events import (
    EventIn,
    EventType,
    SetCompletedPayload,
    SetDeadlineChangedPayload,
    SetOpenedPayload,
    SetSwitchedByUserPayload,
    TopicCompletedPayload,
    TopicOpenedPayload,
)
from app.schemas.sets import SetEditIn, SetOut, SetsByExam, SetSwitchIn, TopicOut
from app.workers.queue import enqueue

router = APIRouter(prefix="/sets", tags=["sets"])
_logger = structlog.get_logger(__name__)
_MESSAGE_TYPES = [EventType.message_user, EventType.message_assistant]


async def _version(response: Response, deps: RuleDeps, student_id: UUID) -> None:
    response.headers["X-Knowledge-Version"] = str(
        await version.get(deps.redis, student_id)
    )


async def _owned_set(session: AsyncSession, student_id: UUID, set_id: UUID) -> SetOut:
    item = await set_repo.get_set(session, student_id, set_id)
    if item is None:
        raise NotFound("set not found")
    return item


def _topic(item: SetOut, skill_id: str) -> TopicOut:
    topic = next((topic for topic in item.topics if topic.skill_id == skill_id), None)
    if topic is None:
        raise NotFound("set topic not found")
    return topic


async def _read_sets(
    session: AsyncSession, student_id: UUID, exam_id: ExamId
) -> SetsByExam:
    items = await set_repo.list_sets(session, student_id, exam_id)
    forecast = await forecast_repo.get(session, student_id, exam_id)
    return SetsByExam(
        exam_id=exam_id,
        forecast=forecast,
        current=next((item for item in items if item.status == "current"), None),
        upcoming=[item for item in items if item.status == "upcoming"],
        done=[item for item in items if item.status == "done"],
    )


async def _record(session: AsyncSession, deps: RuleDeps, event_in: EventIn) -> dict:
    event = await store.append(session, deps.redis, event_in, dispatch_event=False)
    return await dispatch.dispatch(session, event, deps)


@router.get("", response_model=SetsByExam)
async def list_sets(
    exam_id: ExamId,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> SetsByExam:
    current = await _read_sets(session, student.student_id, exam_id)
    if current.current is None and not current.upcoming and not current.done:
        current = await apply_sets.rebuild_sets(
            session, deps, student.student_id, exam_id
        )
    await _version(response, deps, student.student_id)
    return current


@router.post("/switch", response_model=SetsByExam)
async def switch_set(
    body: SetSwitchIn,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> SetsByExam:
    target = await _owned_set(session, student.student_id, body.set_id)
    if target.status == "done":
        raise Conflict("completed set cannot be selected")
    before = await set_repo.list_sets(session, student.student_id, target.exam_id)
    previous = next((item.id for item in before if item.status == "current"), None)
    await _record(
        session,
        deps,
        EventIn(
            type=EventType.set_switched_by_user,
            payload=SetSwitchedByUserPayload(
                from_set_id=previous, to_set_id=body.set_id
            ).model_dump(mode="json"),
            student_id=student.student_id,
            exam_id=target.exam_id,
            set_id=body.set_id,
        ),
    )
    result = await _read_sets(session, student.student_id, target.exam_id)
    await _version(response, deps, student.student_id)
    return result


@router.get("/{set_id}", response_model=SetOut)
async def get_set(
    set_id: UUID,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> SetOut:
    item = await _owned_set(session, student.student_id, set_id)
    await _version(response, deps, student.student_id)
    return item


@router.post("/{set_id}/open", response_model=SetOut)
async def open_set(
    set_id: UUID,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> SetOut:
    item = await _owned_set(session, student.student_id, set_id)
    if item.status == "done":
        raise Conflict("completed set cannot be opened")
    await _record(
        session,
        deps,
        EventIn(
            type=EventType.set_opened,
            payload=SetOpenedPayload(
                set_id=set_id, skill_ids=[topic.skill_id for topic in item.topics]
            ).model_dump(mode="json"),
            student_id=student.student_id,
            exam_id=item.exam_id,
            set_id=set_id,
        ),
    )
    result = await apply_sets.open_set(session, deps, student.student_id, set_id)
    await _version(response, deps, student.student_id)
    return result


@router.patch("/{set_id}", response_model=SetOut)
async def edit_set(
    set_id: UUID,
    body: SetEditIn,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> SetOut:
    item = await _owned_set(session, student.student_id, set_id)
    if body.deadline is not None and body.deadline < deps.now().date():
        raise ValidationFailed("deadline cannot be in the past")
    old_deadline = item.deadline
    await set_repo.update_set(
        session, student.student_id, set_id, body.skill_ids, body.deadline
    )
    if body.deadline is not None and body.deadline != old_deadline:
        await _record(
            session,
            deps,
            EventIn(
                type=EventType.set_deadline_changed,
                payload=SetDeadlineChangedPayload(
                    set_id=set_id, old=old_deadline, new=body.deadline
                ).model_dump(mode="json"),
                student_id=student.student_id,
                exam_id=item.exam_id,
                set_id=set_id,
            ),
        )
    result = await _owned_set(session, student.student_id, set_id)
    await _version(response, deps, student.student_id)
    return result


@router.post("/{set_id}/topics/{skill_id}/open", response_model=TopicOut)
async def open_topic(
    set_id: UUID,
    skill_id: str,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> TopicOut:
    item = await _owned_set(session, student.student_id, set_id)
    topic = _topic(item, skill_id)
    await _record(
        session,
        deps,
        EventIn(
            type=EventType.topic_opened,
            payload=TopicOpenedPayload(set_id=set_id, skill_id=skill_id).model_dump(
                mode="json"
            ),
            student_id=student.student_id,
            exam_id=item.exam_id,
            set_id=set_id,
            topic_skill_id=skill_id,
        ),
    )
    await _version(response, deps, student.student_id)
    return topic


@router.post("/{set_id}/topics/{skill_id}/complete", response_model=SetOut)
async def complete_topic(
    set_id: UUID,
    skill_id: str,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
    arq: Annotated[Any, Depends(get_arq)],
) -> SetOut:
    item = await _owned_set(session, student.student_id, set_id)
    topic = _topic(item, skill_id)
    if topic.status == "closed":
        raise Conflict("topic already completed")
    await set_repo.set_topic_status(session, set_id, skill_id, "closed")
    await _record(
        session,
        deps,
        EventIn(
            type=EventType.topic_completed,
            payload=TopicCompletedPayload(set_id=set_id, skill_id=skill_id).model_dump(
                mode="json"
            ),
            student_id=student.student_id,
            exam_id=item.exam_id,
            set_id=set_id,
            topic_skill_id=skill_id,
        ),
    )
    updated = await _owned_set(session, student.student_id, set_id)
    set_done = bool(updated.topics) and all(
        topic.status == "closed" for topic in updated.topics
    )
    if set_done:
        await _record(
            session,
            deps,
            EventIn(
                type=EventType.set_completed,
                payload=SetCompletedPayload(set_id=set_id).model_dump(mode="json"),
                student_id=student.student_id,
                exam_id=item.exam_id,
                set_id=set_id,
            ),
        )
        await set_repo.set_status(session, student.student_id, set_id, "done")
        updated = await _owned_set(session, student.student_id, set_id)
    # The observer should see the topic window before the student moves on;
    # the cached context of the closed topic and of the set is stale now.
    await session.commit()
    await _drop_topic_context(deps, student.student_id, set_id, skill_id)
    await _observe_after_completion(
        session, arq, student.student_id, updated, skill_id, set_done
    )
    await _version(response, deps, student.student_id)
    return updated


async def _drop_topic_context(
    deps: RuleDeps, student_id: UUID, set_id: UUID, skill_id: str
) -> None:
    try:
        await deps.redis.delete(
            keys.ctx_topic(str(student_id), skill_id),
            keys.ctx_topic(str(student_id), f"set:{set_id}"),
        )
    except Exception:  # noqa: BLE001 - the knowledge version still guards it
        _logger.warning("ctx_topic_invalidate_failed", student_id=str(student_id))


async def _observe_after_completion(
    session: AsyncSession,
    arq: Any,
    student_id: UUID,
    set_out: SetOut,
    skill_id: str,
    set_done: bool,
) -> None:
    """Queue the observer on the completed topic chat; when the whole set is
    done - on every topic chat with unprocessed messages and on the set chat
    (phase3 3.12)."""
    if arq is None:
        return
    try:
        targets: list[tuple[UUID, str]] = [
            (chat_id_for(student_id, "prep", set_out.id, skill_id), "topic_completed")
        ]
        if set_done:
            for topic in set_out.topics:
                chat_id = chat_id_for(student_id, "prep", set_out.id, topic.skill_id)
                if topic.skill_id != skill_id and await store.count_unprocessed(
                    session, chat_id, _MESSAGE_TYPES
                ):
                    targets.append((chat_id, "set_completed"))
            set_chat = chat_id_for(student_id, "prep", set_out.id, None)
            if await store.count_unprocessed(session, set_chat, _MESSAGE_TYPES):
                targets.append((set_chat, "set_completed"))
    except Exception:  # noqa: BLE001
        _logger.warning("observer_targets_failed", student_id=str(student_id))
        return
    for chat_id, trigger in targets:
        try:
            job_id = await enqueue(
                arq,
                "interactive",
                "observe_chat",
                _job_id=f"observe:{chat_id}",
                chat_id=chat_id,
                student_id=student_id,
                trigger=trigger,
            )
        except Exception:  # noqa: BLE001 - completing a topic must not fail on it
            _logger.warning("observer_not_enqueued", chat_id=str(chat_id))
            continue
        _logger.info(
            "observer_enqueued", chat_id=str(chat_id), trigger=trigger, job_id=job_id
        )
