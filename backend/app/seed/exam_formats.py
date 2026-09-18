"""Load exam formats (sections, scale table) into Neo4j — memory-architecture §2.3.

Idempotent MERGE by (exam_id, section.name) and by exam for the scale table.
Depends on seed_skills: the Exam node must exist first.

Source: 20-B1.md §6.3.
"""

from __future__ import annotations

import json
from pathlib import Path

from neo4j import AsyncDriver
from pydantic import BaseModel, Field

from app.graph import labels as L
from app.seed.skills import SeedError, SeedReport


class SectionDef(BaseModel):
    name: str
    n_items: int
    minutes: int
    item_types: dict[str, int]
    scoring_rule: str
    calculator: bool
    adaptive: bool
    area_shares: dict[str, float]
    difficulty_shares: dict[str, float]
    answer_forms: list[str]


class ExamFormatFile(BaseModel):
    exam_id: str
    name: str
    max_raw_score: float
    sections: list[SectionDef]
    scale_table: dict | None = None
    scale_note: str | None = None
    source: str
    checked_at: str
    is_demo: bool = False


async def seed_exam_formats(driver: AsyncDriver, path: Path) -> SeedReport:
    """Load every .json under data/exam_formats/."""
    report = SeedReport()
    files = sorted(path.glob("*.json"))
    if not files:
        raise SeedError(str(path), "no exam format files found")

    for path in files:
        raw = json.loads(path.read_text(encoding="utf-8"))
        try:
            data = ExamFormatFile.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            raise SeedError(str(path), str(exc)) from exc

        report = report + await _upsert(driver, data)

    return report


async def _upsert(driver: AsyncDriver, data: ExamFormatFile) -> SeedReport:
    report = SeedReport()
    async with driver.session() as session:
        # check the Exam exists
        rec = await (
            await session.run(
                f"MATCH (e:{L.EXAM} {{id: $id}}) RETURN e.id AS id", id=data.exam_id
            )
        ).single()
        if rec is None:
            raise SeedError(data.exam_id, "Exam node missing — run seed_skills first")

        # update Exam-level fields
        await session.run(
            f"""
            MATCH (e:{L.EXAM} {{id: $id}})
            SET e.source = $source, e.checked_at = $checked_at,
                e.is_demo = $is_demo, e.scale_note = $scale_note
            """,
            id=data.exam_id,
            source=data.source,
            checked_at=data.checked_at,
            is_demo=data.is_demo,
            scale_note=data.scale_note,
        )

        # sections
        for sec in data.sections:
            await session.run(
                f"""
                MATCH (e:{L.EXAM} {{id: $exam_id}})
                MERGE (s:{L.SECTION} {{exam_id: $exam_id, name: $name}})
                SET s.n_items = $n_items, s.minutes = $minutes,
                    s.item_types = $item_types, s.scoring_rule = $scoring_rule,
                    s.calculator = $calculator, s.adaptive = $adaptive,
                    s.area_shares = $area_shares,
                    s.difficulty_shares = $difficulty_shares,
                    s.answer_forms = $answer_forms
                MERGE (e)-[:{L.HAS_SECTION}]->(s)
                """,
                exam_id=data.exam_id,
                name=sec.name,
                n_items=sec.n_items,
                minutes=sec.minutes,
                item_types=sec.item_types,
                scoring_rule=sec.scoring_rule,
                calculator=sec.calculator,
                adaptive=sec.adaptive,
                area_shares=sec.area_shares,
                difficulty_shares=sec.difficulty_shares,
                answer_forms=sec.answer_forms,
            )
            report.nodes += 1
            report.rels += 1

        # scale table
        if data.scale_table:
            await session.run(
                f"""
                MATCH (e:{L.EXAM} {{id: $exam_id}})
                MERGE (st:{L.SCALE_TABLE} {{exam_id: $exam_id}})
                SET st.raw_to_scaled = $raw_to_scaled
                MERGE (e)-[:{L.HAS_SCALE}]->(st)
                """,
                exam_id=data.exam_id,
                raw_to_scaled=data.scale_table,
            )
            report.nodes += 1
            report.rels += 1

    return report
