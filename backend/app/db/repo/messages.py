"""Student-isolated chat read model."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message as MessageRow
from app.schemas.chat import AssistantMarkup, MessageOut


async def append_message(
    session: AsyncSession,
    student_id: UUID,
    chat_id: UUID,
    role: Literal["user", "assistant"],
    text: str,
    markup: AssistantMarkup | None,
    event_id: int,
) -> UUID:
    message_id = uuid4()
    session.add(
        MessageRow(
            id=message_id,
            student_id=student_id,
            chat_id=chat_id,
            role=role,
            text=text,
            markup=markup.model_dump(mode="json") if markup is not None else None,
            event_id=event_id,
            created_at=datetime.now(UTC),
        )
    )
    await session.flush()
    return message_id


async def list_messages(
    session: AsyncSession, student_id: UUID, chat_id: UUID, limit: int = 50
) -> list[MessageOut]:
    rows = (
        await session.scalars(
            select(MessageRow)
            .where(MessageRow.student_id == student_id, MessageRow.chat_id == chat_id)
            .order_by(MessageRow.created_at.desc(), MessageRow.id.desc())
            .limit(limit)
        )
    ).all()
    return [
        MessageOut.model_validate(
            {
                "id": row.id,
                "role": row.role,
                "text": row.text,
                "markup": row.markup,
                "event_id": row.event_id,
                "created_at": row.created_at,
            }
        )
        for row in reversed(rows)
    ]


def _to_out(row: MessageRow) -> MessageOut:
    return MessageOut.model_validate(
        {
            "id": row.id,
            "role": row.role,
            "text": row.text,
            "markup": row.markup,
            "event_id": row.event_id,
            "created_at": row.created_at,
        }
    )


async def get_message(
    session: AsyncSession, student_id: UUID, message_id: UUID
) -> MessageOut | None:
    """One message of this student; someone else's id reads as missing."""
    row = await session.scalar(
        select(MessageRow).where(
            MessageRow.id == message_id, MessageRow.student_id == student_id
        )
    )
    return _to_out(row) if row is not None else None


async def list_by_event_ids(
    session: AsyncSession, student_id: UUID, event_ids: list[int]
) -> dict[int, UUID]:
    """`message.*` event id -> message id — how an observation's `event_ids`
    unfold back to the chat messages the student sees."""
    if not event_ids:
        return {}
    rows = await session.execute(
        select(MessageRow.event_id, MessageRow.id).where(
            MessageRow.student_id == student_id, MessageRow.event_id.in_(event_ids)
        )
    )
    return {int(event_id): message_id for event_id, message_id in rows.all()}
