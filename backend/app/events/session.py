"""Redis-backed 30-minute student activity sessions."""

from uuid import UUID, uuid4

from redis.asyncio import Redis

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
