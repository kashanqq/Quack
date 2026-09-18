"""Integration tests for phase-2 personal-layer queries.

Requires a live Neo4j with the seeded canonical graph. The `graph` fixture
comes from tests/graph/conftest.py (module-scope, skips if Neo4j is down).

Source: 20-B1-phase2.md §8.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from app.graph.queries.personal import (
    add_root_cause,
    ensure_student,
    get_misc_states,
    get_state_history,
    list_evidence,
    list_root_causes,
    merge_evidence,
    upsert_misc_state,
    upsert_state,
)
from app.graph.schema import apply_schema
from app.schemas.knowledge import (
    EvidenceContext,
    EvidenceIn,
    KnowledgeStateOut,
)
from app.seed.misconceptions import seed_misconceptions
from app.seed.skills import seed_skills

pytestmark = [pytest.mark.phase1, pytest.mark.integration]

DATA = Path(__file__).resolve().parents[3] / "data"
NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


@pytest_asyncio.fixture(scope="module")
async def seeded(graph):
    """Seed skills and misconceptions once for the module."""
    await apply_schema(graph, 384)
    await seed_skills(graph, DATA / "skills")

    class _FakeEmbedder:
        def embed(self, texts):
            return [[0.0] * 384 for _ in texts]

    await seed_misconceptions(graph, DATA / "misconceptions", embedder=_FakeEmbedder())
    yield graph


def _state(skill_id: str, exam_id: str = "SAT_MATH") -> KnowledgeStateOut:
    return KnowledgeStateOut(
        skill_id=skill_id,
        exam_id=exam_id,  # type: ignore[arg-type]
        p_recall=0.5,
        p_at_obs=0.5,
        half_life_h=24.0,
        confidence=0.5,
        evidence_mass=1.0,
        n_correct=1,
        n_incorrect=0,
        n_partial=0,
        has_strong=True,
        last_observed_at=NOW - timedelta(hours=1),
        created_at=NOW - timedelta(days=1),
    )


def _evidence(event_id: int, skill_id: str) -> EvidenceIn:
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
        observed_at=NOW,
        extractor_version=None,
    )


# --- misconceptions ---


async def test_get_misc_states_empty(seeded):
    sid = uuid4()
    await ensure_student(seeded, sid)
    states = await get_misc_states(seeded, sid, ["math.alg.abs_value_eq"])
    assert states == []


async def test_upsert_misc_state_creates_and_reads(seeded):
    sid = uuid4()
    await ensure_student(seeded, sid)
    result = await upsert_misc_state(
        seeded,
        sid,
        "lib.abs_single_branch",
        status="suspected",
        counters={"occurrence_count": 1, "strong_count": 0, "consecutive_avoided": 0},
        triggers={"n": 1},
    )
    assert result.misconception_id == "lib.abs_single_branch"
    assert result.status == "suspected"

    states = await get_misc_states(seeded, sid, ["math.alg.abs_value_eq"])
    assert len(states) == 1
    assert states[0].occurrence_count == 1


async def test_upsert_misc_state_updates_existing(seeded):
    sid = uuid4()
    await ensure_student(seeded, sid)
    await upsert_misc_state(
        seeded,
        sid,
        "lib.abs_single_branch",
        "suspected",
        {"occurrence_count": 1, "strong_count": 0, "consecutive_avoided": 0},
    )
    result = await upsert_misc_state(
        seeded,
        sid,
        "lib.abs_single_branch",
        "confirmed",
        {"occurrence_count": 2, "strong_count": 1, "consecutive_avoided": 0},
    )
    assert result.status == "confirmed"
    assert result.occurrence_count == 2

    # не создалось дубля
    states = await get_misc_states(seeded, sid, ["math.alg.abs_value_eq"])
    assert len(states) == 1


# --- evidence ---


async def test_merge_evidence_and_list(seeded):
    sid = uuid4()
    await ensure_student(seeded, sid)
    await merge_evidence(seeded, sid, _evidence(42, "math.alg.linear_eq"))
    evidence = await list_evidence(seeded, sid, "math.alg.linear_eq")
    assert len(evidence) == 1
    assert evidence[0].event_id == 42
    assert evidence[0].evidence_id == "42:math.alg.linear_eq"


# --- root causes ---


async def test_add_root_cause_and_list(seeded):
    sid = uuid4()
    await ensure_student(seeded, sid)
    await merge_evidence(seeded, sid, _evidence(99, "sat.alg.abs_value_eq"))
    await add_root_cause(
        seeded,
        "99:sat.alg.abs_value_eq",
        "math.alg.linear_eq",
        confidence=0.4,
        source="rule",
    )
    roots = await list_root_causes(seeded, sid, window_days=30)
    assert len(roots) == 1
    assert roots[0].root_skill_id == "math.alg.linear_eq"
    assert roots[0].source == "rule"


async def test_add_root_cause_idempotent(seeded):
    sid = uuid4()
    await ensure_student(seeded, sid)
    await merge_evidence(seeded, sid, _evidence(77, "sat.alg.abs_value_eq"))
    await add_root_cause(
        seeded, "77:sat.alg.abs_value_eq", "math.alg.linear_eq", 0.4, "rule"
    )
    await add_root_cause(
        seeded, "77:sat.alg.abs_value_eq", "math.alg.linear_eq", 0.4, "rule"
    )
    roots = await list_root_causes(seeded, sid, window_days=30)
    assert len(roots) == 1


# --- state history ---


async def test_get_state_history_walks_previous(seeded):
    sid = uuid4()
    await ensure_student(seeded, sid)
    s1 = _state("math.alg.quadratic_roots")
    s2 = _state("math.alg.quadratic_roots").model_copy(update={"p_at_obs": 0.7})
    await upsert_state(seeded, sid, s1, source_event_id=1)
    await upsert_state(seeded, sid, s2, source_event_id=2)

    history = await get_state_history(
        seeded, sid, "math.alg.quadratic_roots", "SAT_MATH", n=3
    )
    assert len(history) == 2
    # newest first
    assert history[0].p_at_obs == pytest.approx(0.7)
    assert history[1].p_at_obs == pytest.approx(0.5)
