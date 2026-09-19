"""The soft factor inside ranking — §13.1 `test_rank_soft.py`."""

import pytest

from app.config import KnowledgeParams
from app.matching.hard import HardResult
from app.matching.rank import rank
from app.schemas.matching import FactorOut
from app.schemas.profile import Profile

pytestmark = pytest.mark.phase4

PARAMS = KnowledgeParams()


def _hard(program_id: str, status: str = "in_range") -> HardResult:
    return HardResult(
        program_id=program_id,
        realism_inputs={"exam_score": status},
        factors=[
            FactorOut(
                id="exam_score",
                kind="hard",
                status=status,
                text="порог",
                source=None,
                weight=3.0,
            )
        ],
        assumptions=[],
    )


def _order(soft_scores, results=None):
    profile = Profile(student_id=__import__("uuid").uuid4())
    results = results or [_hard("a"), _hard("b")]
    return [item.program_id for item in rank(profile, results, soft_scores, PARAMS)]


def test_soft_scores_reorder_within_a_level():
    assert _order({"a": 0.1, "b": 0.9}) == ["b", "a"]
    assert _order({"a": 0.9, "b": 0.1}) == ["a", "b"]


def test_missing_score_is_neutral_not_a_penalty():
    profile = Profile(student_id=__import__("uuid").uuid4())
    results = [_hard("a")]
    with_none = rank(profile, results, {"a": None}, PARAMS)[0]
    neutral = rank(profile, results, {"a": 0.5}, PARAMS)[0]
    assert with_none.score == pytest.approx(neutral.score)
    # А вот отсутствие ключа — это «мягкого фактора нет вовсе».
    without = rank(profile, results, {}, PARAMS)[0]
    assert without.score < with_none.score


def test_an_impossible_program_is_not_lifted_above_its_level():
    results = [_hard("possible", "in_range"), _hard("impossible", "below")]
    assert _order({"possible": 0.0, "impossible": 1.0}, results) == [
        "possible",
        "impossible",
    ]


def test_soft_contribution_uses_the_configured_weight():
    profile = Profile(student_id=__import__("uuid").uuid4())
    params = KnowledgeParams(matching_priority_weights={"program": 10, "realism": 3})
    ranked = rank(profile, [_hard("a")], {"a": 1.0}, params)[0]
    assert ranked.factors["soft"] == pytest.approx(10.0)
