"""Authenticated profile read and update routes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_student, get_redis, get_session
from app.db.repo import profiles as profile_repo
from app.events import store
from app.schemas.auth import StudentCtx
from app.schemas.events import EventIn, EventType, ProfileUpdatedPayload
from app.schemas.profile import Profile, ProfileUpdateIn

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=Profile)
async def get_profile(
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Profile:
    return await profile_repo.get_profile(session, student.student_id)


@router.patch("", response_model=Profile)
async def update_profile(
    body: ProfileUpdateIn,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> Profile:
    profile = await profile_repo.apply_profile_update(session, student.student_id, body)
    payload = ProfileUpdatedPayload(
        field=body.path, value=body.value, by=body.by
    ).model_dump(mode="json")
    await store.append(
        session,
        redis,
        EventIn(
            type=EventType.profile_updated,
            payload=payload,
            student_id=student.student_id,
        ),
    )
    return profile
