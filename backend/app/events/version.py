"""Redis-backed version of a student's knowledge state."""

from uuid import UUID

from redis.asyncio import Redis

from app import keys


async def bump(redis: Redis, student_id: UUID) -> int:
    return int(await redis.incr(keys.knowledge_version(student_id)))


async def get(redis: Redis, student_id: UUID) -> int:
    value = await redis.get(keys.knowledge_version(student_id))
    return int(value) if value is not None else 0
