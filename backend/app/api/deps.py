"""FastAPI dependencies for infrastructure and authenticated students."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import jwt
import structlog
from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import commit as commit_module
from app.config import settings
from app.errors import Unauthorized
from app.events.dispatch import RuleDeps
from app.events.outbox import JobOutbox
from app.schemas.auth import StudentCtx

_logger = structlog.get_logger(__name__)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Provide the request transaction; roll it back if the request failed.

    The **commit** deliberately does not live here. A `yield` dependency is
    torn down after the response has already been sent, so committing here
    would mean acknowledging work before it is durable — phase 5 §10 wants the
    opposite order. `app/api/commit.py::commit_request`, called from the HTTP
    middleware, commits it (together with the request's job intents, §9.2)
    between the endpoint and the response; the session is parked on
    `request.state` for it to find.
    """
    async with request.app.state.sessionmaker() as session:
        setattr(request.state, commit_module.SESSION_ATTR, session)
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise
        finally:
            setattr(request.state, commit_module.SESSION_ATTR, None)


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_arq(request: Request) -> Any:
    """ARQ pool for enqueuing jobs from a request, or None when unavailable."""
    return getattr(request.app.state, "arq", None)


def get_graph(request: Request) -> Any:
    return getattr(request.app.state, "neo4j", None)


def get_rule_deps(request: Request) -> RuleDeps:
    """Use application-owned connections and a callable UTC clock.

    Phase 4 (§1.4): one `JobOutbox` per request, kept on `request.state` so
    every `RuleDeps` of that request shares it. `commit_request` writes the
    recorded intents into the request transaction and delivers them after the
    commit — a rolled-back request never reaches either step, so its jobs are
    neither written nor enqueued.
    """
    outbox = getattr(request.state, "job_outbox", None)
    if outbox is None:
        outbox = JobOutbox()
        request.state.job_outbox = outbox
    return RuleDeps(
        graph=get_graph(request),
        redis=get_redis(request),
        params=settings.knowledge,
        now=lambda: datetime.now(UTC),
        jobs=outbox,
    )


async def flush_outbox(request: Request) -> AsyncIterator[None]:
    """Safety net for a route that records jobs without `get_session`.

    `commit_request` persists and delivers on the normal path, so this usually
    finds nothing left. It stays because a route that builds its own session
    (the SSE chat transport) still needs its intents to reach the queue, and
    because a streaming response finishes after the commit point.
    """
    try:
        yield
    finally:
        await _drain(request)


async def _drain(request: Request) -> None:
    outbox = getattr(request.state, "job_outbox", None)
    if outbox is None or not (outbox.entries or outbox.ready):
        return
    sessionmaker = getattr(request.app.state, "sessionmaker", None)
    session = None
    try:
        if sessionmaker is not None and outbox.entries:
            session = sessionmaker()
        await outbox.flush(session, get_arq(request), sessionmaker)
    except Exception:  # noqa: BLE001 — the response is already on its way
        _logger.warning("outbox_flush_failed", exc_info=True)
    finally:
        if session is not None:
            await session.close()


def get_llm(request: Request) -> Any:
    return request.app.state.llm


def get_current_student(request: Request) -> StudentCtx:
    token = request.cookies.get("quack_token")
    try:
        if not token:
            raise ValueError("missing token")
        claims = jwt.decode(
            token,
            settings.JWT_SECRET.get_secret_value(),
            algorithms=["HS256"],
            options={"require": ["sub", "email", "iat", "exp"]},
        )
        student_id = UUID(claims["sub"])
        email = claims["email"]
        if not isinstance(email, str) or not email:
            raise ValueError("invalid email claim")
        return StudentCtx(student_id=student_id, email=email)
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise Unauthorized("unauthorized") from exc


def client_ip(request: Request) -> str:
    if settings.ENV == "prod":
        forwarded = request.headers.get("X-Forwarded-For", "")
        first = forwarded.split(",", 1)[0].strip()
        if first:
            return first
    return request.client.host if request.client is not None else "unknown"
