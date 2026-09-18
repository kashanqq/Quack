"""Read/write queries over the personal layer (Neo4j).

Source: memory-architecture-quack.md §2.2, §2.4, 20-B1.md §2.4.
Every query starts with MATCH (st:Student {id: $student_id}) — see
00-contracts.md §3.2.

Real functions: ensure_student, get_states, get_state, upsert_state, merge_evidence.
Stubs (phase 2): get_misc_states, upsert_misc_state, add_root_cause, list_evidence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from neo4j import AsyncDriver

from app.graph import labels as L
from app.knowledge.hlr import recall_p
from app.schemas.knowledge import (
    EvidenceIn,
    EvidenceOut,
    KnowledgeStateOut,
    MisconceptionStateOut,
    RootCauseOut,
)

# --- real ---


async def ensure_student(driver: AsyncDriver, student_id: UUID) -> None:
    """MERGE (:Student {id}) — idempotent, called from /auth/me."""
    query = f"MERGE (st:{L.STUDENT} {{id: $student_id}})"
    async with driver.session() as session:
        await session.run(query, student_id=str(student_id))


async def get_state(
    driver: AsyncDriver, student_id: UUID, skill_id: str, exam_id: str
) -> KnowledgeStateOut | None:
    """Latest state for (student, skill, exam); p_recall at read time."""
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
        result = await session.run(
            query, student_id=str(student_id), skill_id=skill_id, exam_id=exam_id
        )
        rec = await result.single()
    if rec is None:
        return None
    return _row_to_state(rec, now=datetime.now(UTC))


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
    now = datetime.now(UTC)
    out: list[KnowledgeStateOut] = []
    async with driver.session() as session:
        result = await session.run(query, student_id=str(student_id), exam_id=exam_id)
        async for rec in result:
            out.append(_row_to_state(rec, now=now))
    return out


async def upsert_state(
    driver: AsyncDriver,
    student_id: UUID,
    new_state: KnowledgeStateOut,
    source_event_id: int,
) -> None:
    """Create a new KnowledgeState, link it via PREVIOUS to the current one (if any).

    HAS_STATE moves from old to new; old keeps PREVIOUS -> new (newest first).
    """
    query = f"""
    MATCH (st:{L.STUDENT} {{id: $student_id}})
    MERGE (s:{L.SKILL} {{id: $skill_id}})
    WITH st, s
    OPTIONAL MATCH (st)-[old_rel:{L.HAS_STATE}]->(old:{L.KNOWLEDGE_STATE})
    WHERE old.exam_id = $exam_id AND old.skill_id = $skill_id
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


# --- phase 2: misconceptions, roots, history ---


async def get_misc_states(
    driver: AsyncDriver, student_id: UUID, skill_ids: list[str]
) -> list[MisconceptionStateOut]:
    """Misconception states for a set of skills — memory-architecture §5."""
    if not skill_ids:
        return []
    query = f"""
    MATCH (st:{L.STUDENT} {{id: $student_id}})
          -[:{L.HAS_MISC_STATE}]->(ms:{L.MISCONCEPTION_STATE})
          -[:{L.OF_MISCONCEPTION}]->(m:{L.MISCONCEPTION})
    OPTIONAL MATCH (m)-[:{L.ABOUT}]->(s:{L.SKILL})
    WITH st, ms, m, collect(DISTINCT s.id) AS skill_ids
    WHERE any(sid IN skill_ids WHERE sid IN $skill_ids)
    RETURN m.id AS misconception_id, m.name AS name,
           ms.status AS status,
           ms.occurrence_count AS occurrence_count,
           ms.strong_count AS strong_count,
           ms.consecutive_avoided AS consecutive_avoided,
           ms.triggers AS triggers,
           ms.first_seen_at AS first_seen_at,
           ms.updated_at AS updated_at,
           skill_ids
    ORDER BY m.id
    """
    out: list[MisconceptionStateOut] = []
    async with driver.session() as session:
        result = await session.run(
            query, student_id=str(student_id), skill_ids=skill_ids
        )
        async for rec in result:
            out.append(
                MisconceptionStateOut(
                    misconception_id=rec["misconception_id"],
                    name=rec["name"],
                    status=rec["status"],
                    occurrence_count=int(rec["occurrence_count"]),
                    strong_count=int(rec["strong_count"]),
                    consecutive_avoided=int(rec["consecutive_avoided"]),
                    triggers=_parse_triggers(rec["triggers"]),
                    first_seen_at=rec["first_seen_at"].to_native(),
                    updated_at=rec["updated_at"].to_native(),
                    skill_ids=list(rec["skill_ids"] or []),
                )
            )
    return out


