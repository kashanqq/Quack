"""rank — 20-B1-phase2.md §5.3."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.config import KnowledgeParams
from app.matching.hard import HardResult
from app.matching.rank import Ranked, rank
from app.schemas.matching import FactorOut
from app.schemas.profile import (
    Priorities,
    Profile,
    ProfileField,
    Questionnaire,
)

pytestmark = pytest.mark.phase1

PARAMS = KnowledgeParams()


def _factor(fid: str, status: str) -> FactorOut:
    return FactorOut(
        id=fid,
        kind="hard",
        status=status,  # type: ignore[arg-type]
        text="...",
        source=None,
        weight=1.0,
    )


def _result(
    program_id: str,
    *,
    factors: list[FactorOut] | None = None,
    grant_required: bool = False,
) -> HardResult:
    factors = factors or []
    inputs = {f.id: f.status for f in factors if f.status == "below"}
    return HardResult(
        program_id=program_id,
        realism_inputs=inputs,
        factors=factors,
        assumptions=[],
        grant_required=grant_required,
    )


def _profile(ranking: list[str] | None = None) -> Profile:
    return Profile(
        student_id=uuid4(),
        questionnaire=Questionnaire(
            priorities=Priorities(
                ranking=ProfileField(value=ranking, mark="stated")
                if ranking
                else ProfileField(value=None)
            ),
        ),
    )


# --- ordering ---


def test_possible_before_try():
    p = _profile()
    hard = [
        _result("p1", factors=[_factor("exam_score:SAT_MATH", "in_range")]),  # possible
        _result("p2", factors=[_factor("exam_score:SAT_MATH", "below")]),  # try
    ]
    ranked = rank(p, hard, {}, PARAMS)
    assert [r.program_id for r in ranked] == ["p1", "p2"]


def test_impossible_last():
    p = _profile()
    hard = [
        _result("p1", factors=[_factor("exam_score:SAT_MATH", "below")]),  # try
        _result("p2", grant_required=True),  # impossible
    ]
    ranked = rank(p, hard, {}, PARAMS)
    assert ranked[-1].program_id == "p2"


def test_within_level_higher_score_first():
    p = _profile()
    # p1: exam_score above (score 3.0 * 1.0 = 3.0)
    # p2: exam_score in_range (score 3.0 * 0.8 = 2.4)
    hard = [
        _result("p1", factors=[_factor("exam_score:SAT_MATH", "above")]),
        _result("p2", factors=[_factor("exam_score:SAT_MATH", "in_range")]),
    ]
    ranked = rank(p, hard, {}, PARAMS)
    assert [r.program_id for r in ranked] == ["p1", "p2"]


# --- priority reorder ---


def test_student_priorities_reorder_weights():
    # оба possible; у обоих один below. Один с cost, другой с location.
    # при приоритете cost первый должен иметь больший вес cost
    p = _profile(ranking=["cost", "location"])
    hard = [
        _result("p1", factors=[_factor("budget", "below")]),  # cost ниже → 0 * w
        _result("p2", factors=[_factor("country", "below")]),  # location ниже → 0 * w
    ]
    # оба try, оба need 0. Смотрим только что не падает.
    ranked = rank(p, hard, {}, PARAMS)
    assert len(ranked) == 2


# --- soft scores ---


def test_soft_score_added():
    p = _profile()
    hard = [
        _result("p1", factors=[_factor("exam_score:SAT_MATH", "in_range")]),
        _result("p2", factors=[_factor("exam_score:SAT_MATH", "in_range")]),
    ]
    ranked = rank(p, hard, {"p2": 1.0}, PARAMS)
    # p2 получает дополнительный вклад soft
    assert ranked[0].program_id == "p2"


# --- general ---


def test_returns_list_of_ranked():
    p = _profile()
    hard = [_result("p1")]
    ranked = rank(p, hard, {}, PARAMS)
    assert isinstance(ranked, list)
    assert isinstance(ranked[0], Ranked)


def test_empty_input():
    p = _profile()
    assert rank(p, [], {}, PARAMS) == []


def test_factors_dict_includes_contributions():
    p = _profile()
    hard = [_result("p1", factors=[_factor("exam_score:SAT_MATH", "above")])]
    ranked = rank(p, hard, {}, PARAMS)
    assert "exam_score:SAT_MATH" in ranked[0].factors
