"""The durable wrapper every registered job runs inside (§13.1, D01).

ARQ already retries a delivery, but its bookkeeping lives in Redis and its
`max_tries` is spent by *any* failure — including an LLM that has been down
for an hour. That is the phase-4 gap: an outage longer than the retry budget
silently drops the work.

This wrapper puts the lifecycle in Postgres instead:

- `Retry(defer=N)` — what every phase-4 job raises when a dependency is down
  — becomes `waiting_dependency`. No attempt is spent, `not_before` moves N
  seconds out, and `outbox_replay` brings the job back whenever the
  dependency returns, with no user action (AC03).
- A real error spends one attempt with a backoff; the third one is `failed`
  plus the existing `job.failed` event. Nothing is silently dropped (§16).
- Success is `succeeded`.

The generator itself is untouched: the transport keys are stripped here, so
`observe_chat(ctx, request_id, chat_id, ...)` keeps its phase-3 signature
(§23 "Job transport").
"""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from arq import Retry
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from redis.exceptions import RedisError

from app.db.repo import outbox as outbox_repo
from app.errors import LLMUnavailable, SearchUnavailable
from app.events.outbox import LEASE_S, LEASE_TOKEN_KEY, OUTBOX_ID_KEY

_logger = structlog.get_logger(__name__)

# Backoff between two real (non-outage) attempts of the same job — technical
# defaults for one VPS, not a product SLA (D09).
RETRY_BACKOFF_S: tuple[int, ...] = (30, 60)
# Deferral per dependency, aligned with the phase-4 job policy (§13.1).
DEPENDENCY_DEFER_S: dict[str, int] = {
    "llm": 120,
    "graph": 60,
    "search": 60,
    "redis": 60,
}


def _dependency_of(exc: BaseException) -> str | None:
    if isinstance(exc, LLMUnavailable):
        return "llm"
    if isinstance(exc, SearchUnavailable):
        return "search"
    if isinstance(exc, ServiceUnavailable | SessionExpired):
        return "graph"
    if isinstance(exc, RedisError):
        return "redis"
    return None


def _error_code(exc: BaseException) -> str:
    code = getattr(exc, "code", None)
    return str(code) if isinstance(code, str) else type(exc).__name__


def durable(
    fn: Callable[..., Awaitable[Any]], *, name: str, max_tries: int
) -> Callable[..., Awaitable[Any]]:
    """Wrap one job so its lifecycle survives Redis, ARQ and the worker."""

    @functools.wraps(fn)
    async def run(ctx: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        intent_id = kwargs.pop(OUTBOX_ID_KEY, None)
        raw_token = kwargs.pop(LEASE_TOKEN_KEY, None)
        token = _uuid_or_none(raw_token)
        if intent_id is None:
            # A cron run or a phase-4 style enqueue: no durable row to keep.
            return await fn(ctx, *args, **kwargs)

        intent_id = int(intent_id)
        structlog.contextvars.bind_contextvars(outbox_id=intent_id, fn_name=name)
        sessionmaker = ctx.get("sessionmaker")
        owned = await _write(
            sessionmaker,
            lambda session, now: outbox_repo.mark_started(
                session, intent_id, lease_token=token, lease_s=LEASE_S, now=now
            ),
        )
        if owned is False:
            _logger.info("job_lease_lost", outbox_id=intent_id, fn_name=name)
            return None
        try:
            result = await fn(ctx, *args, **kwargs)
        except Retry as retry:
            await _park(sessionmaker, intent_id, token, retry, name)
            raise
        except Exception as exc:
            await _fail(sessionmaker, intent_id, token, exc, name, max_tries)
            raise
        await _write(
            sessionmaker,
            lambda session, now: outbox_repo.mark_done(
                session, intent_id, lease_token=token, now=now
            ),
        )
        return result

    return run


async def _park(
    sessionmaker: Any,
    intent_id: int,
    token: UUID | None,
    retry: Retry,
    name: str,
    dependency: str | None = None,
) -> None:
    """`Retry` means "come back later" — never "this job has failed".

    With a named dependency the row waits on it; a bare `Retry` (a busy lock,
    a cron skew) only moves `not_before`. Either way no attempt is spent, so
    an outage cannot exhaust the three business tries (§13.1).
    """
    dependency = dependency or _dependency_of(retry.__cause__ or retry)
    defer = int(retry.defer_score or 0) // 1000
    if dependency is None:
        await _write(
            sessionmaker,
            lambda session, now: outbox_repo.mark_deferred(
                session,
                intent_id,
                lease_token=token,
                defer_s=defer or 30,
                now=now,
            ),
        )
        _logger.info("job_deferred", outbox_id=intent_id, fn_name=name, defer_s=defer)
        return
    wait = defer or DEPENDENCY_DEFER_S[dependency]
    await _write(
        sessionmaker,
        lambda session, now: outbox_repo.mark_waiting(
            session,
            intent_id,
            lease_token=token,
            dependency=dependency,  # type: ignore[arg-type]
            defer_s=wait,
            now=now,
        ),
    )
    _logger.info(
        "job_parked",
        outbox_id=intent_id,
        fn_name=name,
        dependency=dependency,
        defer_s=wait,
    )


async def _fail(
    sessionmaker: Any,
    intent_id: int,
    token: UUID | None,
    exc: BaseException,
    name: str,
    max_tries: int,
) -> None:
    dependency = _dependency_of(exc)
    if dependency is not None:
        # A dependency that fell over mid-job is an outage, not this job's
        # fault: park it the same way an explicit `Retry` would.
        await _park(sessionmaker, intent_id, token, Retry(), name, dependency)
        return
    code = _error_code(exc)
    intent = await _read(sessionmaker, intent_id)
    attempts = intent.attempts if intent is not None else 0
    if attempts + 1 >= max_tries:
        await _write(
            sessionmaker,
            lambda session, now: outbox_repo.mark_failed(
                session, intent_id, lease_token=token, error_code=code, now=now
            ),
        )
        _logger.warning(
            "job_failed_terminal", outbox_id=intent_id, fn_name=name, error_code=code
        )
        return
    backoff = RETRY_BACKOFF_S[min(attempts, len(RETRY_BACKOFF_S) - 1)]
    await _write(
        sessionmaker,
        lambda session, now: outbox_repo.mark_retry(
            session,
            intent_id,
            lease_token=token,
            error_code=code,
            defer_s=backoff,
            now=now,
        ),
    )
    _logger.info(
        "job_retry_scheduled",
        outbox_id=intent_id,
        fn_name=name,
        attempt=attempts + 1,
        error_code=code,
    )


async def _write(sessionmaker: Any, operation: Callable[[Any, datetime], Any]) -> Any:
    """One short transaction; a broken bookkeeping write never fails a job."""
    if sessionmaker is None:
        return None
    try:
        async with sessionmaker() as session:
            result = await operation(session, datetime.now(UTC))
            await session.commit()
            return result
    except Exception:  # noqa: BLE001 — the sweeper re-checks the row anyway
        _logger.warning("outbox_state_write_failed", exc_info=True)
        return None


async def _read(sessionmaker: Any, intent_id: int) -> outbox_repo.Intent | None:
    if sessionmaker is None:
        return None
    try:
        async with sessionmaker() as session:
            return await outbox_repo.get(session, intent_id)
    except Exception:  # noqa: BLE001
        return None


def _uuid_or_none(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None
