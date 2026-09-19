"""Program cache and student-owned saved programs."""

from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProgramCache
from app.db.models import SavedProgram as SavedProgramRow
from app.errors import Conflict, NotFound
from app.schemas.common import Page
from app.schemas.programs import ExtractionMeta, Program, SavedProgram

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
    return Program.model_validate(
        {**row.payload, **values, "extraction": row.extraction}
    )


def _confirmed_fields(program: Program) -> int:
    """How much of a record is actually filled — the duplicate tie-breaker."""
    count = sum(
        1
        for value in (
            program.duration_months,
            program.tuition_per_year,
            program.living_per_year,
            program.scholarships_note,
            program.environment_text,
        )
        if value
    )
    count += sum(1 for item in program.requirements if item.threshold is not None)
    count += len(program.deadlines)
    return count


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


async def get_by_normalized_url(
    session: AsyncSession, normalized_url: str
) -> Program | None:
    row = await session.scalar(
        select(ProgramCache).where(ProgramCache.normalized_url == normalized_url)
    )
    return _to_program(row) if row is not None else None


async def find_duplicate(
    session: AsyncSession,
    university_slug: str,
    direction_slug: str,
    *,
    exclude_id: str | None = None,
) -> Program | None:
    statement = select(ProgramCache).where(
        ProgramCache.university_slug == university_slug,
        ProgramCache.direction_slug == direction_slug,
    )
    if exclude_id is not None:
        statement = statement.where(ProgramCache.id != exclude_id)
    row = await session.scalar(statement.order_by(ProgramCache.id).limit(1))
    return _to_program(row) if row is not None else None


async def flag(session: AsyncSession, program_id: str, reason: str) -> Program:
    """«Неверно» about a record: hide it from matching (§6.8).

    Флаговать пол нельзя: это выверенные вручную данные, и ошибка в них —
    задача редактора, а не одного ученика.
    """
    row = await session.get(ProgramCache, program_id)
    if row is None:
        raise NotFound("program not found")
    if not row.extracted_auto:
        raise Conflict("curated program cannot be flagged")
    row.flagged = True
    extraction = dict(row.extraction or {})
    notes = list(extraction.get("notes") or [])
    note = f"flagged:{reason[:200]}"
    if note not in notes:
        notes.append(note)
    extraction["notes"] = notes
    row.extraction = extraction
    await session.flush()
    return _to_program(row)


async def upsert_extracted(
    session: AsyncSession,
    program: Program,
    meta: ExtractionMeta,
    *,
    normalized_url: str,
    university_slug: str,
    direction_slug: str,
) -> Literal["created", "updated", "skipped_floor", "superseded", "lost"]:
    """Write one automatically extracted program, applying §6.7.

    Returns what happened, so the search status can report it:
    `skipped_floor` — a curated record already covers this program;
    `superseded` — this record wins over an older automatic duplicate;
    `lost` — the older automatic duplicate wins and this one is not written.
    """
    duplicate = await find_duplicate(
        session, university_slug, direction_slug, exclude_id=program.id
    )
    if duplicate is not None and not duplicate.extracted_auto:
        return "skipped_floor"

    existing = await session.get(ProgramCache, program.id)
    outcome: Literal["created", "updated", "skipped_floor", "superseded", "lost"] = (
        "updated" if existing is not None else "created"
    )

    if duplicate is not None and duplicate.id != program.id:
        new_score = _confirmed_fields(program)
        old_score = _confirmed_fields(duplicate)
        if new_score > old_score or (
            new_score == old_score and program.checked_at > duplicate.checked_at
        ):
            loser = await session.get(ProgramCache, duplicate.id)
            if loser is not None:
                loser.flagged = True
                loser_meta = dict(loser.extraction or {})
                notes = list(loser_meta.get("notes") or [])
                notes.append(f"superseded_by:{program.id}")
                loser_meta["notes"] = notes
                loser.extraction = loser_meta
            outcome = "superseded"
        else:
            return "lost"

    await upsert_program(
        session,
        program,
        extraction=meta,
        normalized_url=normalized_url,
        university_slug=university_slug,
        direction_slug=direction_slug,
    )
    return outcome


async def upsert_program(
    session: AsyncSession,
    program: Program,
    *,
    extraction: ExtractionMeta | None = None,
    normalized_url: str | None = None,
    university_slug: str | None = None,
    direction_slug: str | None = None,
) -> None:
    values = {name: getattr(program, name) for name in _SCALAR_FIELDS}
    values["payload"] = {
        "requirements": [item.model_dump(mode="json") for item in program.requirements],
        "deadlines": [item.model_dump(mode="json") for item in program.deadlines],
    }
    if extraction is not None:
        values["extraction"] = extraction.model_dump(mode="json")
    if normalized_url is not None:
        values["normalized_url"] = normalized_url
    if university_slug is not None:
        values["university_slug"] = university_slug
    if direction_slug is not None:
        values["direction_slug"] = direction_slug
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


async def list_all(session: AsyncSession) -> list[Program]:
    rows = (
        await session.scalars(
            select(ProgramCache)
            .where(ProgramCache.flagged.is_(False))
            .order_by(ProgramCache.id)
        )
    ).all()
    return [_to_program(row) for row in rows]


async def list_saved_programs(session: AsyncSession, student_id: UUID) -> list[Program]:
    rows = (
        await session.scalars(
            select(ProgramCache)
            .join(SavedProgramRow, SavedProgramRow.program_id == ProgramCache.id)
            .where(SavedProgramRow.student_id == student_id)
            .order_by(SavedProgramRow.saved_at, SavedProgramRow.program_id)
        )
    ).all()
    return [_to_program(row) for row in rows]
