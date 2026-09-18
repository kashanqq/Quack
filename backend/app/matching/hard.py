"""Hard factors — product-logic §3.3, memory-architecture §10.3.

Pure function: score each program's requirements against the profile and
return one HardResult per program with per-factor statuses.

Source: 20-B1-phase2.md §5.1, 00-contracts-phase2.md §7.1.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.config import KnowledgeParams
from app.schemas.common import ExamId, FactorStatus, Source
from app.schemas.knowledge import ForecastOut, TestDate
from app.schemas.matching import FactorOut
from app.schemas.profile import Profile
from app.schemas.programs import Program, Requirement

_IN_RANGE_TOLERANCE = 0.05  # ±5% от порога


class HardResult(BaseModel):
    """Result of hard_filter for one program — memory-architecture §10.3."""

    program_id: str
    realism_inputs: dict[str, FactorStatus]
    factors: list[FactorOut]
    assumptions: list[str]


# --- public ---


def hard_filter(
    profile: Profile,
    programs: list[Program],
    forecasts: dict[ExamId, ForecastOut],
    test_dates: dict[ExamId, list[TestDate]],
    today: date,
    params: KnowledgeParams,
) -> list[HardResult]:
    """Score each program on its requirements vs the profile."""
    return [
        _score_program(profile, p, forecasts, test_dates, today, params)
        for p in programs
    ]


def explain_empty(hard_results: list[HardResult]) -> str:
    """Which factor is `below` for every program and what loosening gives."""
    if not hard_results:
        return "нет программ в каталоге"

    # частота below-факторов
    counter: dict[str, int] = {}
    for r in hard_results:
        for f in r.factors:
            if f.status == "below":
                counter[f.id] = counter.get(f.id, 0) + 1

    total = len(hard_results)
    dominant = [fid for fid, cnt in counter.items() if cnt == total]
    if not dominant:
        return "пока ничего не подошло — попробуй ослабить бюджет или расширить страны"

    top = dominant[0]
    hint = _hint_for(top)
    return f"все программы отсекает: {top}. {hint}"


# --- scoring ---


def _score_program(
    profile: Profile,
    program: Program,
    forecasts: dict[ExamId, ForecastOut],
    test_dates: dict[ExamId, list[TestDate]],
    today: date,
    params: KnowledgeParams,
) -> HardResult:
    factors: list[FactorOut] = []
    assumptions: list[str] = []
    realism_inputs: dict[str, FactorStatus] = {}

    source = _source_from(program)

    # 1. Требования программы
    for req in program.requirements:
        factor = _requirement_factor(profile, req, forecasts, params, source)
        factors.append(factor)
        if req.type in ("exam_score", "language"):
            realism_inputs[factor.id] = factor.status

    # 2. Бюджет
    budget_factor, budget_status = _budget_factor(profile, program, source)
    factors.append(budget_factor)
    if budget_factor.id in ("budget", "grant"):
        realism_inputs[budget_factor.id] = budget_status
        if budget_status == "unknown":
            assumptions.append(
                "бюджет не указан или валюта не совпадает — считаем, что подходит"
            )

    # 3. Страна / город / язык / направление
    for f in _preference_factors(profile, program):
        factors.append(f)
        if f.status == "below":
            realism_inputs[f.id] = "below"

    # 4. Дедлайн против планируемой даты экзамена
    dl_factor = _deadline_factor(profile, program, test_dates, today)
    if dl_factor is not None:
        factors.append(dl_factor)
        if dl_factor.status == "below":
            realism_inputs[dl_factor.id] = "below"

    return HardResult(
        program_id=program.id,
        realism_inputs=realism_inputs,
        factors=factors,
        assumptions=assumptions,
    )


# --- factors ---


def _source_from(program: Program) -> Source:
    return Source(
        label=program.university,
        url=program.source_url,
        checked_at=program.checked_at,
        is_demo=program.is_demo,
    )


def _requirement_factor(
    profile: Profile,
    req: Requirement,
    forecasts: dict[ExamId, ForecastOut],
    params: KnowledgeParams,
    source: Source,
) -> FactorOut:
    if req.type == "exam_score" and req.exam_id is not None:
        return _exam_score_factor(profile, req, forecasts, params, source)
    if req.type == "language":
        return _language_factor(profile, req, source)
    if req.type in ("gpa", "document", "other"):
        # Не оцениваем глубоко — это отметка "present" обычно.
        return FactorOut(
            id=f"{req.type}",
            kind="hard",
            status="unknown",
            text=req.description,
            source=source,
            weight=0.5,
        )
    return FactorOut(
        id=req.type,
        kind="hard",
        status="unknown",
        text=req.description,
        source=source,
        weight=0.5,
    )


def _exam_score_factor(
    profile: Profile,
    req: Requirement,
    forecasts: dict[ExamId, ForecastOut],
    params: KnowledgeParams,
    source: Source,
) -> FactorOut:
    threshold = float(req.threshold or 0)
    exam_id = req.exam_id  # уже проверено что not None

    forecast = forecasts.get(exam_id)  # type: ignore[arg-type]
    if forecast is not None and forecast.coverage >= params.c_cov:
        score = forecast.predicted_scaled
        note = "по модели знаний"
        forecast_used = True
    else:
        # self-assessment
        acad = profile.questionnaire.academics
        if exam_id == "SAT_MATH":
            field = acad.sat_score
        else:
            field = acad.ent_trial_score
        score = float(field.value) if field.value is not None else None
        note = "по твоей оценке"
        forecast_used = False

    if score is None:
        return FactorOut(
            id=f"exam_score:{exam_id}",
            kind="hard",
            status="unknown",
            text=f"{exam_id} — нет балла",
            source=source,
            weight=1.0,
        )

    status = _compare_above(score, threshold)
    text = f"{exam_id}: {score:.0f} против порога {threshold:.0f} ({note})"
    _ = forecast_used
    return FactorOut(
        id=f"exam_score:{exam_id}",
        kind="hard",
        status=status,
        text=text,
        source=source,
        weight=1.0,
    )


def _language_factor(profile: Profile, req: Requirement, source: Source) -> FactorOut:
    threshold = float(req.threshold or 0)
    field = profile.questionnaire.academics.ielts_score
    if field.value is None:
        return FactorOut(
            id="language",
            kind="hard",
            status="unknown",
            text="IELTS — балл не указан",
            source=source,
            weight=0.8,
        )
    score = float(field.value)
    status = _compare_above(score, threshold)
    return FactorOut(
        id="language",
        kind="hard",
        status=status,
        text=f"IELTS: {score:.1f} против порога {threshold:.1f}",
        source=source,
        weight=0.8,
    )


def _budget_factor(
    profile: Profile, program: Program, source: Source
) -> tuple[FactorOut, FactorStatus]:
    prefs = profile.questionnaire.preferences

    tuition = program.tuition_per_year
    living = program.living_per_year
    if tuition is None and living is None:
        return (
            FactorOut(
                id="budget",
                kind="hard",
                status="unknown",
                text="стоимость программы неизвестна",
                source=source,
                weight=0.8,
            ),
            "unknown",
        )

    budget = prefs.budget_per_year.value
    budget_currency = (prefs.currency.value or "").upper()
    program_currency = program.currency.upper()

    if budget is None or not budget_currency or budget_currency != program_currency:
        return (
            FactorOut(
                id="budget",
                kind="hard",
                status="unknown",
                text=f"стоимость в {program_currency}, бюджет не указан в этой валюте",
                source=source,
                weight=0.8,
            ),
            "unknown",
        )

    total = (tuition or 0) + (living or 0)
    status = _compare_below(total, float(budget))

    grant_need = prefs.grant_need.value

    # нужен только грант — проверяем всегда, а не только при in_range
    if grant_need == "only_grant" and not program.scholarships_note:
        return (
            FactorOut(
                id="budget",
                kind="hard",
                status="below",
                text="нужен только грант, а у программы нет стипендии",
                source=source,
                weight=1.0,
            ),
            "below",
        )

    text = f"стоимость {total} {program_currency}/год против бюджета {budget}"
    return (
        FactorOut(
            id="budget",
            kind="hard",
            status=status,
            text=text,
            source=source,
            weight=1.0 if grant_need == "only_grant" else 0.8,
        ),
        status,
    )


def _preference_factors(profile: Profile, program: Program) -> list[FactorOut]:
    out: list[FactorOut] = []
    prefs = profile.questionnaire.preferences
    constraints = profile.questionnaire.constraints

    countries = prefs.countries.value or []
    if countries and program.country not in countries:
        out.append(
            FactorOut(
                id="country",
                kind="hard",
                status="below",
                text=f"{program.country} не в списке стран",
                source=None,
                weight=1.0,
            )
        )

    cities = prefs.cities.value or []
    if cities and program.city not in cities:
        out.append(
            FactorOut(
                id="city",
                kind="hard",
                status="below",
                text=f"{program.city} не в списке городов",
                source=None,
                weight=0.5,
            )
        )

    language = prefs.language.value
    if language and program.language.lower() != language.lower():
        out.append(
            FactorOut(
                id="language_pref",
                kind="hard",
                status="below",
                text=f"язык программы {program.language}, хотелось {language}",
                source=None,
                weight=0.5,
            )
        )

    direction = profile.questionnaire.direction.field.value
    if direction and direction.lower() not in program.direction.lower():
        out.append(
            FactorOut(
                id="direction",
                kind="hard",
                status="below",
                text=f"направление {program.direction} не совпадает",
                source=None,
                weight=0.8,
            )
        )

    excluded = constraints.excluded.value or []
    if program.country in excluded or program.id in excluded:
        out.append(
            FactorOut(
                id="excluded",
                kind="hard",
                status="below",
                text="программа явно исключена",
                source=None,
                weight=1.0,
            )
        )

    required = constraints.required.value or []
    if required and program.country not in required and program.id not in required:
        out.append(
            FactorOut(
                id="required",
                kind="hard",
                status="below",
                text="не входит в обязательный список",
                source=None,
                weight=1.0,
            )
        )

    return out


def _deadline_factor(
    profile: Profile,
    program: Program,
    test_dates: dict[ExamId, list[TestDate]],
    today: date,
) -> FactorOut | None:
    # ближайший application дедлайн
    apps = [d for d in program.deadlines if d.kind == "application"]
    if not apps:
        return None
    next_app = min(apps, key=lambda d: d.date)

    # планируемая дата экзамена
    acad = profile.questionnaire.academics
    exam_date: date | None = None
    if acad.sat_date.value is not None:
        exam_date = acad.sat_date.value
    else:
        for exam_id in ("SAT_MATH", "ENT_MATH"):
            candidates = [
                td.date for td in test_dates.get(exam_id, []) if td.date >= today
            ]
            if candidates:
                exam_date = min(candidates)
                break

    if exam_date is None:
        return None

    status: FactorStatus
    if exam_date > next_app.date:
        status = "below"
        text = f"экзамен {exam_date} позже дедлайна подачи {next_app.date}"
    else:
        status = "in_range"
        text = f"экзамен {exam_date} успевает к {next_app.date}"

    return FactorOut(
        id=f"deadline:{program.id}",
        kind="hard",
        status=status,
        text=text,
        source=Source(
            label="дедлайн программы",
            url=next_app.source,
            checked_at=next_app.checked_at,
            is_demo=next_app.is_demo,
        ),
        weight=0.8,
    )


# --- comparison helpers ---


def _compare_above(score: float, threshold: float) -> FactorStatus:
    if threshold <= 0:
        return "in_range"
    if score >= threshold:
        return "above" if score > threshold * (1 + _IN_RANGE_TOLERANCE) else "in_range"
    if score >= threshold * (1 - _IN_RANGE_TOLERANCE):
        return "in_range"
    return "below"


def _compare_below(cost: float, budget: float) -> FactorStatus:
    if budget <= 0:
        return "below"
    if cost <= budget:
        return "above" if cost < budget * (1 - _IN_RANGE_TOLERANCE) else "in_range"
    if cost <= budget * (1 + _IN_RANGE_TOLERANCE):
        return "in_range"
    return "below"


def _hint_for(factor_id: str) -> str:
    if factor_id.startswith("exam_score:"):
        return "ослабить цель по баллу или подтянуть подготовку"
    if factor_id == "language":
        return "подтянуть IELTS"
    if factor_id == "budget":
        return "расширить бюджет или поискать стипендии"
    if factor_id == "country":
        return "добавить страны в предпочтения"
    if factor_id == "direction":
        return "расширить направление"
    if factor_id.startswith("deadline:"):
        return "сдвинуть дату экзамена раньше"
    return "пересмотреть ограничения"
