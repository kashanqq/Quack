"""Validate and upsert the floor program catalogue."""

import json
from pathlib import Path

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repo.programs import upsert_program
from app.schemas.programs import Program


def validate_programs_floor(path: Path) -> list[Program]:
    records = TypeAdapter(list[Program]).validate_python(
        json.loads(path.read_text(encoding="utf-8"))
    )
    ids = [record.id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate program id")
    for record in records:
        if len(record.requirements) < 2 or not record.deadlines:
            raise ValueError(f"{record.id}: requirements or deadlines missing")
        if not record.environment_text or not record.source_url:
            raise ValueError(f"{record.id}: environment_text or source_url missing")
    return records


async def seed_programs_floor(session: AsyncSession, path: Path) -> int:
    records = validate_programs_floor(path)
    for record in records:
        await upsert_program(session, record)
    return len(records)
