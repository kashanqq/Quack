"""Four ways out when the forecast says «не успеваешь» — §8.3.

Pure arithmetic: every variant is the phase-2 forecast re-run with one input
changed, so the number the student sees next to a variant is the same number
the system would produce after they accept it. No model, no I/O.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.config import KnowledgeParams
from app.roadmap.milestones import exam_label, format_date_ru
from app.schemas.common import ExamId
from app.schemas.knowledge import (
    ExamFormat,
    ForecastOut,
    KnowledgeStateOut,
    SkillWeight,
    TestDate,
)
from app.schemas.programs import Program
from app.schemas.quack import ExamPaceOut, PaceVariantOut
from app.sets.forecast import forecast as forecast_fn
from app.sets.scale import p_target_from

_MAX_HOUR_STEPS = 20
_MAX_TARGET_STEPS = 40


class PaceInputs(BaseModel):
    """Everything the four variants need, already read from graph and DB."""

    model_config = {"arbitrary_types_allowed": True}

    exam_id: ExamId
    states: list[KnowledgeStateOut] = Field(default_factory=list)
    skill_weights: list[SkillWeight] = Field(default_factory=list)
    exam_format: ExamFormat | None = None
    effort: dict[str, float] = Field(default_factory=dict)
    p_target: float = 0.9
    hours_per_week: int = 0
    test_date: date | None = None
    calendar: list[TestDate] = Field(default_factory=list)
    saved: list[Program] = Field(default_factory=list)
    target_score: float | None = None
    max_raw_score: float | None = None


def target_step(exam_id: ExamId, params: KnowledgeParams) -> int:
    return (
        params.pace_target_step_sat
        if exam_id == "SAT_MATH"
        else params.pace_target_step_ent
    )


def base_forecast(
    inputs: PaceInputs, params: KnowledgeParams, today: date
) -> ForecastOut | None:
    """The forecast as it stands — the baseline every variant is measured от."""
    return _forecast(inputs, params, today)


def variants(
    base: ForecastOut,
    inputs: PaceInputs,
    params: KnowledgeParams,
    today: date,
) -> list[PaceVariantOut]:
    """All four variants, always in the same order, available or not."""
    return [
        _more_hours(base, inputs, params, today),
        _move_date(base, inputs, params, today),
        _remove_program(base, inputs, params, today),
        _lower_target(base, inputs, params, today),
    ]


def words(exam_pace: ExamPaceOut) -> str:
    """One sentence for the pace block — «не успеваешь» told plainly."""
    label = exam_label(exam_pace.exam_id)
    forecast = exam_pace.forecast
    if forecast is None:
        return f"{label}: пока нечего прогнозировать — сохрани программу с порогом"
    hours = exam_pace.hours_declared or 0
    parts = [label]
    if hours:
        parts.append(f"при {hours} ч/нед")
    if forecast.ready_by is not None:
        parts.append(f"готовность {format_date_ru(forecast.ready_by)}")
    else:
        parts.append("готовность не посчитать — часы не указаны")
    if exam_pace.test_date is not None:
        parts.append(f"тест {format_date_ru(exam_pace.test_date)}")
    if exam_pace.on_track is True:
        parts.append("успеваешь")
    elif exam_pace.on_track is False:
        parts.append("не успеваешь")
    return f"{parts[0]}: " + ", ".join(parts[1:])


# --- internals ---


class _Unset:
    """Distinguishes «не передан» from «передан None» for `test_date`."""


_UNSET = _Unset()


def _forecast(
    inputs: PaceInputs,
    params: KnowledgeParams,
    today: date,
    *,
    hours_per_week: int | None = None,
    test_date: date | None | _Unset = _UNSET,
    p_target: float | None = None,
) -> ForecastOut | None:
    """The phase-2 forecast with exactly one input replaced."""
    if inputs.exam_format is None:
        return None
    return forecast_fn(
        states=inputs.states,
        skill_weights=inputs.skill_weights,
        exam_format=inputs.exam_format,
        p_target=inputs.p_target if p_target is None else p_target,
        hours_per_week=(
            inputs.hours_per_week if hours_per_week is None else hours_per_week
        ),
        test_date=inputs.test_date if isinstance(test_date, _Unset) else test_date,
        effort=inputs.effort,
        params=params,
        now=today,
    )


def _on_time(forecast: ForecastOut | None, test_date: date | None) -> bool:
    if forecast is None or forecast.ready_by is None or test_date is None:
        return False
    return forecast.ready_by <= test_date


def _more_hours(
    base: ForecastOut, inputs: PaceInputs, params: KnowledgeParams, today: date
) -> PaceVariantOut:
    hours0 = inputs.hours_per_week or 0
    found: tuple[int, ForecastOut] | None = None
    for step in range(1, _MAX_HOUR_STEPS + 1):
        hours = hours0 + step * params.pace_hours_step
        if hours > params.pace_max_hours:
            break
        candidate = _forecast(inputs, params, today, hours_per_week=hours)
        if _on_time(candidate, inputs.test_date):
            found = (hours, candidate)
            break
    if found is None:
        return PaceVariantOut(
            kind="more_hours",
            text=f"даже {params.pace_max_hours} ч/нед не хватает до теста",
            params={},
            forecast=base,
            available=False,
            unavailable_reason="exceeds_max_hours",
        )
    hours, candidate = found
    ready = format_date_ru(candidate.ready_by) if candidate.ready_by else "к сроку"
    return PaceVariantOut(
        kind="more_hours",
        text=f"{hours} ч/нед → готов {ready}",
        params={"hours_per_week": hours},
        forecast=candidate,
        available=True,
    )


def _move_date(
    base: ForecastOut, inputs: PaceInputs, params: KnowledgeParams, today: date
) -> PaceVariantOut:
    ready_by = base.ready_by
    later = sorted(
        (
            item
            for item in inputs.calendar
            if item.exam_id == inputs.exam_id
            and (ready_by is None or item.date > ready_by)
            and item.registration_deadline >= today
        ),
        key=lambda item: item.date,
    )
    if not later:
        return PaceVariantOut(
            kind="move_date",
            text="более поздних дат в календаре нет",
            params={},
            forecast=base,
            available=False,
            unavailable_reason="no_later_dates",
        )
    chosen = later[0]
    candidate = _forecast(inputs, params, today, test_date=chosen.date)
    return PaceVariantOut(
        kind="move_date",
        text=(
            f"перенести тест на {format_date_ru(chosen.date)} "
            f"(регистрация до {format_date_ru(chosen.registration_deadline)})"
        ),
        params={
            "test_date": chosen.date.isoformat(),
            "registration_deadline": chosen.registration_deadline.isoformat(),
        },
        forecast=candidate or base,
        available=True,
    )


def _thresholds(inputs: PaceInputs) -> list[tuple[float, Program, date | None]]:
    """(threshold, program, latest deadline) for the saved programs that
    actually demand this exam."""
    out: list[tuple[float, Program, date | None]] = []
    for program in inputs.saved:
        best: float | None = None
        for requirement in program.requirements:
            if (
                requirement.type == "exam_score"
                and requirement.exam_id == inputs.exam_id
                and requirement.threshold is not None
            ):
                best = max(best or 0.0, requirement.threshold)
        if best is None:
            continue
        latest = max((item.date for item in program.deadlines), default=None)
        out.append((best, program, latest))
    return out


def _remove_program(
    base: ForecastOut, inputs: PaceInputs, params: KnowledgeParams, today: date
) -> PaceVariantOut:
    thresholds = _thresholds(inputs)
    if len(thresholds) < 2:
        return PaceVariantOut(
            kind="remove_program",
            text="убирать нечего — это единственная программа с порогом",
            params={},
            forecast=base,
            available=False,
            unavailable_reason="only_program",
        )
    # Самый высокий порог; при равенстве — программа с более поздним дедлайном.
    hardest = max(
        thresholds,
        key=lambda item: (item[0], item[2] or date.min),
    )
    remaining = [item[0] for item in thresholds if item[1].id != hardest[1].id]
    new_target = max(remaining)
    p_target = p_target_from(new_target, inputs.exam_format, params)
    candidate = _forecast(inputs, params, today, p_target=p_target)
    available = _on_time(candidate, inputs.test_date)
    ready = (
        format_date_ru(candidate.ready_by)
        if candidate is not None and candidate.ready_by
        else "к сроку"
    )
    return PaceVariantOut(
        kind="remove_program",
        text=(
            f"убрать {hardest[1].university} (порог {int(new_target)} "
            f"остаётся максимальным) → готов {ready}"
        ),
        params={"program_id": hardest[1].id, "new_target": new_target},
        forecast=candidate or base,
        available=available,
        unavailable_reason=None if available else "still_late",
        affected_program_ids=[hardest[1].id],
    )


def _lower_target(
    base: ForecastOut, inputs: PaceInputs, params: KnowledgeParams, today: date
) -> PaceVariantOut:
    target = inputs.target_score
    if target is None or target <= 0:
        return PaceVariantOut(
            kind="lower_target",
            text="цель по экзамену не задана",
            params={},
            forecast=base,
            available=False,
            unavailable_reason="no_target",
        )
    step = target_step(inputs.exam_id, params)
    floor = params.pace_min_target_share * target
    found: tuple[float, ForecastOut] | None = None
    for index in range(1, _MAX_TARGET_STEPS + 1):
        value = target - index * step
        if value < floor:
            break
        candidate = _forecast(
            inputs,
            params,
            today,
            p_target=p_target_from(value, inputs.exam_format, params),
        )
        if _on_time(candidate, inputs.test_date):
            found = (value, candidate)
            break
    if found is None:
        return PaceVariantOut(
            kind="lower_target",
            text=(
                f"снижение цели до {int(floor)} не помогает — ниже опускать не станем"
            ),
            params={},
            forecast=base,
            available=False,
            unavailable_reason="floor_reached",
        )
    value, candidate = found
    affected = [
        program.id for threshold, program, _ in _thresholds(inputs) if threshold > value
    ]
    ready = format_date_ru(candidate.ready_by) if candidate.ready_by else "к сроку"
    return PaceVariantOut(
        kind="lower_target",
        text=f"цель {int(value)} → готов {ready}",
        params={"target_score": value},
        forecast=candidate,
        available=True,
        affected_program_ids=affected,
    )
