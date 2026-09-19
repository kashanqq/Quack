"""Authenticated program-cache routes: read, search, flag (§6.1, §6.8)."""

import hashlib
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app import keys
from app.api.deps import get_current_student, get_rule_deps, get_session
from app.db.repo import programs as program_repo
from app.errors import NotFound
from app.events.dispatch import RuleDeps
from app.schemas.auth import StudentCtx
from app.schemas.common import Page
from app.schemas.programs import (
    Program,
    ProgramFlagIn,
    SearchIn,
    SearchStartedOut,
    SearchStatusOut,
)

router = APIRouter(prefix="/programs", tags=["programs"])


@router.get("", response_model=Page[Program])
async def list_programs(
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    country: str | None = None,
    direction: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[Program]:
    return await program_repo.list_programs(
        session, country=country, direction=direction, limit=limit, offset=offset
    )


@router.post("/search", status_code=202, response_model=SearchStartedOut)
async def start_search(
    body: SearchIn,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> SearchStartedOut:
    """202 and a `search_id`: nothing is searched inside a request (§1.1).

    The id *is* the ARQ job id, hashed from the normalized query, so the
    same question from two students is one search and one budget spend.
    """
    normalized = " ".join(body.query.lower().split())
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    search_id = f"search:{digest}"
    deps.jobs.enqueue(
        "bulk",
        "search_programs",
        job_id=search_id,
        query=body.query,
        student_id=str(student.student_id),
        warm=False,
    )
    return SearchStartedOut(search_id=search_id)


@router.get("/search/{search_id}", response_model=SearchStatusOut)
async def search_status(
    search_id: str,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> SearchStatusOut:
    """Whatever the job last wrote; an unknown id is still `queued`."""
    try:
        raw = await deps.redis.get(keys.search_status(search_id))
    except (RedisError, OSError):
        raw = None
    if not raw:
        return SearchStatusOut(search_id=search_id, status="queued")
    try:
        return SearchStatusOut.model_validate(json.loads(raw))
    except ValueError:
        return SearchStatusOut(search_id=search_id, status="queued")


@router.post("/{program_id}/flag", response_model=Program)
async def flag_program(
    program_id: str,
    body: ProgramFlagIn,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Program:
    """«Неверно» hides an automatically extracted record from matching.

    Идемпотентно; вручную выверенный «пол» так пометить нельзя — 409.
    Полноценная перепроверка — фаза 5.
    """
    return await program_repo.flag(session, program_id, body.reason)


@router.get("/{program_id}", response_model=Program)
async def get_program(
    program_id: str,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Program:
    program = await program_repo.get_program(session, program_id)
    if program is None:
        raise NotFound("program not found")
    return program
