"""Read/write queries over the personal layer (Neo4j).

Source: memory-architecture-quack.md §2.2, §2.4, 20-B1.md §2.4.
Every query starts with MATCH (st:Student {id: $student_id}) — see
00-contracts.md §3.2.

Real functions: ensure_student, get_states, get_state, upsert_state, merge_evidence.
Stubs (phase 2): get_misc_states, upsert_misc_state, add_root_cause, list_evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from neo4j import AsyncDriver

from app.graph import labels as L
from app.knowledge.hlr import recall_p
from app.schemas.knowledge import EvidenceIn, KnowledgeStateOut


# --- real ---


async def ensure_student(driver: AsyncDriver, student_id: UUID) -> None:
    """MERGE (:Student {id}) — idempotent, called from /auth/me."""
    query = f"MERGE (st:{L.STUDENT} {{id: $student_id}})"
    async with driver.session() as session:
        await session.run(query, student_id=str(student_id))


async def get_state(
    driver: AsyncDriver, student_id: UUID, skill_id: str, exam_id: str
) -> KnowledgeStateOut | None:
    """Latest KnowledgeState for (student, skill, exam), with p_recall recomputed at read time."""
    query = f"""
    MATCH (st:{L.STUDENT} {{id: $student_id}})-[:{L.HAS_STATE}]->(k:{L.KNOWLEDGE_STATE})
    MATCH (k)-[:{L.FOR_SKILL}]->(s:{L.SKILL} {{id: $skill_id}})
    WHERE k.exam_id = $exam_id
    RETURN k.skill_id AS skill_id, k.exam_id AS exam_id, k.p_at_obs AS p_at_obs,
           k.half_life_h AS half_life_h, k.confidence AS confidence,
           k.evidence_mass AS evidence_mass, k.n_correct AS n_correct,
           k.n_incorrect AS n_incorrect, k.n_partial AS n_partial,
           k.has_strong AS has_strong, k.last_observed_at AS last_observed_at,
           k.created_at AS created_at
    LIMIT 1
    """
    async with driver.session() as session:
        result = await session.run(query, student_id=str(student_id), skill_id=skill_id, exam_id=exam_id)
        rec = await result.single()
    if rec is None:
        return None
    return _row_to_state(rec, now=datetime.now(timezone.utc))


async def get_states(
    driver: AsyncDriver, student_id: UUID, exam_id: str
) -> list[KnowledgeStateOut]:
    """All current KnowledgeStates for one exam."""
    query = f"""
    MATCH (st:{L.STUDENT} {{id: $student_id}})-[:{L.HAS_STATE}]->(k:{L.KNOWLEDGE_STATE})
    WHERE k.exam_id = $exam_id
    RETURN k.skill_id AS skill_id, k.exam_id AS exam_id, k.p_at_obs AS p_at_obs,
           k.half_life_h AS half_life_h, k.confidence AS confidence,
           k.evidence_mass AS evidence_mass, k.n_correct AS n_correct,
           k.n_incorrect AS n_incorrect, k.n_partial AS n_partial,
           k.has_strong AS has_strong, k.last_observed_at AS last_observed_at,
           k.created_at AS created_at
    ORDER BY k.skill_id
    """
    now = datetime.now(timezone.utc)
    out: list[KnowledgeStateOut] = []
    async with driver.session() as session:
        result = await session.run(query, student_id=str(student_id), exam_id=exam_id)
        async for rec in result:
            out.append(_row_to_state(rec, now=now))
    return out


async def upsert_state(
    driver: AsyncDriver, student_id: UUID, new_state: KnowledgeStateOut, source_event_id: int
) -> None:
    """Create a new KnowledgeState, link it via PREVIOUS to the current one (if any).

    HAS_STATE moves from old to new; old keeps PREVIOUS -> new (newest first).
    """
    query = f"""
    MATCH (st:{L.STUDENT} {{id: $student_id}})
    MERGE (s:{L.SKILL} {{id: $skill_id}})
    OPTIONAL MATCH (st)-[old_rel:{L.HAS_STATE}]->(old:{L.KNOWLEDGE_STATE})
    WHERE old.exam_id = $exam_id
    CREATE (new:{L.KNOWLEDGE_STATE} {{
        skill_id: $skill_id, exam_id: $exam_id,
        p_at_obs: $p_at_obs, half_life_h: $half_life_h,
        confidence: $confidence, evidence_mass: $evidence_mass,
        n_correct: $n_correct, n_incorrect: $n_incorrect, n_partial: $n_partial,
        has_strong: $has_strong, student_id: $student_id,
        last_observed_at: datetime($last_observed_at),
        created_at: datetime($created_at),
        source_event_id: $source_event_id
    }})
    CREATE (new)-[:{L.FOR_SKILL}]->(s)
    CREATE (st)-[:{L.HAS_STATE}]->(new)
    FOREACH (_ IN CASE WHEN old IS NULL THEN [] ELSE [1] END |
        CREATE (new)-[:{L.PREVIOUS}]->(old)
        DELETE old_rel
    )
    """
    async with driver.session() as session:
        await session.run(
            query,
            student_id=str(student_id),
            skill_id=new_state.skill_id,
            exam_id=new_state.exam_id,
            p_at_obs=new_state.p_at_obs,
            half_life_h=new_state.half_life_h,
            confidence=new_state.confidence,
            evidence_mass=new_state.evidence_mass,
            n_correct=new_state.n_correct,
            n_incorrect=new_state.n_incorrect,
            n_partial=new_state.n_partial,
            has_strong=new_state.has_strong,
            last_observed_at=new_state.last_observed_at.isoformat(),
            created_at=new_state.created_at.isoformat(),
            source_event_id=source_event_id,
        )


async def merge_evidence(driver: AsyncDriver, student_id: UUID, ev: EvidenceIn) -> str:
    """MERGE Evidence on (event_id, skill_id). Idempotent — second call is a no-op."""
    query = f"""
    MATCH (st:{L.STUDENT} {{id: $student_id}})
    MERGE (s:{L.SKILL} {{id: $skill_id}})
    MERGE (e:{L.EVIDENCE} {{event_id: $event_id, skill_id: $skill_id}})
    ON CREATE SET
        e.exam_id = $exam_id, e.kind = $kind, e.tier = $tier,
        e.source = $source, e.weight = $weight, e.direction = $direction,
        e.difficulty_factor = $difficulty_factor, e.summary = $summary,
        e.observed_at = datetime($observed_at),
        e.extractor_version = $extractor_version
    MERGE (st)-[:{L.HAS_EVIDENCE}]->(e)
    MERGE (e)-[:{L.SUPPORTS} {{direction: $direction}}]->(s)
    RETURN e.event_id AS event_id, e.skill_id AS skill_id
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            student_id=str(student_id),
            skill_id=ev.skill_id,
            event_id=ev.event_id,
            exam_id=ev.exam_id,
            kind=ev.kind,
            tier=ev.tier,
            source=ev.source,
            weight=ev.weight,
            direction=ev.direction,
            difficulty_factor=ev.difficulty_factor,
            summary=ev.summary,
            observed_at=ev.observed_at.isoformat(),
            extractor_version=ev.extractor_version,
        )
        rec = await result.single()
    assert rec is not None
    return f"{rec['event_id']}:{rec['skill_id']}"


