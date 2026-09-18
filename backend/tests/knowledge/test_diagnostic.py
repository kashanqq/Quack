"""knowledge.diagnostic — memory-architecture §8.4, 20-B1-phase2.md §2.4."""

from __future__ import annotations

import pytest

from app.config import KnowledgeParams
from app.knowledge.diagnostic import (
    apply_answer,
    finish,
    next_skill,
    start,
)
from app.schemas.common import ExamId
from app.schemas.diagnostic import DiagnosticState
from app.schemas.knowledge import (
    AreaOut,
    Prerequisite,
    RootCauseOut,
    SkillRef,
    SkillWeight,
)
from app.schemas.tasks import Grade

pytestmark = pytest.mark.phase1

PARAMS = KnowledgeParams()
EXAM: ExamId = "SAT_MATH"


def _skill(skill_id: str, *, exam_id: str = EXAM) -> SkillRef:
    return SkillRef(
        id=skill_id,
        name=skill_id,
        description="...",
        exam_ids=[exam_id],  # type: ignore[list-item]
        effort_h=4.0,
        base_half_life_h=None,
    )


def _weight(
    skill_id: str, weight: float = 3.0, area: str = "area.sat.algebra"
) -> SkillWeight:
    return SkillWeight(skill=_skill(skill_id), area_id=area, weight=weight)


def _area(area_id: str = "area.sat.algebra", share: float = 1.0) -> AreaOut:
    return AreaOut(id=area_id, name=area_id, score_share=share)


def _prereq(skill_id: str, strength: float = 0.9) -> Prerequisite:
    return Prerequisite(skill_id=skill_id, strength=strength, depth=1)


def _correct() -> Grade:
    return Grade(correct=True)


def _wrong(misc_id: str | None = None) -> Grade:
    return Grade(correct=False, matched_misconception_id=misc_id)


# --- start ---


def test_start_with_default_budget():
    skills = [_weight("a"), _weight("b")]
    areas = [_area()]
    state = start(skills, areas, [], [], budget=None, params=PARAMS)
    assert state.exam_id == EXAM
    assert state.budget_left == PARAMS.diag_base
    assert state.reserve_left == PARAMS.diag_reserve
    assert state.budget_order  # непустой порядок


def test_start_with_explicit_budget():
    skills = [_weight("a")]
    state = start(skills, [_area()], [], [], budget=5, params=PARAMS)
    assert state.budget_left == 5


def test_start_roots_first_in_pending_descent():
    skills = [_weight("a"), _weight("b")]
    roots = [
        RootCauseOut(
            from_skill_id="x",
            root_skill_id="b",
            confidence=0.8,
            source="diagnostic",
            created_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ),
        )
    ]
    state = start(skills, [_area()], [], roots, budget=None, params=PARAMS)
    assert state.pending_descent[0] == "b"


# --- next_skill ---


def test_next_skill_from_budget_order():
    skills = [_weight("a"), _weight("b")]
    state = start(skills, [_area()], [], [], budget=None, params=PARAMS)
    nxt = next_skill(state, [], params=PARAMS)
    assert nxt in ("a", "b")


def test_next_skill_returns_none_when_budget_exhausted():
    skills = [_weight("a")]
    state = start(skills, [_area()], [], [], budget=1, params=PARAMS)
    # Отвечаем на один — исчерпываем бюджет
    state = apply_answer(state, "a", _correct(), [], params=PARAMS)
    assert next_skill(state, [], params=PARAMS) is None


# --- apply_answer ---


def test_apply_correct_moves_to_firm():
    skills = [_weight("a")]
    state = start(skills, [_area()], [], [], budget=None, params=PARAMS)
    state2 = apply_answer(state, "a", _correct(), [], params=PARAMS)
    assert "a" in state2.firm
    assert state2.budget_left == state.budget_left - 1


def test_apply_wrong_moves_to_shaky():
    skills = [_weight("a")]
    state = start(skills, [_area()], [], [], budget=None, params=PARAMS)
    state2 = apply_answer(state, "a", _wrong(), [], params=PARAMS)
    assert "a" in state2.shaky


def test_apply_wrong_with_reserve_pushes_strongest_prereq():
    skills = [_weight("a")]
    state = start(skills, [_area()], [], [], budget=None, params=PARAMS)
    prereqs = [_prereq("p1", 0.5), _prereq("p2", 0.9)]
    state2 = apply_answer(state, "a", _wrong(), prereqs, params=PARAMS)
    # Самая сильная предпосылка — p2
    assert state2.pending_descent[0] == "p2"


def test_apply_wrong_without_reserve_does_not_descend():
    skills = [_weight("a")]
    state = start(skills, [_area()], [], [], budget=1, params=PARAMS)
    # Принудительно исчерпаем резерв
    state = state.model_copy(update={"reserve_left": 0})
    state2 = apply_answer(state, "a", _wrong(), [_prereq("p1")], params=PARAMS)
    assert "p1" not in state2.pending_descent


def test_apply_wrong_with_reserve_pushes_prereq():
    skills = [_weight("a")]
    state = start(skills, [_area()], [], [], budget=1, params=PARAMS)
    state2 = apply_answer(state, "a", _wrong(), [_prereq("p1", 0.9)], params=PARAMS)
    assert "p1" in state2.pending_descent


def test_apply_trap_hit_adds_to_reask_queue():
    skills = [_weight("a")]
    state = start(skills, [_area()], [], [], budget=None, params=PARAMS)
    state2 = apply_answer(state, "a", _wrong("lib.x"), [], params=PARAMS)
    assert any(sid == "a" for sid, _ in state2.reask_queue)
    assert "lib.x" in state2.trap_hits


def test_apply_correct_marks_indirect_for_prereqs():
    skills = [_weight("a")]
    state = start(skills, [_area()], [], [], budget=None, params=PARAMS)
    prereqs = [_prereq("p1")]
    state2 = apply_answer(state, "a", _correct(), prereqs, params=PARAMS)
    # indirect должен содержать p1 с весом prior_indirect_weight
    assert any(sid == "p1" for sid, _ in state2.indirect)


# --- finish ---


def test_finish_empty_state():
    skills = [_weight("a")]
    state = start(skills, [_area()], [], [], budget=None, params=PARAMS)
    result = finish(state, {}, params=PARAMS)
    assert result.firm == []
    assert result.shaky == []
    assert result.start_from == []
    assert isinstance(result.words, str)


def test_finish_start_from_from_shaky_without_shaky_prereqs():
    skills = [_weight("a"), _weight("b")]
    state = start(skills, [_area()], [], [], budget=None, params=PARAMS)
    state = apply_answer(state, "a", _correct(), [], params=PARAMS)
    state = apply_answer(state, "b", _wrong(), [], params=PARAMS)
    result = finish(state, {}, params=PARAMS)
    assert "b" in result.shaky
    assert "b" in result.start_from


def test_finish_words_is_nonempty():
    skills = [_weight("a")]
    state = start(skills, [_area()], [], [], budget=None, params=PARAMS)
    state = apply_answer(state, "a", _correct(), [], params=PARAMS)
    result = finish(state, {}, params=PARAMS)
    assert result.words


# --- integrity ---


def test_state_is_pydantic():
    skills = [_weight("a")]
    state = start(skills, [_area()], [], [], budget=None, params=PARAMS)
    assert isinstance(state, DiagnosticState)
    # сериализуется в JSON-совместимый dict
    dumped = state.model_dump(mode="json")
    DiagnosticState.model_validate(dumped)
