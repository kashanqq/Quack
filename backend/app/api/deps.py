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

from app.config import settings
from app.errors import Unauthorized
from app.events.dispatch import RuleDeps
from app.events.outbox import JobOutbox
from app.schemas.auth import StudentCtx

_logger = structlog.get_logger(__name__)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Commit a successful request and roll back a failed one."""
    async with request.app.state.sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


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
    every `RuleDeps` of that request shares it. `flush_outbox` drains it
    after the session dependency has committed — a rolled-back request never
    reaches the flush, so its jobs are never enqueued.
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
    """Enqueue the request's recorded jobs once the transaction is done.

    Declared *before* `get_session` in a route's dependency list would flush
    too early, so routes take it as a plain dependency: FastAPI tears down
    dependencies in reverse order of resolution, and `get_session` is
    resolved first by every route that has both.
    """
    try:
        yield
    finally:
        await _drain(request)


async def _drain(request: Request) -> None:
    outbox = getattr(request.state, "job_outbox", None)
    if outbox is None or not outbox.entries:
        return
    session = None
    sessionmaker = getattr(request.app.state, "sessionmaker", None)
    try:
        if sessionmaker is not None:
            session = sessionmaker()
        await outbox.flush(session, get_arq(request))
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
