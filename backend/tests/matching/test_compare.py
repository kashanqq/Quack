"""compare — 20-B1-phase2.md §5.4."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.matching.compare import compare
from app.matching.hard import HardResult
from app.schemas.matching import FactorOut
from app.schemas.profile import (
    Priorities,
    Profile,
    ProfileField,
    Questionnaire,
)
from app.schemas.programs import Program

pytestmark = pytest.mark.phase1


def _program(
    pid: str,
    *,
    tuition: int = 40000,
    living: int = 15000,
    currency: str = "USD",
    language: str = "English",
    duration: int = 48,
    environment: str | None = None,
    scholarships: str | None = None,
) -> Program:
    from datetime import date

    return Program(
        id=pid,
        university=f"Uni {pid}",
        country="US",
        city="Boston",
        direction="CS",
        language=language,
        duration_months=duration,
        tuition_per_year=tuition,
        living_per_year=living,
        currency=currency,
        requirements=[],
        deadlines=[],
        scholarships_note=scholarships,
        environment_text=environment,
        source_url="https://example.com",
        checked_at=date(2026, 9, 18),
        is_demo=True,
        extracted_auto=False,
        flagged=False,
    )


def _hard(pid: str, statuses: dict[str, str]) -> HardResult:
    factors = [
        FactorOut(
            id=fid,
            kind="hard",
            status=s,  # type: ignore[arg-type]
            text="...",
            source=None,
            weight=1.0,
        )
        for fid, s in statuses.items()
    ]
    return HardResult(
        program_id=pid,
        realism_inputs={},
        factors=factors,
        assumptions=[],
        grant_required=False,
    )


def _profile(ranking: list[str] | None = None) -> Profile:
    return Profile(
        student_id=uuid4(),
        questionnaire=Questionnaire(
            priorities=Priorities(
                ranking=ProfileField(value=ranking, mark="stated")
                if ranking
                else ProfileField(value=None)
            ),
        ),
    )


def test_differs_shows_factors():
    p = _profile()
    programs = [_program("p1"), _program("p2")]
    hard = [
        _hard("p1", {"exam_score:SAT_MATH": "above"}),
        _hard("p2", {"exam_score:SAT_MATH": "below"}),
    ]
    out = compare(p, programs, hard)
    factor_row = next(r for r in out.rows if r.param == "exam_score:SAT_MATH")
    assert factor_row.differs
    assert factor_row.values["p1"] == "above"
    assert factor_row.values["p2"] == "below"


def test_collapsed_same_for_same_cost():
    p = _profile()
    programs = [_program("p1", tuition=40000), _program("p2", tuition=40000)]
    out = compare(p, programs, [])
    # стоимость одинаковая → должна быть в collapsed_same
    assert "стоимость / год" in out.collapsed_same


def test_same_cost_in_collapsed():
    p = _profile()
    programs = [_program("p1", tuition=40000), _program("p2", tuition=40000)]
    out = compare(p, programs, [])
    cost_rows = [r for r in out.rows if r.param == "стоимость / год"]
    assert cost_rows == []  # не в rows
    assert "стоимость / год" in out.collapsed_same


def test_different_cost_in_rows():
    p = _profile()
    programs = [_program("p1", tuition=40000), _program("p2", tuition=50000)]
    out = compare(p, programs, [])
    cost_row = next(r for r in out.rows if r.param == "стоимость / год")
    assert cost_row.differs


def test_conclusion_is_none():
    p = _profile()
    out = compare(p, [], [])
    assert out.conclusion is None


def test_priorities_added_as_rows():
    p = _profile(ranking=["research", "mobility", "ranking"])
    programs = [
        _program("p1", environment="strong research, exchange partners"),
        _program("p2", environment="small town only"),
    ]
    out = compare(p, programs, [])
    research_row = next(r for r in out.rows if r.param == "research")
    assert research_row.differs


def test_returns_compare_out():
    p = _profile()
    out = compare(p, [_program("p1")], [])
    assert out.program_ids == ["p1"]
