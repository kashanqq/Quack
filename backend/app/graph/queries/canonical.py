"""Read-only queries over the canonical layer (Neo4j).

Source: memory-architecture-quack.md §2.1, 20-B1.md §2.3.
All Cypher is built from app.graph.labels constants.

All functions take an AsyncDriver as first arg and return Pydantic models
from app.schemas.knowledge.
"""

from __future__ import annotations

from neo4j import AsyncDriver

from app.graph import labels as L
from app.schemas.knowledge import (
    AreaOut,
    ExamFormat,
    MisconceptionRef,
    Prerequisite,
    Section,
    SkillRef,
    SkillWeight,
)

# --- exam / skills ---


async def get_skill(driver: AsyncDriver, skill_id: str) -> SkillRef | None:
    """Fetch a single canonical skill by id, or None if missing."""
    query = f"""
    MATCH (s:{L.SKILL} {{id: $skill_id}})
    OPTIONAL MATCH (a:{L.AREA})-[:{L.HAS_SKILL}]->(s)
    OPTIONAL MATCH (a2:{L.AREA})-[:{L.HAS_SKILL}]->(s)
    WITH s, collect(DISTINCT a.id) + collect(DISTINCT a2.id) AS _dummy
    OPTIONAL MATCH (e:{L.EXAM})-[:{L.HAS_AREA}]->(:{L.AREA})-[:{L.HAS_SKILL}]->(s)
    WITH s, collect(DISTINCT e.id) AS exam_ids
    RETURN s.id AS id, s.name AS name, s.description AS description,
           exam_ids, s.effort_h AS effort_h, s.base_half_life_h AS base_half_life_h
    """
    async with driver.session() as session:
        result = await session.run(query, skill_id=skill_id)
        rec = await result.single()
        if rec is None:
            return None
        return SkillRef(
            id=rec["id"],
            name=rec["name"],
            description=rec["description"],
            exam_ids=rec["exam_ids"],
            effort_h=float(rec["effort_h"]),
            base_half_life_h=rec["base_half_life_h"],
        )


async def list_exam_skills(driver: AsyncDriver, exam_id: str) -> list[SkillWeight]:
    """All skills for an exam, with area_id and weight. Uses the exam's own area."""
    query = f"""
    MATCH (e:{L.EXAM} {{id: $exam_id}})-[:{L.HAS_AREA}]->(a:{L.AREA})
          -[hs:{L.HAS_SKILL}]->(s:{L.SKILL})
    OPTIONAL MATCH (a2:{L.AREA})-[:{L.HAS_SKILL}]->(s)
    OPTIONAL MATCH (e2:{L.EXAM})-[:{L.HAS_AREA}]->(:{L.AREA})-[:{L.HAS_SKILL}]->(s)
    WITH a, hs, s, collect(DISTINCT e2.id) AS exam_ids
    RETURN s.id AS skill_id, s.name AS name, s.description AS description,
           s.effort_h AS effort_h, s.base_half_life_h AS base_half_life_h,
           exam_ids, a.id AS area_id, hs.weight AS weight
    ORDER BY a.id, s.id
    """
    out: list[SkillWeight] = []
    async with driver.session() as session:
        result = await session.run(query, exam_id=exam_id)
        async for rec in result:
            out.append(
                SkillWeight(
                    skill=SkillRef(
                        id=rec["skill_id"],
                        name=rec["name"],
                        description=rec["description"],
                        exam_ids=rec["exam_ids"],
                        effort_h=float(rec["effort_h"]),
                        base_half_life_h=rec["base_half_life_h"],
                    ),
                    area_id=rec["area_id"],
                    weight=float(rec["weight"]),
                )
            )
    return out


async def list_areas(driver: AsyncDriver, exam_id: str) -> list[AreaOut]:
    """Areas of an exam with score_share."""
    query = f"""
    MATCH (e:{L.EXAM} {{id: $exam_id}})-[:{L.HAS_AREA}]->(a:{L.AREA})
    RETURN a.id AS id, a.name AS name, a.score_share AS score_share
    ORDER BY a.id
    """
    out: list[AreaOut] = []
    async with driver.session() as session:
        result = await session.run(query, exam_id=exam_id)
        async for rec in result:
            out.append(
                AreaOut(
                    id=rec["id"],
                    name=rec["name"],
                    score_share=float(rec["score_share"]),
                )
            )
    return out


async def get_prerequisites(
    driver: AsyncDriver, skill_id: str, depth: int = 2
) -> list[Prerequisite]:
    """Walk REQUIRES upward from skill_id up to `depth` hops."""
    query = f"""
    MATCH (s:{L.SKILL} {{id: $skill_id}})
    MATCH path = (s)-[:{L.REQUIRES}*1..{int(depth)}]->(p:{L.SKILL})
    WITH p, length(path) AS d, relationships(path) AS rels
    WITH p, d, [r IN rels | r.strength] AS strengths
    RETURN DISTINCT p.id AS skill_id, d AS depth,
           reduce(m=1.0, x IN strengths | CASE WHEN x<m THEN x ELSE m END) AS strength
    ORDER BY depth, skill_id
    """
    out: list[Prerequisite] = []
    async with driver.session() as session:
        result = await session.run(query, skill_id=skill_id)
        async for rec in result:
            out.append(
                Prerequisite(
                    skill_id=rec["skill_id"],
                    strength=float(rec["strength"]),
                    depth=int(rec["depth"]),
                )
            )
    return out


