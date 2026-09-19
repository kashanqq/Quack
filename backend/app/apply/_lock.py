"""Per-student write lock for the personal graph layer.

Source: docs/tz/phase3-agents.md §2.4, §3.10, §5.2 F9.

Every rule that reads a skill state and writes the next one
(`apply.observation`, `apply.task_answered`, `apply.dispute`) is a
read-modify-write over the graph; the observer job and a live task answer of
the same student would otherwise lose one of the two updates.

- Waiting is bounded (`wait_s`, default 5 s): a student answering a task never
  waits longer than that. On timeout the body still runs, with `got=False` and
  a warning — a lost race is a smaller evil than a stuck answer.
- Reentrant within one asyncio task: the observer rule appends `task.answered`
  and dispatches `apply_task_answered` while holding the lock; that nested
  acquire sees its own token in a context variable and passes through.
- Redis unavailable → no lock, `got=False`, warning (the turn is allowed).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from uuid import UUID, uuid4

import structlog
from redis.asyncio import Redis

from app import keys

_logger = structlog.get_logger(__name__)
_held: ContextVar[frozenset[str]] = ContextVar(
    "quack_student_locks", default=frozenset()
)
_POLL_S = 0.05


def lock_key(student_id: UUID | str) -> str:
    return keys.lock(f"knowledge:{student_id}")


@asynccontextmanager
async def student_lock(
    redis: Redis | None,
    student_id: UUID | str,
    *,
    ttl_s: int = 15,
    wait_s: float = 5,
) -> AsyncIterator[bool]:
    key = lock_key(student_id)
    if key in _held.get():
        yield True
        return
    if redis is None:
        yield False
        return

    token = uuid4().hex
    got = False
    try:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + wait_s
        while True:
            if await redis.set(key, token, nx=True, ex=ttl_s):
                got = True
                break
            if loop.time() >= deadline:
                break
            await asyncio.sleep(_POLL_S)
    except Exception:  # noqa: BLE001 — Redis down must not block the write
        _logger.warning("student_lock_unavailable", student_id=str(student_id))
        yield False
        return

    if not got:
        _logger.warning("student_lock_timeout", student_id=str(student_id))
    reset = _held.set(_held.get() | {key}) if got else None
    try:
        yield got
    finally:
        if reset is not None:
            _held.reset(reset)
        if got:
            try:
                current = await redis.get(key)
                if (
                    current is not None
                    and (current.decode() if isinstance(current, bytes) else current)
                    == token
                ):
                    await redis.delete(key)
            except Exception:  # noqa: BLE001
                _logger.warning(
                    "student_lock_release_failed", student_id=str(student_id)
                )