async def upsert_misc_state(
    driver: AsyncDriver,
    student_id: UUID,
    misconception_id: str,
    status: str,
    counters: dict,
    triggers: dict | None = None,
) -> MisconceptionStateOut:
    """Create or update MisconceptionState — memory-architecture §5.

    MERGE по (student_id, misconception_id). counters: occurrence_count,
    strong_count, consecutive_avoided. triggers сериализуется в JSON-строку.
    """
    import json as _json

    triggers_json = _json.dumps(triggers or {}, ensure_ascii=False)
    occurrence_count = int(counters.get("occurrence_count", 0))
    strong_count = int(counters.get("strong_count", 0))
    consecutive_avoided = int(counters.get("consecutive_avoided", 0))
    now = datetime.now(UTC).isoformat()

    query = f"""
    MATCH (st:{L.STUDENT} {{id: $student_id}})
    MATCH (m:{L.MISCONCEPTION} {{id: $misconception_id}})
    MERGE (st)-[:{L.HAS_MISC_STATE}]->
        (ms:{L.MISCONCEPTION_STATE} {{misconception_id: $misconception_id}})
    ON CREATE SET ms.first_seen_at = datetime($now), ms.created_at = datetime($now)
    SET ms.status = $status,
        ms.occurrence_count = $occurrence_count,
        ms.strong_count = $strong_count,
        ms.consecutive_avoided = $consecutive_avoided,
        ms.triggers = $triggers,
        ms.updated_at = datetime($now),
        ms.student_id = $student_id
    MERGE (ms)-[:{L.OF_MISCONCEPTION}]->(m)
    OPTIONAL MATCH (m)-[:{L.ABOUT}]->(s:{L.SKILL})
    WITH ms, m, collect(DISTINCT s.id) AS skill_ids
    RETURN m.id AS misconception_id, m.name AS name,
           ms.status AS status,
           ms.occurrence_count AS occurrence_count,
           ms.strong_count AS strong_count,
           ms.consecutive_avoided AS consecutive_avoided,
           ms.triggers AS triggers,
           ms.first_seen_at AS first_seen_at,
           ms.updated_at AS updated_at,
           skill_ids
    """
    async with driver.session() as session:
        result = await session.run(
            query,
            student_id=str(student_id),
            misconception_id=misconception_id,
            status=status,
            occurrence_count=occurrence_count,
            strong_count=strong_count,
            consecutive_avoided=consecutive_avoided,
            triggers=triggers_json,
            now=now,
        )
        rec = await result.single()
    assert rec is not None
    return MisconceptionStateOut(
        misconception_id=rec["misconception_id"],
        name=rec["name"],
        status=rec["status"],
        occurrence_count=int(rec["occurrence_count"]),
        strong_count=int(rec["strong_count"]),
        consecutive_avoided=int(rec["consecutive_avoided"]),
        triggers=_parse_triggers(rec["triggers"]),
        first_seen_at=rec["first_seen_at"].to_native(),
        updated_at=rec["updated_at"].to_native(),
        skill_ids=list(rec["skill_ids"] or []),
    )


async def add_root_cause(
    driver: AsyncDriver,
    evidence_id: str,
    root_skill_id: str,
    confidence: float,
    source: str,
) -> None:
    """Create ROOT_CAUSE edge from Evidence to a Skill — memory-architecture §6.

    evidence_id format: "{event_id}:{skill_id}" (как возвращает merge_evidence).
    MERGE по (evidence_id, root_skill_id) — повторный вызов не создаёт дублей.
    """
    query = f"""
    MATCH (e:{L.EVIDENCE})
    WHERE e.event_id = $event_id AND e.skill_id = $from_skill
    MATCH (r:{L.SKILL} {{id: $root_skill_id}})
    MERGE (e)-[rc:{L.ROOT_CAUSE} {{root_skill_id: $root_skill_id}}]->(r)
    SET rc.confidence = $confidence,
        rc.source = $source,
        rc.created_at = coalesce(rc.created_at, datetime())
    """
    event_id, _, from_skill = evidence_id.partition(":")
    async with driver.session() as session:
        await session.run(
            query,
            event_id=int(event_id),
            from_skill=from_skill,
            root_skill_id=root_skill_id,
            confidence=confidence,
            source=source,
        )