async def get_dependents(driver: AsyncDriver, skill_id: str) -> list[str]:
    """One-hop reverse: which skills REQUIRE this skill."""
    query = f"""
    MATCH (d:{L.SKILL})-[:{L.REQUIRES}]->(s:{L.SKILL} {{id: $skill_id}})
    RETURN DISTINCT d.id AS id
    ORDER BY id
    """
    out: list[str] = []
    async with driver.session() as session:
        result = await session.run(query, skill_id=skill_id)
        async for rec in result:
            out.append(rec["id"])
    return out


async def get_exam_format(driver: AsyncDriver, exam_id: str) -> ExamFormat | None:
    """Fetch ExamFormat with sections + scale_table."""
    query = f"""
    MATCH (e:{L.EXAM} {{id: $exam_id}})
    OPTIONAL MATCH (e)-[:{L.HAS_SECTION}]->(sec:{L.SECTION})
    OPTIONAL MATCH (e)-[:{L.HAS_SCALE}]->(st:{L.SCALE_TABLE})
    RETURN e.id AS exam_id, e.name AS name, e.max_raw_score AS max_raw_score,
           e.source AS source, e.checked_at AS checked_at, e.is_demo AS is_demo,
           e.scale_note AS scale_note,
           collect(DISTINCT {{
             name: sec.name, n_items: sec.n_items, minutes: sec.minutes,
             item_types: sec.item_types, scoring_rule: sec.scoring_rule,
             calculator: sec.calculator, adaptive: sec.adaptive,
             area_shares: sec.area_shares, difficulty_shares: sec.difficulty_shares,
             answer_forms: sec.answer_forms
           }}) AS sections,
           st.raw_to_scaled AS scale_table
    """
    async with driver.session() as session:
        result = await session.run(query, exam_id=exam_id)
        rec = await result.single()
        if rec is None:
            return None
        sections: list[Section] = []
        for raw in rec["sections"]:
            if raw["name"] is None:
                continue
            sections.append(
                Section(
                    name=raw["name"],
                    n_items=int(raw["n_items"]),
                    minutes=int(raw["minutes"]),
                    item_types=dict(raw["item_types"] or {}),
                    scoring_rule=raw["scoring_rule"] or "",
                    calculator=bool(raw["calculator"]),
                    adaptive=bool(raw["adaptive"]),
                    area_shares=dict(raw["area_shares"] or {}),
                    difficulty_shares=dict(raw["difficulty_shares"] or {}),
                    answer_forms=list(raw["answer_forms"] or []),
                )
            )
        return ExamFormat(
            exam_id=rec["exam_id"],
            name=rec["name"],
            max_raw_score=float(rec["max_raw_score"]),
            sections=sections,
            scale_table=rec["scale_table"],
            scale_note=rec["scale_note"],
            source=rec["source"] or "",
            checked_at=rec["checked_at"],
            is_demo=bool(rec["is_demo"]),
        )


async def list_misconceptions_for_skill(
    driver: AsyncDriver, skill_id: str
) -> list[MisconceptionRef]:
    """All library misconceptions ABOUT this skill."""
    query = f"""
    MATCH (m:{L.MISCONCEPTION} {{scope: 'library'}})
          -[:{L.ABOUT}]->(s:{L.SKILL} {{id: $skill_id}})
    OPTIONAL MATCH (m)-[:{L.ABOUT}]->(s2:{L.SKILL})
    WITH m, collect(DISTINCT s2.id) AS skill_ids
    RETURN m.id AS id, m.name AS name, m.description AS description,
           m.error_class AS error_class, skill_ids
    ORDER BY m.id
    """
    out: list[MisconceptionRef] = []
    async with driver.session() as session:
        result = await session.run(query, skill_id=skill_id)
        async for rec in result:
            out.append(
                MisconceptionRef(
                    id=rec["id"],
                    name=rec["name"],
                    description=rec["description"],
                    error_class=rec["error_class"],
                    skill_ids=rec["skill_ids"],
                )
            )
    return out


async def list_templates_for_skill(driver: AsyncDriver, skill_id: str) -> list[str]:
    """IDs of TaskTemplates that TEST this skill."""
    query = f"""
    MATCH (t:{L.TASK_TEMPLATE})-[:{L.TESTS}]->(s:{L.SKILL} {{id: $skill_id}})
    RETURN DISTINCT t.id AS id
    ORDER BY id
    """
    out: list[str] = []
    async with driver.session() as session:
        result = await session.run(query, skill_id=skill_id)
        async for rec in result:
            out.append(rec["id"])
    return out


async def is_dag(driver: AsyncDriver) -> bool:
    """True if REQUIRES has no cycles. Used by tests and seed validation."""
    query = f"""
    MATCH (s:{L.SKILL})-[:{L.REQUIRES}*1..10]->(s)
    RETURN count(*) AS cycles
    """
    async with driver.session() as session:
        result = await session.run(query)
        rec = await result.single()
        return rec is None or int(rec["cycles"]) == 0
