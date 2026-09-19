"""hard_filter — product-logic §3.3, 20-B1-phase2.md §5.1."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.config import KnowledgeParams
from app.matching.hard import explain_empty, hard_filter
from app.schemas.knowledge import ForecastOut
from app.schemas.profile import (
    Academics,
    Constraints,
    Direction,
    Preferences,
    Profile,
    ProfileField,
    Questionnaire,
)
from app.schemas.programs import Deadline, Program, Requirement

pytestmark = pytest.mark.phase1

PARAMS = KnowledgeParams()
TODAY = date(2026, 9, 18)


def _req(
    type_: str,
    *,
    exam_id: str | None = None,
    threshold: float | None = None,
    comparator: str = ">=",
) -> Requirement:
    return Requirement(
        type=type_,  # type: ignore[arg-type]
        exam_id=exam_id,  # type: ignore[arg-type]
        threshold=threshold,
        comparator=comparator,  # type: ignore[arg-type]
        description="...",
        source=None,
    )


def _program(
    program_id: str = "p1",
    *,
    country: str = "US",
    city: str = "Boston",
    direction: str = "CS",
    language: str = "English",
    tuition: int | None = 40000,
    living: int | None = 15000,
    currency: str = "USD",
    requirements: list[Requirement] | None = None,
    deadlines: list[Deadline] | None = None,
    scholarships_note: str | None = None,
) -> Program:
    return Program(
        id=program_id,
        university="MIT",
        country=country,
        city=city,
        direction=direction,
        language=language,
        duration_months=48,
        tuition_per_year=tuition,
        living_per_year=living,
        currency=currency,
        requirements=requirements or [],
        deadlines=deadlines or [],
        scholarships_note=scholarships_note,
        environment_text=None,
        source_url="https://example.com",
        checked_at=TODAY,
        is_demo=True,
        extracted_auto=False,
        flagged=False,
    )


def _profile(
    *,
    sat_score: int | None = None,
    ielts: float | None = None,
    budget: int | None = None,
    currency: str | None = None,
    grant_need: str | None = None,
    countries: list[str] | None = None,
    cities: list[str] | None = None,
    language: str | None = None,
    direction: str | None = None,
    sat_date: date | None = None,
    excluded: list[str] | None = None,
    required: list[str] | None = None,
) -> Profile:
    from uuid import uuid4

    def f(value):
        if value is None:
            return ProfileField(value=None)
        return ProfileField(value=value, mark="stated")

    return Profile(
        student_id=uuid4(),
        questionnaire=Questionnaire(
            direction=Direction(field=f(direction), alternatives=f(None)),
            academics=Academics(
                sat_score=f(sat_score),
                sat_date=f(sat_date),
                ielts_score=f(ielts),
            ),
            preferences=Preferences(
                countries=f(countries),
                cities=f(cities),
                language=f(language),
                budget_per_year=f(budget),
                currency=f(currency),
                grant_need=f(grant_need),
            ),
            constraints=Constraints(
                required=f(required),
                excluded=f(excluded),
            ),
        ),
    )


def _forecast_raw(
    exam_id: str, *, predicted_scaled: float, coverage: float
) -> ForecastOut:
    return ForecastOut(
        exam_id=exam_id,  # type: ignore[arg-type]
        predicted_raw=10.0,
        predicted_scaled=predicted_scaled,
        coverage=coverage,
        hours_needed=0.0,
        ready_by=None,
        test_date=None,
        on_track=None,
        as_of_event_id=1,
        note="test",
    )


# --- exam_score ---


def test_exam_score_above():
    p = _profile(sat_score=1600)
    prog = _program(
        requirements=[_req("exam_score", exam_id="SAT_MATH", threshold=1200)]
    )
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "exam_score:SAT_MATH")
    assert f.status == "above"


def test_exam_score_in_range():
    p = _profile(sat_score=1200)
    prog = _program(
        requirements=[_req("exam_score", exam_id="SAT_MATH", threshold=1200)]
    )
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "exam_score:SAT_MATH")
    assert f.status == "in_range"


def test_exam_score_below():
    p = _profile(sat_score=1000)
    prog = _program(
        requirements=[_req("exam_score", exam_id="SAT_MATH", threshold=1300)]
    )
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "exam_score:SAT_MATH")
    assert f.status == "below"


def test_exam_score_unknown_without_data():
    p = _profile()  # без sat_score
    prog = _program(
        requirements=[_req("exam_score", exam_id="SAT_MATH", threshold=1200)]
    )
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "exam_score:SAT_MATH")
    assert f.status == "unknown"


def test_exam_score_uses_forecast_when_coverage_high():
    p = _profile(sat_score=1000)  # самооценка ниже порога
    forecast = _forecast_raw("SAT_MATH", predicted_scaled=1350, coverage=0.8)
    prog = _program(
        requirements=[_req("exam_score", exam_id="SAT_MATH", threshold=1300)]
    )
    results = hard_filter(p, [prog], {"SAT_MATH": forecast}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "exam_score:SAT_MATH")
    # прогноз выше порога → in_range / above, а не below
    assert f.status in ("in_range", "above")
    assert "по модели знаний" in f.text


def test_exam_score_falls_back_to_self_with_low_coverage():
    p = _profile(sat_score=1000)
    forecast = _forecast_raw("SAT_MATH", predicted_scaled=1350, coverage=0.3)
    prog = _program(
        requirements=[_req("exam_score", exam_id="SAT_MATH", threshold=1300)]
    )
    results = hard_filter(p, [prog], {"SAT_MATH": forecast}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "exam_score:SAT_MATH")
    assert f.status == "below"
    assert "по твоей оценке" in f.text


# --- language ---


def test_language_above():
    p = _profile(ielts=7.5)
    prog = _program(requirements=[_req("language", threshold=6.5)])
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "language")
    assert f.status == "above"


def test_language_unknown_without_ielts():
    p = _profile()
    prog = _program(requirements=[_req("language", threshold=6.5)])
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "language")
    assert f.status == "unknown"


# --- budget ---


def test_budget_in_range():
    p = _profile(budget=60000, currency="USD")
    prog = _program(tuition=40000, living=15000, currency="USD")
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "budget")
    assert f.status in ("in_range", "above")


def test_budget_below():
    p = _profile(budget=30000, currency="USD")
    prog = _program(tuition=40000, living=15000, currency="USD")
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "budget")
    assert f.status == "below"


def test_budget_unknown_when_currency_mismatch():
    p = _profile(budget=30000, currency="KZT")
    prog = _program(tuition=40000, living=15000, currency="USD")
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "budget")
    assert f.status == "unknown"
    assert results[0].assumptions


def test_budget_grant_only_without_scholarship_is_below():
    p = _profile(budget=60000, currency="USD", grant_need="only_grant")
    prog = _program(tuition=40000, living=15000, currency="USD", scholarships_note=None)
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "budget")
    assert f.status == "below"


# --- preferences ---


def test_country_not_in_preference():
    p = _profile(countries=["KZ"])
    prog = _program(country="US")
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "country")
    assert f.status == "below"


def test_direction_mismatch():
    p = _profile(direction="Medicine")
    prog = _program(direction="CS")
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    f = next(x for x in results[0].factors if x.id == "direction")
    assert f.status == "below"


# --- deadline ---


def test_deadline_exam_after_application_is_below():
    p = _profile(sat_date=TODAY + timedelta(days=60))
    prog = _program(
        deadlines=[
            Deadline(
                kind="application",
                date=TODAY + timedelta(days=30),
                round=None,
                source="https://example.com",
                checked_at=TODAY,
                is_demo=True,
            )
        ]
    )
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    dl = next((x for x in results[0].factors if x.id.startswith("deadline:")), None)
    assert dl is not None
    assert dl.status == "below"


def test_deadline_exam_before_application_is_ok():
    p = _profile(sat_date=TODAY + timedelta(days=15))
    prog = _program(
        deadlines=[
            Deadline(
                kind="application",
                date=TODAY + timedelta(days=30),
                round=None,
                source="https://example.com",
                checked_at=TODAY,
                is_demo=True,
            )
        ]
    )
    results = hard_filter(p, [prog], {}, {}, TODAY, PARAMS)
    dl = next((x for x in results[0].factors if x.id.startswith("deadline:")), None)
    assert dl is not None
    assert dl.status == "in_range"


# --- explain_empty ---


def test_explain_empty_when_all_country_below():
    p = _profile(countries=["KZ"])
    programs = [_program("p1", country="US"), _program("p2", country="DE")]
    results = hard_filter(p, programs, {}, {}, TODAY, PARAMS)
    text = explain_empty(results)
    assert "country" in text


def test_explain_empty_when_no_programs():
    assert "нет программ" in explain_empty([])
