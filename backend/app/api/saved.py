"""Authenticated saved-program routes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_student, get_redis, get_session
from app.db.repo import programs as program_repo
from app.errors import NotFound
from app.events import store
from app.schemas.auth import StudentCtx
from app.schemas.common import Page
from app.schemas.events import EventIn, EventType, ProgramSavedPayload
from app.schemas.programs import Program, SavedProgram

router = APIRouter(prefix="/saved", tags=["saved"])


class SavedProgramWithProgram(SavedProgram):
    program: Program


@router.get("", response_model=Page[SavedProgramWithProgram])
async def list_saved(
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Page[SavedProgramWithProgram]:
    saved = await program_repo.list_saved(session, student.student_id)
    items = []
    for item in saved:
        program = await program_repo.get_program(session, item.program_id)
        if program is None:
            raise NotFound("program not found")
        items.append(
            SavedProgramWithProgram(
                program_id=item.program_id,
                saved_at=item.saved_at,
                program=program,
            )
        )
    return Page[SavedProgramWithProgram](items=items, total=len(items))


@router.post("/{program_id}", status_code=201)
async def save_program(
    program_id: str,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> None:
    await program_repo.save_program(session, student.student_id, program_id)
    await store.append(
        session,
        redis,
        EventIn(
            type=EventType.program_saved,
            payload=ProgramSavedPayload(program_id=program_id).model_dump(mode="json"),
            student_id=student.student_id,
        ),
    )


@router.delete("/{program_id}", status_code=204)
async def remove_saved(
    program_id: str,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> None:
    await program_repo.remove_saved(session, student.student_id, program_id)
    await store.append(
        session,
        redis,
        EventIn(
            type=EventType.program_removed,
            payload=ProgramSavedPayload(program_id=program_id).model_dump(mode="json"),
            student_id=student.student_id,
        ),
    )
