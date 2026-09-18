"""p_target по экзамену — 00-contracts-phase2.md §2, memory-architecture §4.4."""

from __future__ import annotations

import pytest

from app.apply.targets import p_target_from, raw_from_scaled
from app.config import KnowledgeParams
from app.schemas.knowledge import ExamFormat

pytestmark = pytest.mark.phase1

PARAMS = KnowledgeParams()


def _format(*, max_raw: float = 58.0, scale: dict | None = None) -> ExamFormat:
    return ExamFormat(
        exam_id="SAT_MATH",
        name="SAT Math",
        max_raw_score=max_raw,
        sections=[],
        scale_table=scale,
        scale_note=None,
        source="demo",
        checked_at="2026-09-01",  # type: ignore[arg-type]
        is_demo=True,
    )


def test_raw_target_is_a_share_of_the_maximum():
    assert p_target_from(29.0, _format(), PARAMS) == pytest.approx(0.5)


def test_scaled_target_is_converted_through_the_scale_table():
    """Порог программы назван в шкале (SAT 700), максимум — в сырых баллах:
    без обратного перевода доля всегда > 1 и цель ни на что не влияла."""
    exam_format = _format(scale=({"0": 200, "29": 500, "58": 800}))
    assert p_target_from(650.0, exam_format, PARAMS) == pytest.approx(0.75, abs=0.01)


def test_target_never_exceeds_p_target_max():
    assert p_target_from(1000.0, _format(), PARAMS) == PARAMS.p_target_max
    assert p_target_from(58.0, _format(), PARAMS) == PARAMS.p_target_max


def test_without_exam_format_falls_back_to_the_ceiling():
    assert p_target_from(700.0, None, PARAMS) == PARAMS.p_target_max
    assert p_target_from(700.0, _format(max_raw=0.0), PARAMS) == PARAMS.p_target_max


def test_raw_from_scaled_is_the_inverse_of_the_forecast_scale():
    from app.sets.forecast import _scale

    exam_format = _format(scale={"0": 200, "29": 500, "58": 800})
    for raw in (5.0, 29.0, 44.0):
        assert raw_from_scaled(_scale(raw, exam_format), exam_format) == pytest.approx(
            raw, abs=0.01
        )
