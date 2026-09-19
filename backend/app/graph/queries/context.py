"""The four reads behind the tutor's topic context (memory-architecture §9.2).

Source: docs/tz/phase3-agents.md §3.7 (Q1–Q4), F6.

`graph.context.build_topic_context` runs them in parallel with
`asyncio.gather`; each opens its own driver session. Q1 is one Cypher for the
whole slice, never a loop over skills. Every personal read starts from the
student node (00-contracts §3.2).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from neo4j import AsyncDriver
from pydantic import BaseModel

from app.graph import labels as L
from app.graph.queries import kb as kb_q
from app.graph.queries import personal as personal_q
from app.schemas.knowledge import KnowledgeStateOut, MisconceptionStateOut, TestDate


class SkillSliceRow(BaseModel):
    """One skill of the slice: its current state for the exam and up to the
    last three states (newest first, the current one included)."""

    skill_id: str
    name: str
    state: KnowledgeStateOut | None
    history: list[KnowledgeStateOut]


async def q_skill_slice(
    driver: AsyncDriver, student_id: UUID, exam_id: str, skill_ids: list[str]
) -> list[SkillSliceRow]:
    """Q1 — the topic skill and its prerequisites with state and history."""
    if not skill_ids:
        return []
    query = f"""
    OPTIONAL MATCH (st:{L.STUDENT} {{id: $student_id}})
    MATCH (s:{L.SKILL}) WHERE s.id IN $skill_ids
    OPTIONAL MATCH (st)-[:{L.HAS_STATE}]->(k:{L.KNOWLEDGE_STATE})-[:{L.FOR_SKILL}]->(s)
    WHERE k.exam_id = $exam_id
    OPTIONAL MATCH (k)-[:{L.PREVIOUS}*1..2]->(prev:{L.KNOWLEDGE_STATE})
    WITH s, k, prev
    ORDER BY prev.last_observed_at DESC
    WITH s, k, collect(prev) AS prevs
    RETURN s.id AS skill_id, coalesce(s.name, s.id) AS name, k AS state, prevs
    ORDER BY skill_id
    """
    now = datetime.now(UTC)
    rows: list[SkillSliceRow] = []
    async with driver.session() as session:
        result = await session.run(
            query, student_id=str(student_id), skill_ids=skill_ids, exam_id=exam_id
        )
        async for rec in result:
            state = _state(rec["state"], now)
            history = [state] if state is not None else []
            history.extend(s for s in (_state(node, now) for node in rec["prevs"]) if s)
            rows.append(
                SkillSliceRow(
                    skill_id=rec["skill_id"],
                    name=rec["name"],
                    state=state,
                    history=history[:3],
                )
            )
    return rows


async def q_root_causes(
    driver: AsyncDriver, student_id: UUID, skill_ids: list[str], window_days: int
) -> dict[str, tuple[int, float]]:
    """Q2 — per root skill: ROOT_CAUSE edges in the window and Σ confidence."""
    if not skill_ids:
        return {}
    query = f"""
    MATCH (st:{L.STUDENT} {{id: $student_id}})
          -[:{L.HAS_EVIDENCE}]->(e:{L.EVIDENCE})-[rc:{L.ROOT_CAUSE}]->(r:{L.SKILL})
    WHERE r.id IN $skill_ids
      AND e.observed_at >= datetime($now) - duration({{days: $window_days}})
    RETURN r.id AS skill_id, count(rc) AS n, sum(rc.confidence) AS confidence
    """
    out: dict[str, tuple[int, float]] = {}
    async with driver.session() as session:
        result = await session.run(
            query,
            student_id=str(student_id),
            skill_ids=skill_ids,
            window_days=window_days,
            now=datetime.now(UTC).isoformat(),
        )
        async for rec in result:
            out[rec["skill_id"]] = (int(rec["n"]), float(rec["confidence"] or 0.0))
    return out


async def q_misconceptions(
    driver: AsyncDriver, student_id: UUID, skill_ids: list[str]
) -> list[MisconceptionStateOut]:
    """Q3 — the student's misconception states ABOUT these skills."""
    return await personal_q.get_misc_states(driver, student_id, skill_ids)


async def q_test_dates(
    driver: AsyncDriver, exam_id: str, after: date
) -> list[TestDate]:
    """Q4 — the exam's test dates after `after`, nearest first."""
    dates = await kb_q.list_test_dates(driver, exam_id)
    return [d for d in dates if d.date > after]


def _state(node, now: datetime) -> KnowledgeStateOut | None:
    if node is None:
        return None
    data = dict(node)
    if "half_life_h" not in data or "last_observed_at" not in data:
        return None
    return personal_q._row_to_state(personal_q._dict_to_row(data), now=now)
