"""Per-student key/value state; transaction ownership remains with the caller."""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StudentState


async def get_all(session: AsyncSession, student_id: UUID) -> dict[str, Any]:
    rows = await session.execute(
        select(StudentState.key, StudentState.value).where(
            StudentState.student_id == student_id
        )
    )
    return {key: value for key, value in rows}


async def patch(
    session: AsyncSession, student_id: UUID, entries: dict[str, Any]
) -> None:
    """Upsert every key; a None value deletes the key."""
    removed = [key for key, value in entries.items() if value is None]
    if removed:
        await session.execute(
            delete(StudentState).where(
                StudentState.student_id == student_id, StudentState.key.in_(removed)
            )
        )
    rows = [
        {"student_id": student_id, "key": key, "value": value}
        for key, value in entries.items()
        if value is not None
    ]
    if rows:
        statement = insert(StudentState).values(rows)
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[StudentState.student_id, StudentState.key],
                set_={"value": statement.excluded.value, "updated_at": func.now()},
            )
        )


async def clear(session: AsyncSession, student_id: UUID) -> None:
    await session.execute(
        delete(StudentState).where(StudentState.student_id == student_id)
    )
