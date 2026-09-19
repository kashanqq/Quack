"""Forecast readiness — memory-architecture-quack.md §4.7.

Pure function: predicted_raw, coverage, scaled estimate, ready_by, on_track.
Source: 20-B1-phase2.md §3.3, 00-contracts-phase2.md §7.1.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

from app.config import KnowledgeParams
from app.schemas.knowledge import (
    ExamFormat,
    ForecastOut,
    KnowledgeStateOut,
    SkillWeight,
)

_PRIOR_P_RECALL = 0.5
_DAYS_PER_WEEK = 7


def forecast(
    states: list[KnowledgeStateOut],
    skill_weights: list[SkillWeight],
    exam_format: ExamFormat,
    p_target: float,
    hours_per_week: int,
    test_date: date | None,
    effort: dict[str, float],
    params: KnowledgeParams,
    now: date,
) -> ForecastOut:
    """Build a ForecastOut from states and skill weights.

    - predicted_raw = Σ weight·p_recall по conf ≥ c_vis, остальные — приор
    - coverage     = Σ weight·[conf ≥ c_vis] / Σ weight
    - predicted_scaled по ScaleTable (интерполяция; SAT — оценочно)
    - hours_needed = Σ gap·effort_h
    - ready_by     = now + hours_needed / hours_per_week недель
    - on_track     = ready_by ≤ test_date (None без даты)
    - note         = «по модели знаний» / «по твоей оценке»
    """
    state_by_skill: dict[str, KnowledgeStateOut] = {}
    for s in states:
        state_by_skill.setdefault(s.skill_id, s)

    total_weight = 0.0
    covered_weight = 0.0
    predicted_raw = 0.0
    hours_needed = 0.0

    for sw in skill_weights:
        sid = sw.skill.id
        total_weight += sw.weight

        state = state_by_skill.get(sid)
        covered = state is not None and state.confidence >= params.c_vis

        if covered:
            p = state.p_recall  # type: ignore[union-attr]
            covered_weight += sw.weight
        else:
            p = _PRIOR_P_RECALL

        predicted_raw += sw.weight * p

        # hours: gap·effort_h
        gap = max(0.0, p_target - p)
        eff = effort.get(sid, sw.skill.effort_h)
        hours_needed += gap * eff

    coverage = covered_weight / total_weight if total_weight > 0 else 0.0

    predicted_scaled = _scale(predicted_raw, exam_format)
    note = _note(coverage, params, exam_format)

    if hours_per_week > 0:
        weeks = hours_needed / hours_per_week
        ready_by = now + timedelta(days=math.ceil(weeks * _DAYS_PER_WEEK))
    else:
        ready_by = None

    on_track: bool | None
    if test_date is None or ready_by is None:
        on_track = None
    else:
        on_track = ready_by <= test_date

    return ForecastOut(
        exam_id=exam_format.exam_id,
        predicted_raw=predicted_raw,
        predicted_scaled=predicted_scaled,
        coverage=coverage,
        hours_needed=hours_needed,
        ready_by=ready_by,
        test_date=test_date,
        on_track=on_track,
        as_of_event_id=0,
        note=note,
    )


def _scale(raw: float, exam_format: ExamFormat) -> float | None:
    """Linear interpolation between ScaleTable points. None if no table."""
    table = exam_format.scale_table
    if not table:
        return None
    # scale_table: {"30": 480, "35": 530, ...}
    points: list[tuple[float, float]] = []
    for k, v in table.items():
        try:
            points.append((float(k), float(v)))
        except (ValueError, TypeError):
            continue
    if not points:
        return None
    points.sort()

    if raw <= points[0][0]:
        return points[0][1]
    if raw >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        if x0 <= raw <= x1:
            if x1 == x0:
                return y0
            t = (raw - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return None


def _note(coverage: float, params: KnowledgeParams, exam_format: ExamFormat) -> str:
    base = "по модели знаний" if coverage >= params.c_cov else "по твоей оценке"
    if exam_format.scale_note:
        base += f" · {exam_format.scale_note}"
    return base
