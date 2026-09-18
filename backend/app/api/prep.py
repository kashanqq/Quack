"""Student-scoped preparation metadata."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis

from app.api.deps import get_current_student, get_redis
from app.keys import knowledge_version
from app.schemas.auth import StudentCtx

router = APIRouter(prefix="/prep", tags=["prep"])


class KnowledgeVersionOut(BaseModel):
    version: int


@router.get("/knowledge/version", response_model=KnowledgeVersionOut)
async def get_knowledge_version(
    student: Annotated[StudentCtx, Depends(get_current_student)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> KnowledgeVersionOut:
    value = await redis.get(knowledge_version(str(student.student_id)))
    return KnowledgeVersionOut(version=int(value) if value is not None else 0)
