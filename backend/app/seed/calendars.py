"""Exam date seeding into B1-owned Neo4j Exam nodes."""

import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from app.schemas.common import ExamId


class TestDate(BaseModel):
    exam_id: ExamId
    date: date
    registration_deadline: date
    late_deadline: date | None = None
    source: str
    checked_at: date
    is_demo: bool


def validate_calendars(path: Path) -> list[TestDate]:
    records = TypeAdapter(list[TestDate]).validate_python(
        json.loads(path.read_text(encoding="utf-8"))
    )
    keys = [(record.exam_id, record.date) for record in records]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate exam date")
    return records


async def seed_calendars(driver: object, path: Path) -> int:
    records = validate_calendars(path)
    if records and driver is None:
        raise RuntimeError("waiting: B1 graph driver")
    for record in records:
        async with driver.session() as session:
            result = await session.run(
                "MATCH (e:Exam {id: $exam_id}) "
                "MERGE (e)-[:HAS_DATE]->(d:TestDate {date: date($date)}) "
                "SET d.registration_deadline = date($registration_deadline), "
                "d.late_deadline = CASE WHEN $late_deadline IS NULL THEN NULL "
                "ELSE date($late_deadline) END, "
                "d.source = $source, d.checked_at = date($checked_at), "
                "d.is_demo = $is_demo",
                exam_id=record.exam_id,
                date=record.date.isoformat(),
                registration_deadline=record.registration_deadline.isoformat(),
                late_deadline=(
                    record.late_deadline.isoformat() if record.late_deadline else None
                ),
                source=record.source,
                checked_at=record.checked_at.isoformat(),
                is_demo=record.is_demo,
            )
            await result.consume()
    return len(records)
