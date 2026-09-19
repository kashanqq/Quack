"""The four pace variants — §13.1 `test_pace.py`."""

from datetime import date

import pytest

from app.config import KnowledgeParams
from app.schemas.quack import ExamPaceOut
from app.sets.pace import PaceInputs, base_forecast, variants, words
from tests.quack.conftest import (
    TODAY,
    make_exam_format,
    make_program,
    make_skill_weight,
    make_state,
    make_test_dates,
)

pytestmark = pytest.mark.phase4

PARAMS = KnowledgeParams()
_SKILLS = ("s1", "s2", "s3", "s4", "s5")


def _late_date():
    from app.schemas.knowledge import TestDate

    return TestDate(
        exam_id="SAT_MATH",
        date=date(2027, 3, 13),
        registration_deadline=date(2027, 2, 13),
        source="collegeboard",
        checked_at=TODAY,
        is_demo=False,
    )


def _inputs(**overrides) -> PaceInputs:
    base = {
        "exam_id": "SAT_MATH",
        "states": [make_state(skill, 0.5) for skill in _SKILLS],
        "skill_weights": [make_skill_weight(skill, effort_h=30.0) for skill in _SKILLS],
        "exam_format": make_exam_format(),
        # 5 навыков × разрыв 0.4 × 30 ч = 60 ч: при 4 ч/нед это 15 недель,
        # то есть заведомо позже теста — ровно сценарий product-logic §3.6.
        "effort": {skill: 30.0 for skill in _SKILLS},
        "p_target": 0.9,
        "hours_per_week": 4,
        "test_date": date(2026, 11, 7),
        "calendar": [*make_test_dates(), _late_date()],
        "saved": [make_program(1, threshold=1450), make_program(2, threshold=1300)],
        "target_score": 1450,
        "max_raw_score": 44.0,
    }
    return PaceInputs(**{**base, **overrides})


def _by_kind(items):
    return {item.kind: item for item in items}


def test_base_forecast_is_late_and_all_four_variants_are_returned():
    inputs = _inputs()
    base = base_forecast(inputs, PARAMS, TODAY)
    assert base is not None
    assert base.on_track is False
    result = variants(base, inputs, PARAMS, TODAY)
    assert [item.kind for item in result] == [
        "more_hours",
        "move_date",
        "remove_program",
        "lower_target",
    ]
    # Прогноз обязателен даже у недоступного варианта (§14.7).
    assert all(item.forecast is not None for item in result)


def test_more_hours_finds_the_smallest_sufficient_pace():
    inputs = _inputs()
    base = base_forecast(inputs, PARAMS, TODAY)
    variant = _by_kind(variants(base, inputs, PARAMS, TODAY))["more_hours"]
    assert variant.available is True
    hours = variant.params["hours_per_week"]
    assert hours > inputs.hours_per_week
    assert variant.forecast.on_track is True
    # Минимальность: на шаг меньше уже не успевает.
    smaller = base_forecast(
        _inputs(hours_per_week=hours - PARAMS.pace_hours_step), PARAMS, TODAY
    )
    assert smaller.ready_by > inputs.test_date


def test_more_hours_stops_at_the_ceiling():
    params = KnowledgeParams(pace_max_hours=5)
    inputs = _inputs(hours_per_week=4, test_date=date(2026, 9, 25))
    base = base_forecast(inputs, params, TODAY)
    variant = _by_kind(variants(base, inputs, params, TODAY))["more_hours"]
    assert variant.available is False
    assert variant.unavailable_reason == "exceeds_max_hours"


def test_move_date_picks_the_first_date_after_readiness():
    inputs = _inputs()
    base = base_forecast(inputs, PARAMS, TODAY)
    variant = _by_kind(variants(base, inputs, PARAMS, TODAY))["move_date"]
    assert variant.available is True
    chosen = date.fromisoformat(variant.params["test_date"])
    assert chosen > base.ready_by
    assert date.fromisoformat(variant.params["registration_deadline"]) >= TODAY


def test_move_date_unavailable_without_later_dates():
    inputs = _inputs(calendar=make_test_dates()[:1])
    base = base_forecast(inputs, PARAMS, TODAY)
    variant = _by_kind(variants(base, inputs, PARAMS, TODAY))["move_date"]
    assert variant.available is False
    assert variant.unavailable_reason == "no_later_dates"


def test_remove_program_targets_the_highest_threshold():
    inputs = _inputs()
    base = base_forecast(inputs, PARAMS, TODAY)
    variant = _by_kind(variants(base, inputs, PARAMS, TODAY))["remove_program"]
    assert variant.params["program_id"] == "program-1"
    assert variant.params["new_target"] == 1300
    assert variant.affected_program_ids == ["program-1"]


def test_remove_program_unavailable_with_a_single_program():
    inputs = _inputs(saved=[make_program(1, threshold=1450)])
    base = base_forecast(inputs, PARAMS, TODAY)
    variant = _by_kind(variants(base, inputs, PARAMS, TODAY))["remove_program"]
    assert variant.available is False
    assert variant.unavailable_reason == "only_program"


def test_lower_target_respects_the_step_and_the_floor():
    inputs = _inputs()
    base = base_forecast(inputs, PARAMS, TODAY)
    variant = _by_kind(variants(base, inputs, PARAMS, TODAY))["lower_target"]
    if variant.available:
        value = variant.params["target_score"]
        assert value >= PARAMS.pace_min_target_share * inputs.target_score
        assert (inputs.target_score - value) % PARAMS.pace_target_step_sat == 0
        # Программы с порогом выше новой цели названы прямо.
        assert "program-1" in variant.affected_program_ids
    else:
        assert variant.unavailable_reason == "floor_reached"


def test_lower_target_needs_a_target():
    inputs = _inputs(target_score=None)
    base = base_forecast(inputs, PARAMS, TODAY)
    variant = _by_kind(variants(base, inputs, PARAMS, TODAY))["lower_target"]
    assert variant.available is False
    assert variant.unavailable_reason == "no_target"


def test_variants_are_deterministic():
    inputs = _inputs()
    base = base_forecast(inputs, PARAMS, TODAY)
    first = variants(base, inputs, PARAMS, TODAY)
    second = variants(base, inputs, PARAMS, TODAY)
    assert [item.model_dump() for item in first] == [
        item.model_dump() for item in second
    ]


def test_words_say_plainly_whether_the_student_is_in_time():
    inputs = _inputs()
    base = base_forecast(inputs, PARAMS, TODAY)
    pace = ExamPaceOut(
        exam_id="SAT_MATH",
        forecast=base,
        on_track=False,
        test_date=inputs.test_date,
        hours_declared=4,
    )
    text = words(pace)
    assert "SAT" in text and "4 ч/нед" in text and "не успеваешь" in text
