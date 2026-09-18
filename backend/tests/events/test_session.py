"""Redis activity-session behavior without a running Redis server."""

from uuid import uuid4

import pytest

from app.events.session import current_session_id
from app.keys import session as session_key

pytestmark = pytest.mark.phase1


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expirations: list[tuple[str, int]] = []
        self.set_calls: list[tuple[str, str, int]] = []

    async def get(self, key: str) -> bytes | None:
        value = self.values.get(key)
        return value.encode() if value is not None else None

    async def expire(self, key: str, seconds: int) -> None:
        self.expirations.append((key, seconds))

    async def set(self, key: str, value: str, ex: int) -> None:
        self.values[key] = value
        self.set_calls.append((key, value, ex))


async def test_same_session_within_ttl_and_new_after_delete():
    redis = FakeRedis()
    student_id = uuid4()
    key = session_key(str(student_id))

    first = await current_session_id(redis, student_id)
    again = await current_session_id(redis, student_id)
    assert again == first
    assert redis.set_calls == [(key, str(first), 1800)]
    assert redis.expirations == [(key, 1800)]

    del redis.values[key]
    fresh = await current_session_id(redis, student_id)
    assert fresh != first
    assert redis.set_calls[-1] == (key, str(fresh), 1800)
