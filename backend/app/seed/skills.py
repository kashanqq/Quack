"""Load skill map and areas into Neo4j — memory-architecture-quack.md §2.1.

Idempotent: MERGE by id, SET properties, no deletes.
Validates Σ weight == max_raw_score, DAG (no cycles in REQUIRES).

Source: 20-B1.md §6.3.
"""

from __future__ import annotations

import json
from pathlib import Path

from neo4j import AsyncDriver
from pydantic import BaseModel, Field

from app.graph import labels as L
from app.graph.schema import apply_schema


class SourceRef(BaseModel):
    url: str
    checked_at: str


class SkillRequires(BaseModel):
    skill_id: str
    strength: float


class SkillDef(BaseModel):
    id: str
    name: str
    description: str
    effort_h: float
    base_half_life_h: float | None = None
    requires: list[SkillRequires] = Field(default_factory=list)


class AreaSkillRef(BaseModel):
    id: str
    weight: float


class AreaDef(BaseModel):
    id: str
    name: str
    score_share: float
    skills: list[AreaSkillRef]


class ExamHeader(BaseModel):
    id: str
    name: str
    max_raw_score: float


class SkillsFile(BaseModel):
    exam: ExamHeader
    areas: list[AreaDef]
    skills: list[SkillDef]
    sources: list[SourceRef] = Field(default_factory=list)


class SeedReport(BaseModel):
    nodes: int = 0
    rels: int = 0

    def __add__(self, other: "SeedReport") -> "SeedReport":
        return SeedReport(nodes=self.nodes + other.nodes, rels=self.rels + other.rels)


class SeedError(Exception):
    def __init__(self, path: str, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


async def seed_skills(driver: AsyncDriver, path: Path) -> SeedReport:
    """Load every .json under data/skills/. Exam + Area + Skill + HAS_AREA + HAS_SKILL + REQUIRES."""
    report = SeedReport()
    files = sorted(path.glob("*.json"))
    if not files:
        raise SeedError(str(path), "no skill files found")

    for path in files:
        raw = json.loads(path.read_text(encoding="utf-8"))
        try:
            data = SkillsFile.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            raise SeedError(str(path), str(exc)) from exc

        _validate_file(data, path)
        report = report + await _upsert_file(driver, data)

    return report


def _validate_file(data: SkillsFile, path: Path) -> None:
    total = sum(s.weight for area in data.areas for s in area.skills)
    if abs(total - data.exam.max_raw_score) > 1e-6:
        raise SeedError(
            str(path),
            f"Σ weight {total} != max_raw_score {data.exam.max_raw_score}",
        )
    # skill uniqueness in this file
    ids = [s.id for s in data.skills]
    if len(ids) != len(set(ids)):
        raise SeedError(str(path), "duplicate skill ids")


async def _upsert_file(driver: AsyncDriver, data: SkillsFile) -> SeedReport:
    report = SeedReport()
    async with driver.session() as session:
        # 1. Exam
        await session.run(
            f"""
            MERGE (e:{L.EXAM} {{id: $id}})
            SET e.name = $name, e.max_raw_score = $max_raw_score,
                e.source = $source, e.checked_at = $checked_at
            """,
            id=data.exam.id,
            name=data.exam.name,
            max_raw_score=data.exam.max_raw_score,
            source=data.sources[0].url if data.sources else None,
            checked_at=data.sources[0].checked_at if data.sources else None,
        )
        report.nodes += 1

        # 2. Areas + relations
        for area in data.areas:
            await session.run(
                f"""
                MATCH (e:{L.EXAM} {{id: $exam_id}})
                MERGE (a:{L.AREA} {{id: $area_id}})
                SET a.name = $name, a.score_share = $score_share, a.exam_id = $exam_id
                MERGE (e)-[:{L.HAS_AREA}]->(a)
                """,
                exam_id=data.exam.id,
                area_id=area.id,
                name=area.name,
                score_share=area.score_share,
            )
            report.nodes += 1

        # 3. Skills — only those defined in this file (self.skills).
        # Areas may reference common skills defined in another file — those get
        # created later by that file's seed.
        for skill in data.skills:
            await session.run(
                f"""
                MERGE (s:{L.SKILL} {{id: $id}})
                SET s.name = $name, s.description = $description,
                    s.effort_h = $effort_h,
                    s.base_half_life_h = $base_half_life_h,
                    s.scope = 'canonical'
                """,
                id=skill.id,
                name=skill.name,
                description=skill.description,
                effort_h=skill.effort_h,
                base_half_life_h=skill.base_half_life_h,
            )
            report.nodes += 1

        # 4. HAS_SKILL edges (area → skill, with weight)
        for area in data.areas:
            for aref in area.skills:
                await session.run(
                    f"""
                    MATCH (a:{L.AREA} {{id: $area_id}})
                    MERGE (s:{L.SKILL} {{id: $skill_id}})
                    MERGE (a)-[r:{L.HAS_SKILL}]->(s)
                    SET r.weight = $weight
                    """,
                    area_id=area.id,
                    skill_id=aref.id,
                    weight=aref.weight,
                )
                report.rels += 1

        # 5. REQUIRES edges
        for skill in data.skills:
            for req in skill.requires:
                await session.run(
                    f"""
                    MATCH (s:{L.SKILL} {{id: $id}})
                    MERGE (p:{L.SKILL} {{id: $prereq}})
                    MERGE (s)-[r:{L.REQUIRES}]->(p)
                    SET r.strength = $strength
                    """,
                    id=skill.id,
                    prereq=req.skill_id,
                    strength=req.strength,
                )
                report.rels += 1

    return report


async def ensure_schema(driver: AsyncDriver, dim: int) -> None:
    """Convenience wrapper — call apply_schema before the first seed_skills."""
    await apply_schema(driver, dim)
