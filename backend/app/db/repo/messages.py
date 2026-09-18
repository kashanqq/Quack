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
