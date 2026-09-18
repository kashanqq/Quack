"""Student-owned milestone completion marks."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MilestoneMark


async def list_marks(session: AsyncSession, student_id: UUID) -> dict[str, datetime]:
    rows = await session.execute(
        select(MilestoneMark.milestone_key, MilestoneMark.done_at).where(
            MilestoneMark.student_id == student_id
        )
    )
    return dict(rows.all())


async def set_mark(
    session: AsyncSession, student_id: UUID, key: str, done: bool
) -> None:
    if not done:
        await session.execute(
            delete(MilestoneMark).where(
                MilestoneMark.student_id == student_id,
                MilestoneMark.milestone_key == key,
            )
        )
    elif await session.get(MilestoneMark, (student_id, key)) is None:
        session.add(MilestoneMark(student_id=student_id, milestone_key=key))
    await session.flush()
