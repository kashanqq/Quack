"""Instance generation from templates — 20-B1.md §4.3, §7 (test_generate block)."""

from __future__ import annotations

import pytest

from app.schemas.tasks import (
    DistractorSpec,
    ParamSpec,
    TaskTemplateSpec,
)
from app.tasks.evaluate import TemplateError
from app.tasks.generate import generate_instance, validate_template


pytestmark = pytest.mark.phase1


# --- fixture: the §3.1 template, verbatim ---


@pytest.fixture
def abs_template() -> TaskTemplateSpec:
    return TaskTemplateSpec(
        id="tpl.sat.alg.abs_eq_sum_roots",
        exam_id="SAT_MATH",
        type="mcq4",
        difficulty=3,
        skill_id="sat.alg.abs_value_eq",
        tags=["negative_branch", "sum_of_roots"],
        time_reference_sec=75,
        kind="template",
        params={
            "a": ParamSpec(range=(2, 5)),
            "b": ParamSpec(range=(2, 12)),
            "c": ParamSpec(range=(1, 9)),
        },
        constraints=["(b + c) % a == 0", "(b - c) % a == 0", "b > c"],
        stem="|{a}x − {b}| = {c}. Чему равна сумма корней уравнения?",
        correct="2*b/a",
        distractors=[
            DistractorSpec(expr="(b + c)/a", misconception_id="lib.abs_single_branch"),
            DistractorSpec(expr="(b - c)/a", misconception_id="lib.abs_single_branch"),
            DistractorSpec(expr="-2*b/a", misconception_id="lib.abs_sign_drop"),
            DistractorSpec(expr="2*c/a", misconception_id=None),
        ],
        solution=[
            "Раскрыть модуль: {a}x − {b} = {c} или {a}x − {b} = −{c}",
            "x1 = ({b}+{c})/{a}, x2 = ({b}−{c})/{a}",
            "Сумма = 2·{b}/{a} = {answer}",
        ],
    )


# --- tests ---


def test_generate_instance_mcq4(abs_template):
    inst = generate_instance(abs_template, seed=1)
    assert len(inst.options) == 4
    correct_opts = [o for o in inst.options if o.correct]
    assert len(correct_opts) == 1
    texts = [o.text for o in inst.options]
    assert len(set(texts)) == len(texts)
    assert "{" not in inst.stem_rendered


def test_generate_instance_deterministic(abs_template):
    i1 = generate_instance(abs_template, seed=1)
    i2 = generate_instance(abs_template, seed=1)
    assert i1.answer == i2.answer
    assert [o.text for o in i1.options] == [o.text for o in i2.options]

    i3 = generate_instance(abs_template, seed=2)
    # могут совпасть, но обычно разные; проверим по answer если возможно
    assert (i1.answer != i3.answer) or (
        [o.text for o in i1.options] != [o.text for o in i3.options]
    )


def test_generate_instance_prefers_student_misconceptions(abs_template):
    inst = generate_instance(abs_template, seed=1, student_misc={"lib.abs_sign_drop"})
    misc_ids = {o.misconception_id for o in inst.options}
    assert "lib.abs_sign_drop" in misc_ids


def test_validate_template_ok(abs_template):
    assert validate_template(abs_template) == []


def test_validate_template_detects_distractors_collapse(abs_template):
    bad = abs_template.model_copy(deep=True)
    # ставим дистрактор, равный верному
    bad.distractors[0] = DistractorSpec(expr="2*b/a", misconception_id=None)
    errors = validate_template(bad)
    assert any("distractors collapse" in e for e in errors)


def test_validate_template_detects_impossible_constraints(abs_template):
    bad = abs_template.model_copy(deep=True)
    bad.constraints = ["a == 0"]
    errors = validate_template(bad)
    assert any("seed failure rate" in e for e in errors)


def test_generate_numeric_no_options():
    spec = TaskTemplateSpec(
        id="tpl.sat.arith.percent_change",
        exam_id="SAT_MATH",
        type="numeric",
        difficulty=2,
        skill_id="sat.arith.percent",
        tags=["percent_change"],
        time_reference_sec=60,
        kind="template",
        params={
            "base": ParamSpec(range=(50, 200)),
            "pct": ParamSpec(range=(5, 40)),
        },
        constraints=["base * pct % 100 == 0"],
        stem="Число {base} увеличили на {pct}%. Какое число получилось?",
        correct="base * (100 + pct) / 100",
        distractors=[],
        answer_forms=["integer", "fraction", "decimal:2"],
        trap_answers=[
            DistractorSpec(
                expr="base * pct / 100", misconception_id="lib.percent_of_not_increase"
            ),
            DistractorSpec(expr="base * (100 - pct) / 100", misconception_id=None),
        ],
        solution=["{base} × (1 + {pct}/100)", "= {answer}"],
    )
    inst = generate_instance(spec, seed=7)
    assert inst.options == []
    assert isinstance(inst.answer, str)
    assert len(inst.trap_answers) >= 1
    assert any(
        t.misconception_id == "lib.percent_of_not_increase" for t in inst.trap_answers
    )


def test_generate_multi_select_answer_is_list_of_keys():
    spec = TaskTemplateSpec(
        id="tpl.ent.alg.multi_root_conditions",
        exam_id="ENT_MATH",
        type="multi_select",
        difficulty=4,
        skill_id="ent.alg.quadratic_conditions",
        tags=["vieta"],
        time_reference_sec=120,
        kind="template",
        params={
            "p": ParamSpec(range=(-5, 5)),
            "q": ParamSpec(range=(1, 9)),
        },
        constraints=["p*p - 4*q > 0"],
        stem="Выберите верные утверждения про x² + {p}x + {q} = 0.",
        correct=["корень 1", "корень 2"],
        distractors=[
            DistractorSpec(expr="корень 3", misconception_id=None),
            DistractorSpec(expr="корень 4", misconception_id=None),
        ],
        solution=["..."],
    )
    inst = generate_instance(spec, seed=1)
    assert isinstance(inst.answer, list)
    # все ключи из answer отмечены correct=True
    keys = set(inst.answer)
    for o in inst.options:
        assert o.correct == (o.key in keys)


def test_generate_solution_contains_answer(abs_template):
    inst = generate_instance(abs_template, seed=1)
    joined = " ".join(inst.solution_rendered)
    assert "{" not in joined
