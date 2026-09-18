"""Student-owned forecast cache."""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ForecastCache
from app.schemas.common import ExamId
from app.schemas.knowledge import ForecastOut


async def get(
    session: AsyncSession, student_id: UUID, exam_id: ExamId
) -> ForecastOut | None:
    row = await session.get(ForecastCache, (student_id, exam_id))
    return ForecastOut.model_validate(row.payload) if row is not None else None


async def put(
    session: AsyncSession,
    student_id: UUID,
    exam_id: ExamId,
    forecast: ForecastOut,
    as_of_event_id: int,
) -> None:
    values = {
        "student_id": student_id,
        "exam_id": exam_id,
        "payload": forecast.model_copy(
            update={"as_of_event_id": as_of_event_id}
        ).model_dump(mode="json"),
        "as_of_event_id": as_of_event_id,
    }
    statement = insert(ForecastCache).values(**values)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[ForecastCache.student_id, ForecastCache.exam_id],
            set_={
                "payload": statement.excluded.payload,
                "as_of_event_id": statement.excluded.as_of_event_id,
                "updated_at": func.now(),
            },
        )
    )
    await session.flush()
