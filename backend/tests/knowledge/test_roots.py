"""Root-cause rules — memory-architecture §6, §10.1.

Numbers from 20-B1-phase2.md §2.3.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.config import KnowledgeParams
from app.knowledge.roots import (
    diagnostic_root,
    root_boost_skills,
    rule_root,
)
from app.schemas.knowledge import (
    KnowledgeStateOut,
    Prerequisite,
    RootCauseOut,
)

pytestmark = pytest.mark.phase1

PARAMS = KnowledgeParams()
NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def _state(
    skill_id: str,
    *,
    p_recall: float = 0.5,
    confidence: float = 0.8,
) -> KnowledgeStateOut:
    return KnowledgeStateOut(
        skill_id=skill_id,
        exam_id="SAT_MATH",
        p_recall=p_recall,
        p_at_obs=p_recall,
        half_life_h=24.0,
        confidence=confidence,
        evidence_mass=1.0,
        n_correct=1,
        n_incorrect=0,
        n_partial=0,
        has_strong=True,
        last_observed_at=NOW - timedelta(days=1),
        created_at=NOW - timedelta(days=2),
    )


def _prereq(skill_id: str, strength: float) -> Prerequisite:
    return Prerequisite(skill_id=skill_id, strength=strength, depth=1)


# --- rule_root ---


def test_rule_root_returns_none_when_prereq_strong():
    prereqs = [
        (
            _prereq("math.alg.linear_eq", 0.9),
            _state("math.alg.linear_eq", p_recall=0.85),
        )
    ]
    assert rule_root("sat.alg.abs_value_eq", prereqs, params=PARAMS) is None


def test_rule_root_returns_none_when_confidence_low():
    prereqs = [
        (
            _prereq("math.alg.linear_eq", 0.9),
            _state("math.alg.linear_eq", p_recall=0.3, confidence=0.4),
        )
    ]
    # p < 0.5 верно, но conf 0.4 < 0.5 — недостаточно
    assert rule_root("sat.alg.abs_value_eq", prereqs, params=PARAMS) is None


def test_rule_root_returns_root_when_p_low_and_conf_high():
    prereqs = [
        (
            _prereq("math.alg.linear_eq", 0.9),
            _state("math.alg.linear_eq", p_recall=0.4, confidence=0.7),
        )
    ]
    root = rule_root("sat.alg.abs_value_eq", prereqs, params=PARAMS)
    assert root is not None
    assert root.from_skill_id == "sat.alg.abs_value_eq"
    assert root.root_skill_id == "math.alg.linear_eq"
    assert root.confidence == pytest.approx(0.4)
    assert root.source == "rule"


def test_rule_root_picks_strongest_strength():
    prereqs = [
        (
            _prereq("math.arith.fractions", 0.5),
            _state("math.arith.fractions", p_recall=0.3, confidence=0.8),
        ),
        (
            _prereq("math.alg.linear_eq", 0.9),
            _state("math.alg.linear_eq", p_recall=0.3, confidence=0.8),
        ),
        (
            _prereq("math.alg.linear_ineq", 0.6),
            _state("math.alg.linear_ineq", p_recall=0.3, confidence=0.8),
        ),
    ]
    root = rule_root("sat.alg.abs_value_eq", prereqs, params=PARAMS)
    assert root is not None
    assert root.root_skill_id == "math.alg.linear_eq"  # strength 0.9


def test_rule_root_ignores_missing_state():
    prereqs = [(_prereq("math.alg.linear_eq", 0.9), None)]
    assert rule_root("sat.alg.abs_value_eq", prereqs, params=PARAMS) is None


# --- diagnostic_root ---


def test_diagnostic_root_confidence_and_source():
    root = diagnostic_root("sat.alg.abs_value_eq", "math.alg.linear_eq")
    assert root.from_skill_id == "sat.alg.abs_value_eq"
    assert root.root_skill_id == "math.alg.linear_eq"
    assert root.confidence == pytest.approx(0.8)
    assert root.source == "diagnostic"


# --- root_boost_skills ---


def test_root_boost_skills_empty():
    assert root_boost_skills([], params=PARAMS, now=NOW) == set()


def test_root_boost_skills_below_sum_threshold():
    # Σ confidence = 0.4 + 0.4 = 0.8 < 1.0
    roots = [
        RootCauseOut(
            from_skill_id="sat.alg.abs_value_eq",
            root_skill_id="math.alg.linear_eq",
            confidence=0.4,
            source="rule",
            created_at=NOW - timedelta(days=1),
        ),
        RootCauseOut(
            from_skill_id="sat.alg.abs_value_eq",
            root_skill_id="math.alg.linear_eq",
            confidence=0.4,
            source="rule",
            created_at=NOW - timedelta(days=1),
        ),
    ]
    assert root_boost_skills(roots, params=PARAMS, now=NOW) == set()


def test_root_boost_skills_at_or_above_threshold():
    # Σ confidence = 0.8 + 0.4 = 1.2 ≥ 1.0
    roots = [
        RootCauseOut(
            from_skill_id="sat.alg.abs_value_eq",
            root_skill_id="math.alg.linear_eq",
            confidence=0.8,
            source="diagnostic",
            created_at=NOW - timedelta(days=1),
        ),
        RootCauseOut(
            from_skill_id="sat.alg.abs_value_eq",
            root_skill_id="math.alg.linear_eq",
            confidence=0.4,
            source="rule",
            created_at=NOW - timedelta(days=1),
        ),
    ]
    assert root_boost_skills(roots, params=PARAMS, now=NOW) == {"math.alg.linear_eq"}


def test_root_boost_skills_ignores_old():
    # корень старше окна root_window_days
    roots = [
        RootCauseOut(
            from_skill_id="sat.alg.abs_value_eq",
            root_skill_id="math.alg.linear_eq",
            confidence=1.5,
            source="diagnostic",
            created_at=NOW - timedelta(days=PARAMS.root_window_days + 1),
        ),
    ]
    assert root_boost_skills(roots, params=PARAMS, now=NOW) == set()


def test_root_boost_skills_multiple_roots():
    roots = [
        RootCauseOut(
            from_skill_id="a",
            root_skill_id="x",
            confidence=1.0,
            source="rule",
            created_at=NOW - timedelta(days=1),
        ),
        RootCauseOut(
            from_skill_id="b",
            root_skill_id="y",
            confidence=1.0,
            source="rule",
            created_at=NOW - timedelta(days=1),
        ),
    ]
    assert root_boost_skills(roots, params=PARAMS, now=NOW) == {"x", "y"}
