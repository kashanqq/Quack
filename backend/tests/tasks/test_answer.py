"""Answer grading — 20-B1.md §4.4, §7 (test_answer block)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sympy import Rational

from app.schemas.tasks import Option, TaskInstance
from app.tasks.answer import grade


pytestmark = pytest.mark.phase1


def _mcq4() -> TaskInstance:
    return TaskInstance(
        id=uuid4(),
        template_id="tpl.sat.alg.abs_eq_sum_roots",
        seed=1,
        exam_id="SAT_MATH",
        type="mcq4",
        skill_id="sat.alg.abs_value_eq",
        stem_rendered="...",
        options=[
            Option(key="A", text="6", correct=True, misconception_id=None),
            Option(
                key="B",
                text="5",
                correct=False,
                misconception_id="lib.abs_single_branch",
            ),
            Option(
                key="C", text="-6", correct=False, misconception_id="lib.abs_sign_drop"
            ),
            Option(key="D", text="3", correct=False, misconception_id=None),
        ],
        answer="A",
        trap_answers=[],
        solution_rendered=["..."],
        time_reference_sec=75,
        difficulty=3,
        tags=[],
    )


def _numeric() -> TaskInstance:
    return TaskInstance(
        id=uuid4(),
        template_id="tpl.sat.arith.percent_change",
        seed=1,
        exam_id="SAT_MATH",
        type="numeric",
        skill_id="sat.arith.percent",
        stem_rendered="...",
        options=[],
        answer="5/2",
        trap_answers=[
            Option(key="T1", text="2.5", correct=False, misconception_id="lib.x"),
            Option(
                key="T2",
                text="2.4",
                correct=False,
                misconception_id="lib.percent_of_not_increase",
            ),
        ],
        solution_rendered=["..."],
        time_reference_sec=60,
        difficulty=2,
        tags=[],
    )


def _multi_select() -> TaskInstance:
    return TaskInstance(
        id=uuid4(),
        template_id="tpl.ent.alg.multi_root_conditions",
        seed=1,
        exam_id="ENT_MATH",
        type="multi_select",
        skill_id="ent.alg.quadratic_conditions",
        stem_rendered="...",
        options=[
            Option(key="A", text="r1", correct=True, misconception_id=None),
            Option(key="B", text="r2", correct=True, misconception_id=None),
            Option(key="C", text="w1", correct=False, misconception_id=None),
            Option(
                key="D",
                text="w2",
                correct=False,
                misconception_id="lib.vieta_sign_confusion",
            ),
        ],
        answer=["A", "B"],
        trap_answers=[
            Option(
                key="B", text="r2", correct=False, misconception_id="lib.omission_r2"
            ),
        ],
        solution_rendered=["..."],
        time_reference_sec=120,
        difficulty=4,
        tags=[],
    )


# --- mcq ---


def test_mcq_correct_key():
    g = grade(_mcq4(), "A")
    assert g.correct is True
    assert g.matched_misconception_id is None


def test_mcq_distractor_with_misconception():
    g = grade(_mcq4(), "B")
    assert g.correct is False
    assert g.matched_misconception_id == "lib.abs_single_branch"


def test_mcq_distractor_without_misconception():
    g = grade(_mcq4(), "D")
    assert g.correct is False
    assert g.matched_misconception_id is None


def test_mcq_unknown_key():
    g = grade(_mcq4(), "Z")
    assert g.correct is False
    assert g.matched_misconception_id is None


# --- numeric ---


def test_numeric_fraction_form():
    g = grade(_numeric(), "5/2")
    assert g.correct is True


def test_numeric_decimal_form_two_places():
    # answer_forms не в инстансе, но тест ожидает, что 2.5 == 5/2
    g = grade(_numeric(), "2.5")
    assert g.correct is True


def test_numeric_wrong_value():
    g = grade(_numeric(), "2.4")
    assert g.correct is False
    assert g.matched_misconception_id == "lib.percent_of_not_increase"


# --- multi_select ---


def test_multi_all_correct_none_wrong():
    g = grade(_multi_select(), ["A", "B"])
    assert g.correct is True
    assert g.partial == pytest.approx(1.0)


def test_multi_half_correct():
    g = grade(_multi_select(), ["A"])
    assert g.correct is False
    assert g.partial == pytest.approx(0.5)
    assert "lib.omission_r2" in g.omitted_misconception_ids


def test_multi_correct_plus_distractor():
    g = grade(_multi_select(), ["A", "B", "D"])
    assert g.correct is False
    assert g.matched_misconception_id == "lib.vieta_sign_confusion"
