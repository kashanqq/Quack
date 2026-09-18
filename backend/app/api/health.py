"""Public, bounded dependency health checks."""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import func, select, text

from app.config import settings
from app.db.models import Event

router = APIRouter()


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
    """Count recently ingested events awaiting graph dispatch."""
    sessionmaker = getattr(request.app.state, "sessionmaker", None)
    if sessionmaker is None:
        return None
    since = datetime.now(UTC) - timedelta(hours=1)
    async with sessionmaker() as session:
        return await session.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.processed_at.is_(None), Event.ingested_at >= since)
        )


async def _bounded_check(
    check: Callable[[Request], Awaitable[bool]], request: Request
) -> Literal["ok", "down"]:
    try:
        return "ok" if await asyncio.wait_for(check(request), timeout=2) else "down"
    except Exception:
        return "down"


async def _llm_status(request: Request) -> Literal["ok", "degraded", "down"]:
    client = getattr(request.app.state, "llm", None)
    if client is None:
        return "down"
    try:
        result = client.status()
        if inspect.isawaitable(result):
            result = await asyncio.wait_for(result, timeout=2)
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
    checks = {
        "postgres": postgres,
        "neo4j": neo4j,
        "redis": redis,
        "search": "skipped",
    }
    if postgres == "ok":
        try:
            pending = await asyncio.wait_for(_graph_pending(request), timeout=2)
            if pending is not None and pending > 0:
                checks["graph_pending"] = pending
        except Exception:
            pass  # The existing storage health status is determined above.
    storage_ok = all(value == "ok" for value in (postgres, neo4j, redis))
    return HealthOut(
        status="ok" if storage_ok else "degraded",
        checks=checks,
        llm_status=llm_status,
        version=settings.GIT_SHA,
    )