async def list_evidence(
    driver: AsyncDriver, student_id: UUID, skill_id: str, limit: int = 50
) -> list[EvidenceOut]:
    """All Evidence for a skill, newest first — memory-architecture §10.5."""
    query = f"""
    MATCH (st:{L.STUDENT} {{id: $student_id}})
          -[:{L.HAS_EVIDENCE}]->(e:{L.EVIDENCE})
    WHERE e.skill_id = $skill_id
    RETURN e.event_id AS event_id, e.skill_id AS skill_id, e.kind AS kind,
           e.tier AS tier, e.source AS source, e.weight AS weight,
           e.direction AS direction, e.observed_at AS observed_at,
           e.summary AS summary,
           e.ctx_instance_id AS instance_id,
           e.ctx_message_id AS message_id
    ORDER BY e.observed_at DESC
    LIMIT $limit
    """
    out: list[EvidenceOut] = []
    async with driver.session() as session:
        result = await session.run(
            query,
            student_id=str(student_id),
            skill_id=skill_id,
            limit=limit,
        )
        async for rec in result:
            out.append(
                EvidenceOut(
                    evidence_id=f"{rec['event_id']}:{rec['skill_id']}",
                    event_id=int(rec["event_id"]),
                    skill_id=rec["skill_id"],
                    kind=rec["kind"],
                    tier=int(rec["tier"]),
                    source=rec["source"],
                    weight=float(rec["weight"]),
                    direction=int(rec["direction"]),
                    observed_at=rec["observed_at"].to_native(),
                    summary=rec["summary"],
                    instance_id=_to_uuid(rec["instance_id"]),
                    message_id=_to_uuid(rec["message_id"]),
                )
            )
    return out


async def list_root_causes(
    driver: AsyncDriver, student_id: UUID, window_days: int
) -> list[RootCauseOut]:
    """All ROOT_CAUSE edges from this student's Evidence in the last window_days."""
    query = f"""
    MATCH (st:{L.STUDENT} {{id: $student_id}})
          -[:{L.HAS_EVIDENCE}]->(e:{L.EVIDENCE})-[rc:{L.ROOT_CAUSE}]->(r:{L.SKILL})
    WHERE e.observed_at >= datetime() - duration({{days: $window_days}})
    RETURN e.skill_id AS from_skill_id,
           r.id AS root_skill_id,
           rc.confidence AS confidence,
           rc.source AS source,
           rc.created_at AS created_at
    ORDER BY rc.created_at DESC
    """
    out: list[RootCauseOut] = []
    async with driver.session() as session:
        result = await session.run(
            query, student_id=str(student_id), window_days=window_days
        )
        async for rec in result:
            out.append(
                RootCauseOut(
                    from_skill_id=rec["from_skill_id"],
                    root_skill_id=rec["root_skill_id"],
                    confidence=float(rec["confidence"]),
                    source=rec["source"],
                    created_at=rec["created_at"].to_native(),
                )
            )
    return out


async def get_state_history(
    driver: AsyncDriver,
    student_id: UUID,
    skill_id: str,
    exam_id: str,
    n: int = 3,
) -> list[KnowledgeStateOut]:
    """Last n KnowledgeStates for (student, skill, exam), newest first.

    Walks PREVIOUS from the current state.
    """
    query = f"""
    MATCH (st:{L.STUDENT} {{id: $student_id}})-[:{L.HAS_STATE}]->(k:{L.KNOWLEDGE_STATE})
    MATCH (k)-[:{L.FOR_SKILL}]->(s:{L.SKILL} {{id: $skill_id}})
    WHERE k.exam_id = $exam_id
    WITH k
    MATCH path = (k)-[:{L.PREVIOUS}*0..{int(n) - 1}]->(prev:{L.KNOWLEDGE_STATE})
    RETURN DISTINCT prev
    LIMIT $n
    """
    out: list[KnowledgeStateOut] = []
    now = datetime.now(UTC)
    async with driver.session() as session:
        result = await session.run(
            query,
            student_id=str(student_id),
            skill_id=skill_id,
            exam_id=exam_id,
            n=n,
        )
        async for rec in result:
            node = rec["prev"]
            data = dict(node)
            out.append(_row_to_state(_dict_to_row(data), now=now))
    return out


def _parse_triggers(value) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    import json as _json

    try:
        return _json.loads(value)
    except (ValueError, TypeError):
        return {}


def _to_uuid(value) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        return None


def _dict_to_row(data: dict) -> dict:
    """Wrap a plain dict into a simple attribute-accessor for _row_to_state."""

    class _Row(dict):
        def __getattr__(self, item):
            return self[item]

    return _Row(data)


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
