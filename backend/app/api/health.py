"""Public, bounded dependency health checks.

Phase 5 (§10, §19) tightens two of them:

- `search` reports the last *recorded* provider result, and says `skipped`
  when it cannot know — a health poll must never spend the monthly search
  budget, and it must not claim `ok` just because nothing was written yet.
- `graph_pending` is the whole recoverable backlog, not the last hour and not
  the observer's open window over chat messages. An answer stuck since
  yesterday is exactly the number an operator needs before a demo.

`status` stays `ok`/`degraded` with HTTP 200 for compatibility. A `degraded`
200 is not a successful release smoke — that judgement belongs to the deploy
workflow, which also checks `version` against the released SHA (§22).
"""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from app import keys
from app.config import settings

router = APIRouter()

_CHECK_TIMEOUT_S = 2


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, Literal["ok", "down", "skipped"] | int]
    llm_status: Literal["ok", "degraded", "down"]
    version: str


async def _postgres(request: Request) -> bool:
    sessionmaker = getattr(request.app.state, "sessionmaker", None)
    if sessionmaker is None:
        return False
    async with sessionmaker() as session:
        await session.execute(text("SELECT 1"))
    return True


async def _neo4j(request: Request) -> bool:
    driver = getattr(request.app.state, "neo4j", None)
    if driver is None:
        return False
    async with driver.session() as session:
        result = await session.run("RETURN 1")
        await result.consume()
    return True


async def _redis(request: Request) -> bool:
    client = getattr(request.app.state, "redis", None)
    return client is not None and bool(await client.ping())


async def _graph_pending(request: Request) -> int | None:
    """The full backlog of events still waiting for the personal graph."""
    from app.events import recovery

    sessionmaker = getattr(request.app.state, "sessionmaker", None)
    if sessionmaker is None:
        return None
    async with sessionmaker() as session:
        return await recovery.pending_count(session)


async def _jobs_pending(request: Request) -> int | None:
    """Durable job intents that have not finished yet (§19)."""
    from app.db.models import JobOutbox
    from app.db.repo import outbox as outbox_repo

    sessionmaker = getattr(request.app.state, "sessionmaker", None)
    if sessionmaker is None:
        return None
    from sqlalchemy import func, select

    async with sessionmaker() as session:
        return int(
            await session.scalar(
                select(func.count())
                .select_from(JobOutbox)
                .where(JobOutbox.status.in_(outbox_repo.ACTIVE))
            )
            or 0
        )


async def _search(request: Request) -> Literal["ok", "down", "skipped"]:
    """The last search result the background jobs recorded, never a live call.

    Health must stay cheap and must not spend the monthly search budget, so
    the jobs write their outcome to Redis and this only reads it. Three
    honest answers: `down` if the last attempt failed, `ok` if one succeeded,
    and `skipped` when nothing is known — no attempt yet, or Redis is not
    answering. `skipped` is never dressed up as `ok`.
    """
    client = getattr(request.app.state, "redis", None)
    if client is None:
        return "skipped"
    try:
        if await client.get(keys.search_last_error()):
            return "down"
        return "ok" if await client.get(keys.search_last_ok()) else "skipped"
    except Exception:
        return "skipped"


async def _bounded_check(
    check: Callable[[Request], Awaitable[bool]], request: Request
) -> Literal["ok", "down"]:
    try:
        return (
            "ok"
            if await asyncio.wait_for(check(request), timeout=_CHECK_TIMEOUT_S)
            else "down"
        )
    except Exception:
        return "down"


async def _bounded_count(
    check: Callable[[Request], Awaitable[int | None]], request: Request
) -> int | None:
    try:
        return await asyncio.wait_for(check(request), timeout=_CHECK_TIMEOUT_S)
    except Exception:
        return None


async def _llm_status(request: Request) -> Literal["ok", "degraded", "down"]:
    client = getattr(request.app.state, "llm", None)
    if client is None:
        return "down"
    try:
        result = client.status()
        if inspect.isawaitable(result):
            result = await asyncio.wait_for(result, timeout=_CHECK_TIMEOUT_S)
        return result if result in {"ok", "degraded", "down"} else "down"
    except Exception:
        return "down"


@router.get("/health", response_model=HealthOut)
async def health(request: Request) -> HealthOut:
    postgres, neo4j, redis, llm_status = await asyncio.gather(
        _bounded_check(_postgres, request),
        _bounded_check(_neo4j, request),
        _bounded_check(_redis, request),
        _llm_status(request),
    )
    checks: dict[str, Literal["ok", "down", "skipped"] | int] = {
        "postgres": postgres,
        "neo4j": neo4j,
        "redis": redis,
        "search": await _search(request),
    }
    if postgres == "ok":
        for name, probe in (
            ("graph_pending", _graph_pending),
            ("jobs_pending", _jobs_pending),
        ):
            count = await _bounded_count(probe, request)
            if count:
                checks[name] = count
    storage_ok = all(value == "ok" for value in (postgres, neo4j, redis))
    return HealthOut(
        status="ok" if storage_ok else "degraded",
        checks=checks,
        llm_status=llm_status,
        version=settings.GIT_SHA,
    )
