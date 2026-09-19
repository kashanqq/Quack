"""apply._lock.student_lock (docs/tz/phase3-agents.md §2.4, §6.12)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.apply._lock import lock_key, student_lock

pytestmark = pytest.mark.phase3


async def test_lock_taken_and_released(redis):
    sid = uuid4()
    async with student_lock(redis, sid) as got:
        assert got is True
        assert await redis.get(lock_key(sid)) is not None
    assert await redis.get(lock_key(sid)) is None


async def test_reentrant_in_the_same_task(redis):
    sid = uuid4()
    async with student_lock(redis, sid, wait_s=0.2):
        async with student_lock(redis, sid, wait_s=0.2) as nested:
            assert nested is True
        # the outer lock is still held after the nested block
        assert await redis.get(lock_key(sid)) is not None


async def test_observer_and_task_answer_serialized(redis):
    sid = uuid4()
    order: list[str] = []

    async def observer():
        async with student_lock(redis, sid):
            order.append("observer:start")
            await asyncio.sleep(0.15)
            order.append("observer:end")

    async def answer():
        await asyncio.sleep(0.02)
        async with student_lock(redis, sid) as got:
            assert got is True
            order.append("answer")

    await asyncio.gather(observer(), answer())

    assert order == ["observer:start", "observer:end", "answer"]


async def test_student_lock_timeout_does_not_block(redis):
    sid = uuid4()
    await redis.set(lock_key(sid), "someone-else", ex=6)

    loop = asyncio.get_running_loop()
    started = loop.time()
    async with student_lock(redis, sid, wait_s=0.3) as got:
        ran = True
    assert got is False and ran
    assert loop.time() - started < 1
    # a lock that is not ours is never released by us
    assert await redis.get(lock_key(sid)) == b"someone-else"


async def test_no_redis_runs_unlocked():
    async with student_lock(None, uuid4()) as got:
        assert got is False
