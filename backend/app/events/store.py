"""Transactional event append and read operations."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, TypeAdapter
from redis.asyncio import Redis
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event as EventRow
from app.events import dispatch as dispatcher
from app.events.session import current_session_id
from app.schemas.events import (
    Event,
    EventIn,
    EventType,
    MessageAssistantPayload,
    MessageUserPayload,
    ProfileUpdatedPayload,
    ProgramSavedPayload,
    TaskAnsweredPayload,
    TaskIssuedPayload,
)

_PAYLOAD_MODELS: dict[EventType, type[BaseModel]] = {
    EventType.message_user: MessageUserPayload,
    EventType.message_assistant: MessageAssistantPayload,
    EventType.task_issued: TaskIssuedPayload,
    EventType.task_answered: TaskAnsweredPayload,
    EventType.profile_updated: ProfileUpdatedPayload,
    EventType.program_saved: ProgramSavedPayload,
    EventType.program_removed: ProgramSavedPayload,
}
_json_payload = TypeAdapter(dict[str, Any])


def _validated_payload(ev: EventIn) -> dict[str, Any]:
    model = _PAYLOAD_MODELS.get(ev.type)
    if model is not None:
        return model.model_validate(ev.payload).model_dump(mode="json")
    # Phase 2 event types have no agreed field-level payload schema yet.
    return _json_payload.dump_python(ev.payload, mode="json")


async def append(session: AsyncSession, redis: Redis, ev: EventIn) -> Event:
    session_id = ev.session_id
    if session_id is None:
        session_id = await current_session_id(redis, ev.student_id)
    occurred_at = ev.occurred_at
    if occurred_at is None:
        occurred_at = datetime.now(UTC)
    payload = _validated_payload(ev)

    result = await session.execute(
        insert(EventRow)
        .values(
            student_id=ev.student_id,
            session_id=session_id,
            exam_id=ev.exam_id,
            set_id=ev.set_id,
            topic_skill_id=ev.topic_skill_id,
            chat_id=ev.chat_id,
            type=ev.type.value,
            payload=payload,
            occurred_at=occurred_at,
            extractor_version=ev.extractor_version,
            source_event_ids=ev.source_event_ids,
        )
        .returning(EventRow.id, EventRow.ingested_at)
    )
    event_id, ingested_at = result.one()
    event = Event(
        **ev.model_dump(exclude={"payload", "session_id", "occurred_at"}),
        payload=payload,
        session_id=session_id,
        occurred_at=occurred_at,
        id=event_id,
        ingested_at=ingested_at,
    )
    await dispatcher.dispatch(session, event)
    return event


async def list_unprocessed(
    session: AsyncSession, chat_id: UUID, limit: int = 50
) -> list[Event]:
    result = await session.scalars(
        select(EventRow)
        .where(EventRow.chat_id == chat_id, EventRow.processed_at.is_(None))
        .order_by(EventRow.id)
        .limit(limit)
    )
    return [Event.model_validate(row) for row in result]


async def mark_processed(session: AsyncSession, event_ids: list[int]) -> None:
    if not event_ids:
        return
    await session.execute(
        update(EventRow)
        .where(EventRow.id.in_(event_ids))
        .values(processed_at=datetime.now(UTC))
    )


async def list_events(
    session: AsyncSession,
    student_id: UUID,
    types: list[EventType] | None = None,
    since: datetime | None = None,
    limit: int = 200,
) -> list[Event]:
    statement = select(EventRow).where(EventRow.student_id == student_id)
    if types is not None:
        statement = statement.where(EventRow.type.in_([type_.value for type_ in types]))
    if since is not None:
        statement = statement.where(EventRow.occurred_at >= since)
    result = await session.scalars(statement.order_by(EventRow.id).limit(limit))
    return [Event.model_validate(row) for row in result]
