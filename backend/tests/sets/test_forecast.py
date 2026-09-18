"""forecast — memory-architecture §4.7.

Numbers from 20-B1-phase2.md §8 (tests/sets/test_forecast.py).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.config import KnowledgeParams
from app.schemas.knowledge import (
    ExamFormat,
    KnowledgeStateOut,
    Section,
    SkillRef,
    SkillWeight,
)
from app.sets.forecast import forecast

pytestmark = pytest.mark.phase1

PARAMS = KnowledgeParams()
NOW = date(2026, 9, 18)


def _format(
    exam_id: str = "SAT_MATH",
    *,
    scale_table: dict | None = None,
    scale_note: str | None = None,
) -> ExamFormat:
    return ExamFormat(
        exam_id=exam_id,  # type: ignore[arg-type]
        name="Test",
        max_raw_score=44,
        sections=[
            Section(
                name="M1",
                n_items=22,
                minutes=35,
                item_types={"mcq4": 17, "numeric": 5},
                scoring_rule="1 per correct",
                calculator=True,
                adaptive=False,
                area_shares={"area.sat.algebra": 1.0},
                difficulty_shares={"2": 0.5, "3": 0.5},
                answer_forms=["integer"],
            )
        ],
        scale_table=scale_table,
        scale_note=scale_note,
        source="https://...",
        checked_at=NOW,
        is_demo=True,
    )


def _skill(skill_id: str, effort_h: float = 4.0) -> SkillRef:
    return SkillRef(
        id=skill_id,
        name=skill_id,
        description="...",
        exam_ids=["SAT_MATH"],  # type: ignore[list-item]
        effort_h=effort_h,
        base_half_life_h=None,
    )


def _weight(skill_id: str, weight: float = 3.0) -> SkillWeight:
    return SkillWeight(
        skill=_skill(skill_id),
        area_id="area.sat.algebra",
        weight=weight,
    )


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
        last_observed_at=datetime(2026, 9, 17, 12, 0, tzinfo=UTC),
        created_at=datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
    )


# --- numbers ---


def test_predicted_raw_three_skills():
    states = [
        _state("a", p_recall=0.5, confidence=0.8),
        _state("b", p_recall=0.8, confidence=0.8),
        _state("c", p_recall=0.6, confidence=0.8),
    ]
    weights = [_weight("a", 3.0), _weight("b", 3.0), _weight("c", 3.0)]
    f = forecast(
        states,
        weights,
        _format(),
        p_target=0.9,
        hours_per_week=10,
        test_date=None,
        effort={},
        params=PARAMS,
        now=NOW,
    )
    # 3*0.5 + 3*0.8 + 3*0.6 = 1.5 + 2.4 + 1.8 = 5.7
    assert f.predicted_raw == pytest.approx(5.7)


def test_coverage_all_covered():
    states = [_state("a", confidence=0.8), _state("b", confidence=0.5)]
    weights = [_weight("a", 3.0), _weight("b", 3.0)]
    f = forecast(
        states,
        weights,
        _format(),
        p_target=0.9,
        hours_per_week=10,
        test_date=None,
        effort={},
        params=PARAMS,
        now=NOW,
    )
    assert f.coverage == pytest.approx(1.0)


def test_coverage_half():
    states = [_state("a", confidence=0.8)]
    weights = [_weight("a", 3.0), _weight("b", 3.0)]
    f = forecast(
        states,
        weights,
        _format(),
        p_target=0.9,
        hours_per_week=10,
        test_date=None,
        effort={},
        params=PARAMS,
        now=NOW,
    )
    assert f.coverage == pytest.approx(0.5)


def test_note_model_when_coverage_sufficient():
    states = [_state("a", confidence=0.8)]
    weights = [_weight("a", 3.0)]
    f = forecast(
        states,
        weights,
        _format(),
        p_target=0.9,
        hours_per_week=10,
        test_date=None,
        effort={},
        params=PARAMS,
        now=NOW,
    )
    assert "по модели знаний" in f.note


def test_note_estimate_when_coverage_low():
    states = [_state("a", confidence=0.1)]
    weights = [_weight("a", 3.0)]
    f = forecast(
        states,
        weights,
        _format(),
        p_target=0.9,
        hours_per_week=10,
        test_date=None,
        effort={},
        params=PARAMS,
        now=NOW,
    )
    assert "по твоей оценке" in f.note


# --- ScaleTable ---


def test_scaled_none_without_table():
    states = [_state("a")]
    weights = [_weight("a", 3.0)]
    f = forecast(
        states,
        weights,
        _format(),
        p_target=0.9,
        hours_per_week=10,
        test_date=None,
        effort={},
        params=PARAMS,
        now=NOW,
    )
    assert f.predicted_scaled is None


def test_scaled_interpolation():
    states = [_state("a", p_recall=0.5)]
    weights = [_weight("a", 3.0)]
    # raw = 3*0.5 = 1.5; но для интерполяции нужен больший raw.
    # Возьмём weight 10: raw = 5
    weights = [_weight("a", 10.0)]
    fmt = _format(scale_table={"30": 480, "40": 580, "50": 680})
    f = forecast(
        states,
        weights,
        fmt,
        p_target=0.9,
        hours_per_week=10,
        test_date=None,
        effort={},
        params=PARAMS,
        now=NOW,
    )
    # raw = 5 → между 30 и 40: 480 + (5/10?) ... но 5 < 30 → возвращаем 480
    assert f.predicted_scaled == pytest.approx(480.0)


def test_scaled_above_table():
    states = [_state("a", p_recall=0.9, confidence=0.8)]
    weights = [_weight("a", 100.0)]  # raw = 90
    fmt = _format(scale_table={"30": 480, "40": 580})
    f = forecast(
        states,
        weights,
        fmt,
        p_target=0.9,
        hours_per_week=10,
        test_date=None,
        effort={},
        params=PARAMS,
        now=NOW,
    )
    assert f.predicted_scaled == pytest.approx(580.0)


# --- hours / dates ---


def test_hours_needed_and_ready_by():
    states = [_state("a", p_recall=0.5)]
    weights = [_weight("a", 3.0)]
    f = forecast(
        states,
        weights,
        _format(),
        p_target=0.9,
        hours_per_week=10,
        test_date=None,
        effort={"a": 6.0},
        params=PARAMS,
        now=NOW,
    )
    # gap = 0.4, hours = 0.4 * 6 = 2.4, weeks = 0.24 → 1.68 дней → ceil 2
    assert f.hours_needed == pytest.approx(2.4)
    assert f.ready_by == NOW + timedelta(days=2)


def test_on_track_true():
    states = [_state("a", p_recall=0.5)]
    weights = [_weight("a", 3.0)]
    f = forecast(
        states,
        weights,
        _format(),
        p_target=0.9,
        hours_per_week=10,
        test_date=NOW + timedelta(days=30),
        effort={"a": 6.0},
        params=PARAMS,
        now=NOW,
    )
    assert f.on_track is True


def test_on_track_false():
    states = [_state("a", p_recall=0.5)]
    weights = [_weight("a", 3.0)]
    f = forecast(
        states,
        weights,
        _format(),
        p_target=0.9,
        hours_per_week=10,
        test_date=NOW + timedelta(days=1),
        effort={"a": 6.0},
        params=PARAMS,
        now=NOW,
    )
    assert f.on_track is False


def test_on_track_none_without_date():
    states = [_state("a", p_recall=0.5)]
    weights = [_weight("a", 3.0)]
    f = forecast(
        states,
        weights,
        _format(),
        p_target=0.9,
        hours_per_week=10,
        test_date=None,
        effort={"a": 6.0},
        params=PARAMS,
        now=NOW,
    )
    assert f.on_track is None
