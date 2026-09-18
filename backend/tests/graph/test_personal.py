"""Integration tests over the personal layer — 20-B1.md §7.

Uses the seeded canonical graph (skills) plus Student nodes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from app.graph.queries.personal import (
    ensure_student,
    get_state,
    get_states,
    merge_evidence,
    upsert_state,
)
from app.graph.schema import apply_schema
from app.schemas.knowledge import EvidenceContext, EvidenceIn, KnowledgeStateOut
from app.seed.skills import seed_skills

pytestmark = [
    pytest.mark.phase1,
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="module"),  # module-scoped driver fixtures
]


DATA = Path(__file__).resolve().parents[3] / "data"


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def seeded_graph(graph):
    await apply_schema(graph, 384)
    await seed_skills(graph, DATA / "skills")
    yield graph


async def test_ensure_student_idempotent(seeded_graph):
    sid = uuid4()
    await ensure_student(seeded_graph, sid)
    await ensure_student(seeded_graph, sid)
    async with seeded_graph.session() as session:
        result = await session.run(
            "MATCH (s:Student {id: $id}) RETURN count(s) AS n", id=str(sid)
        )
        rec = await result.single()
    assert rec["n"] == 1


async def test_upsert_state_creates_chain(seeded_graph):
    sid = uuid4()
    await ensure_student(seeded_graph, sid)

    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    s1 = _make_state("math.alg.linear_eq", "SAT_MATH", t0, p_at_obs=0.5)
    await upsert_state(seeded_graph, sid, s1, source_event_id=1)

    t1 = t0 + timedelta(hours=1)
    s2 = _make_state("math.alg.linear_eq", "SAT_MATH", t1, p_at_obs=0.75)
    await upsert_state(seeded_graph, sid, s2, source_event_id=2)

    async with seeded_graph.session() as session:
        result = await session.run(
            """
            MATCH (st:Student {id: $id})-[:HAS_STATE]->(k:KnowledgeState)
            WHERE k.exam_id = 'SAT_MATH'
            RETURN count(k) AS n
            """,
            id=str(sid),
        )
        rec = await result.single()
    assert rec["n"] == 1  # только последнее на HAS_STATE

    got = await get_state(seeded_graph, sid, "math.alg.linear_eq", "SAT_MATH")
    assert got is not None
    assert got.p_at_obs == pytest.approx(0.75)


async def test_merge_evidence_idempotent(seeded_graph):
    sid = uuid4()
    await ensure_student(seeded_graph, sid)
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    ev = _make_evidence(t0, event_id=42, skill_id="math.alg.linear_eq")

    await merge_evidence(seeded_graph, sid, ev)
    await merge_evidence(seeded_graph, sid, ev)

    async with seeded_graph.session() as session:
        result = await session.run(
            """
            MATCH (e:Evidence {event_id: 42, skill_id: 'math.alg.linear_eq'})
            RETURN count(e) AS n
            """
        )
        rec = await result.single()
    assert rec["n"] == 1


async def test_two_students_do_not_see_each_other(seeded_graph):
    sid1, sid2 = uuid4(), uuid4()
    await ensure_student(seeded_graph, sid1)
    await ensure_student(seeded_graph, sid2)
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    s = _make_state("math.alg.linear_eq", "SAT_MATH", t0, p_at_obs=0.5)
    await upsert_state(seeded_graph, sid1, s, source_event_id=1)

    states2 = await get_states(seeded_graph, sid2, "SAT_MATH")
    assert states2 == []


async def test_get_state_recomputes_p_recall(seeded_graph):
    sid = uuid4()
    await ensure_student(seeded_graph, sid)
    # get_state computes p_recall against the wall clock, so anchor the
    # observation to "now": half_life 24h → 24 hours later p_recall ≈ 0.5.
    now = datetime.now(UTC)
    s = _make_state("math.alg.linear_eq", "SAT_MATH", now, p_at_obs=0.8)
    s = s.model_copy(
        update={"half_life_h": 24.0, "last_observed_at": now - timedelta(hours=24)}
    )
    await upsert_state(seeded_graph, sid, s, source_event_id=1)

    got = await get_state(seeded_graph, sid, "math.alg.linear_eq", "SAT_MATH")
    assert got is not None
    assert got.p_recall == pytest.approx(0.5, abs=1e-3)


# --- helpers ---


def _make_state(
    skill_id: str, exam_id: str, t0: datetime, p_at_obs: float
) -> KnowledgeStateOut:
    return KnowledgeStateOut(
        skill_id=skill_id,
        exam_id=exam_id,
        p_recall=p_at_obs,
        p_at_obs=p_at_obs,
        half_life_h=24.0,
        confidence=0.5,
        evidence_mass=1.0,
        n_correct=1,
        n_incorrect=0,
        n_partial=0,
        has_strong=True,
        last_observed_at=t0,
        created_at=t0,
    )


def _make_evidence(t0: datetime, event_id: int, skill_id: str) -> EvidenceIn:
    return EvidenceIn(
        event_id=event_id,
        skill_id=skill_id,
        exam_id="SAT_MATH",
        kind="task",
        tier=2,
        source="task",
        weight=0.8,
        direction=1,
        share=None,
        difficulty_factor=1.0,
        summary=None,
        context=EvidenceContext(),
        observed_at=t0,
        extractor_version=None,
    )
