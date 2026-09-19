"""tasks.mocks — 20-B1-phase2.md §4.2."""

from __future__ import annotations

import random

import pytest

from app.config import KnowledgeParams
from app.schemas.knowledge import Section
from app.schemas.tasks import (
    DistractorSpec,
    Grade,
    ParamSpec,
    TaskTemplateSpec,
)
from app.tasks.mocks import assemble_mock, score

pytestmark = pytest.mark.phase1

PARAMS = KnowledgeParams()


def _section(
    item_types: dict[str, int] | None = None,
    *,
    rule: str = "mcq5: 1 per correct",
) -> Section:
    return Section(
        name="M1",
        n_items=10,
        minutes=35,
        item_types=item_types or {"mcq4": 8, "numeric": 2},
        scoring_rule=rule,
        calculator=True,
        adaptive=False,
        area_shares={"area.sat.algebra": 1.0},
        difficulty_shares={"2": 0.5, "3": 0.5},
        answer_forms=["integer"],
    )


def _template(
    tid: str,
    *,
    skill_id: str = "skill.a",
    type_: str = "mcq4",
    difficulty: int = 3,
    distractors: list[DistractorSpec] | None = None,
) -> TaskTemplateSpec:
    return TaskTemplateSpec(
        id=tid,
        exam_id="SAT_MATH",
        type=type_,  # type: ignore[arg-type]
        difficulty=difficulty,
        skill_id=skill_id,
        tags=[],
        time_reference_sec=60,
        kind="template",
        params={"a": ParamSpec(range=(2, 5))},
        constraints=[],
        stem=f"stem {tid}",
        correct="1",
        distractors=distractors
        if distractors is not None
        else [DistractorSpec(expr="2", misconception_id=None)],
        solution=["..."],
    )


# --- mock_topic ---


def test_mock_topic_picks_n_from_range():
    templates = {"skill.a": [_template(f"t{i}", skill_id="skill.a") for i in range(10)]}
    rng = random.Random(42)
    tasks = assemble_mock("mock_topic", _section(), templates, {}, rng, PARAMS)
    assert PARAMS.mock_topic_min <= len(tasks) <= PARAMS.mock_topic_max


def test_mock_topic_empty_pool():
    tasks = assemble_mock("mock_topic", _section(), {}, {}, random.Random(1), PARAMS)
    assert tasks == []


# --- mock_set ---


def test_mock_set_covers_types():
    templates = {
        "skill.a": [
            *[
                _template(f"mcq{i}", skill_id="skill.a", type_="mcq4")
                for i in range(10)
            ],
            *[
                _template(f"num{i}", skill_id="skill.a", type_="numeric")
                for i in range(5)
            ],
        ]
    }
    rng = random.Random(42)
    section = _section(item_types={"mcq4": 8, "numeric": 2})
    tasks = assemble_mock("mock_set", section, templates, {}, rng, PARAMS)
    assert PARAMS.mock_set_min <= len(tasks) <= PARAMS.mock_set_max
    # хотя бы один numeric (20% от 8-12 = 2)
    types = {t.type for _, t in tasks}
    assert "numeric" in types


# --- mock_misconception ---


def test_mock_misconception_only_traps():
    templates = {
        "skill.a": [
            _template(
                "trap",
                distractors=[DistractorSpec(expr="2", misconception_id="lib.x")],
            ),
            _template(
                "plain", distractors=[DistractorSpec(expr="2", misconception_id=None)]
            ),
        ],
        "skill.b": [
            _template(
                "trap2",
                skill_id="skill.b",
                distractors=[DistractorSpec(expr="2", misconception_id="lib.x")],
            ),
        ],
    }
    rng = random.Random(1)
    tasks = assemble_mock("mock_misconception", _section(), templates, {}, rng, PARAMS)
    for _, t in tasks:
        assert any(d.misconception_id for d in t.distractors)


# --- score ---


def test_score_simple_mcq():
    section = _section(rule="mcq4: 1 per correct")
    grades = [
        Grade(correct=True),
        Grade(correct=True),
        Grade(correct=False),
        Grade(correct=True),
    ]
    raw, scaled = score(section, grades, _exam_format())
    assert raw == pytest.approx(3.0)
    assert scaled is None  # без scale_table


def test_score_multi_select_partial():
    section = _section(rule="mcq5: 1 per correct; multi_select partial 2/1")
    grades = [
        Grade(correct=True),  # 1
        Grade(correct=False, partial=0.5),  # 1
        Grade(correct=False, partial=0.0),  # 0
    ]
    raw, _ = score(section, grades, _exam_format())
    assert raw == pytest.approx(2.0)


def test_score_scaled_with_table():
    fmt = _exam_format(scale_table={"10": 500, "20": 600, "30": 700})
    section = _section(rule="mcq4: 1 per correct")
    grades = [Grade(correct=True)] * 20
    raw, scaled = score(section, grades, fmt)
    assert raw == pytest.approx(20.0)
    assert scaled == pytest.approx(600.0)


# --- helper ---


def _exam_format(scale_table: dict | None = None):
    from app.schemas.knowledge import ExamFormat

    return ExamFormat(
        exam_id="SAT_MATH",
        name="SAT Math",
        max_raw_score=44,
        sections=[_section()],
        scale_table=scale_table,
        scale_note=None,
        source="https://...",
        checked_at=__import__("datetime").date(2026, 9, 18),
        is_demo=True,
    )
