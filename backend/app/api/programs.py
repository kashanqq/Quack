"""Authenticated program-cache read routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_student, get_session
from app.db.repo import programs as program_repo
from app.errors import NotFound
from app.schemas.auth import StudentCtx
from app.schemas.common import Page
from app.schemas.programs import Program

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
