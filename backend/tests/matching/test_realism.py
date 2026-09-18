"""realism — 20-B1-phase2.md §5.2."""

from __future__ import annotations

import pytest

from app.config import KnowledgeParams
from app.matching.hard import HardResult
from app.matching.realism import realism

pytestmark = pytest.mark.phase1

PARAMS = KnowledgeParams()


def _result(
    *,
    inputs: dict | None = None,
    grant_required: bool = False,
) -> HardResult:
    return HardResult(
        program_id="p1",
        realism_inputs=inputs or {},
        factors=[],
        assumptions=[],
        grant_required=grant_required,
    )


def test_grant_required_is_impossible():
    r = _result(grant_required=True)
    assert realism(r, PARAMS) == "impossible"


def test_all_in_range_is_possible():
    r = _result(inputs={"exam_score:SAT_MATH": "in_range", "language": "in_range"})
    assert realism(r, PARAMS) == "possible"


def test_any_below_is_try():
    r = _result(inputs={"exam_score:SAT_MATH": "below", "language": "in_range"})
    assert realism(r, PARAMS) == "try"


def test_unknown_does_not_penalize():
    r = _result(inputs={"exam_score:SAT_MATH": "unknown"})
    assert realism(r, PARAMS) == "possible"


def test_empty_inputs_possible():
    assert realism(_result(), PARAMS) == "possible"


def test_grant_required_overrides_below():
    r = _result(inputs={"budget": "below"}, grant_required=True)
    assert realism(r, PARAMS) == "impossible"


def test_above_is_possible():
    r = _result(inputs={"exam_score:SAT_MATH": "above"})
    assert realism(r, PARAMS) == "possible"
