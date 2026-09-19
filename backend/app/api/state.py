"""Per-student key/value state kept by the frontend between visits.

A bridge until each screen has its own domain endpoint: it holds UI
preferences and anything the client has not moved to the domain API yet.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_student, get_session
from app.db.repo import state as state_repo
from app.errors import ValidationFailed
from app.schemas.auth import StudentCtx

router = APIRouter(prefix="/state", tags=["state"])

MAX_KEYS_PER_PATCH = 200
MAX_KEY_LENGTH = 200


@router.get("")
async def get_state(
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    return await state_repo.get_all(session, student.student_id)


@router.patch("", status_code=204)
async def patch_state(
    body: dict[str, Any],
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    if len(body) > MAX_KEYS_PER_PATCH:
        raise ValidationFailed("too many keys")
    if any(not key or len(key) > MAX_KEY_LENGTH for key in body):
        raise ValidationFailed("invalid key")
    await state_repo.patch(session, student.student_id, body)
    return Response(status_code=204)


@router.delete("", status_code=204)
async def clear_state(
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    await state_repo.clear(session, student.student_id)
    return Response(status_code=204)
