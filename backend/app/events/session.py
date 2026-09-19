"""Redis-backed 30-minute student activity sessions."""

from datetime import datetime
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event as EventRow
from app.keys import session as session_key

SESSION_TTL_SECONDS = 1800


async def current_session_id(redis: Redis, student_id: UUID) -> UUID:
    key = session_key(str(student_id))
    existing = await redis.get(key)
    if existing is not None:
        await redis.expire(key, SESSION_TTL_SECONDS)
        return UUID(existing.decode() if isinstance(existing, bytes) else existing)

    session_id = uuid4()
    await redis.set(key, str(session_id), ex=SESSION_TTL_SECONDS)
    return session_id


async def session_minute(
    session: AsyncSession, student_id: UUID, session_id: UUID, now: datetime
) -> int:
    """Minutes since the first event of this activity session (0 when none).

    One definition for the task answer (`task.answered.session_minute`), the
    tutor's session line and the observer's evidence context — otherwise the
    "late in the session" trigger (§5.3) would compare different clocks.
    """
    first = await session.scalar(
        select(func.min(EventRow.occurred_at)).where(
            EventRow.student_id == student_id,
            EventRow.session_id == session_id,
        )
    )
    return max(0, int((now - first).total_seconds() // 60)) if first else 0