# --- stubs (phase 2) ---


async def get_misc_states(driver: AsyncDriver, student_id: UUID, skill_ids: list[str]):
    """Phase 2: misconception states for a set of skills."""
    raise NotImplementedError("phase 2")


async def upsert_misc_state(
    driver: AsyncDriver, student_id: UUID, misconception_id: str, status: str, counters: dict
):
    """Phase 2: update MisconceptionState (occurrence_count, strong_count, ...)."""
    raise NotImplementedError("phase 2")


async def add_root_cause(
    driver: AsyncDriver, evidence_id: str, root_skill_id: str, confidence: float, source: str
):
    """Phase 2: create ROOT_CAUSE edge from evidence to root skill."""
    raise NotImplementedError("phase 2")


async def list_evidence(driver: AsyncDriver, student_id: UUID, skill_id: str, limit: int = 50):
    """Phase 2: all Evidence for a skill, newest first (for 'why do you think so')."""
    raise NotImplementedError("phase 2")


# --- helpers ---


def _row_to_state(rec, *, now: datetime) -> KnowledgeStateOut:
    p_recall = recall_p(
        float(rec["half_life_h"]), rec["last_observed_at"].to_native(), now
    )
    return KnowledgeStateOut(
        skill_id=rec["skill_id"],
        exam_id=rec["exam_id"],
        p_recall=p_recall,
        p_at_obs=float(rec["p_at_obs"]),
        half_life_h=float(rec["half_life_h"]),
        confidence=float(rec["confidence"]),
        evidence_mass=float(rec["evidence_mass"]),
        n_correct=int(rec["n_correct"]),
        n_incorrect=int(rec["n_incorrect"]),
        n_partial=int(rec["n_partial"]),
        has_strong=bool(rec["has_strong"]),
        last_observed_at=rec["last_observed_at"].to_native(),
        created_at=rec["created_at"].to_native(),
    )