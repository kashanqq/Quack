"""Cookie-based student authentication."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Request, Response
from passlib.context import CryptContext
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    client_ip,
    get_current_student,
    get_graph,
    get_redis,
    get_session,
)
from app.config import settings
from app.db.repo.users import get_user_by_email
from app.errors import TooManyRequests, Unauthorized
from app.keys import login_ratelimit
from app.schemas.auth import LoginIn, StudentCtx

try:
    from app.graph.queries.personal import ensure_student as _ensure_student
except ModuleNotFoundError as exc:
    if exc.name != "app.graph" and not (exc.name or "").startswith("app.graph."):
        raise
    _ensure_student = None


router = APIRouter(prefix="/auth", tags=["auth"])
_passwords = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)


def issue_token(student_id: UUID | str, email: str) -> str:
    issued_at = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(student_id),
            "email": email,
            "iat": issued_at,
            "exp": issued_at + timedelta(days=settings.JWT_TTL_DAYS),
        },
        settings.JWT_SECRET.get_secret_value(),
        algorithm="HS256",
    )


def hash_password(raw: str) -> str:
    return _passwords.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return _passwords.verify(raw, hashed)


@router.post("/login", response_model=StudentCtx)
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> StudentCtx:
    key = login_ratelimit(client_ip(request))
    attempts = await redis.incr(key)
    if attempts == 1:
        await redis.expire(key, 60)
    if attempts > 10:
        raise TooManyRequests("too many login attempts")

    user = await get_user_by_email(session, body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise Unauthorized("invalid credentials")

    student = StudentCtx(student_id=user.id, email=user.email)
    response.set_cookie(
        key="quack_token",
        value=issue_token(student.student_id, student.email),
        httponly=True,
        samesite="lax",
        path="/",
        secure=settings.ENV == "prod",
    )
    return student


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
) -> None:
    response.delete_cookie(
        key="quack_token",
        path="/",
        secure=settings.ENV == "prod",
        httponly=True,
        samesite="lax",
    )


@router.get("/me", response_model=StudentCtx)
async def me(
    student: Annotated[StudentCtx, Depends(get_current_student)],
    graph: Annotated[object, Depends(get_graph)],
) -> StudentCtx:
    if _ensure_student is not None:
        if graph is None:
            raise RuntimeError("Neo4j driver is unavailable")
        await _ensure_student(graph, student.student_id)
    return student
