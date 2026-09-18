"""Program cache and student-owned saved programs."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProgramCache
from app.db.models import SavedProgram as SavedProgramRow
from app.errors import Conflict, NotFound
from app.schemas.common import Page
from app.schemas.programs import Program, SavedProgram

_SCALAR_FIELDS = (
    "id",
    "university",
    "country",
    "city",
    "direction",
    "language",
    "duration_months",
    "tuition_per_year",
    "living_per_year",
    "currency",
    "scholarships_note",
    "environment_text",
    "source_url",
    "checked_at",
    "is_demo",
    "extracted_auto",
    "flagged",
)


def _to_program(row: ProgramCache) -> Program:
    values = {name: getattr(row, name) for name in _SCALAR_FIELDS}
    return Program.model_validate({**row.payload, **values})


async def get_program(session: AsyncSession, program_id: str) -> Program | None:
    row = await session.get(ProgramCache, program_id)
    return _to_program(row) if row is not None else None


async def list_programs(
    session: AsyncSession,
    country: str | None = None,
    direction: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[Program]:
    filters = []
    if country is not None:
        filters.append(ProgramCache.country == country)
    if direction is not None:
        filters.append(ProgramCache.direction == direction)
    total = await session.scalar(
        select(func.count()).select_from(ProgramCache).where(*filters)
    )
    rows = (
        await session.scalars(
            select(ProgramCache)
            .where(*filters)
            .order_by(ProgramCache.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return Page[Program](items=[_to_program(row) for row in rows], total=total or 0)


async def upsert_program(session: AsyncSession, program: Program) -> None:
    values = {name: getattr(program, name) for name in _SCALAR_FIELDS}
    values["payload"] = {
        "requirements": [item.model_dump(mode="json") for item in program.requirements],
        "deadlines": [item.model_dump(mode="json") for item in program.deadlines],
    }
    row = await session.get(ProgramCache, program.id)
    if row is None:
        session.add(ProgramCache(**values))
    else:
        for name, value in values.items():
            setattr(row, name, value)
    await session.flush()


async def list_saved(session: AsyncSession, student_id: UUID) -> list[SavedProgram]:
    rows = (
        await session.scalars(
            select(SavedProgramRow)
            .where(SavedProgramRow.student_id == student_id)
            .order_by(SavedProgramRow.saved_at, SavedProgramRow.program_id)
        )
    ).all()
    return [
        SavedProgram(program_id=row.program_id, saved_at=row.saved_at) for row in rows
    ]


async def save_program(
    session: AsyncSession, student_id: UUID, program_id: str
) -> None:
    if await session.get(ProgramCache, program_id) is None:
        raise NotFound("program not found")
    if await session.get(SavedProgramRow, (student_id, program_id)) is not None:
        raise Conflict("program already saved")
    session.add(SavedProgramRow(student_id=student_id, program_id=program_id))
    await session.flush()


async def remove_saved(
    session: AsyncSession, student_id: UUID, program_id: str
) -> None:
    row = await session.get(SavedProgramRow, (student_id, program_id))
    if row is None:
        raise NotFound("saved program not found")
    await session.delete(row)
    await session.flush()
