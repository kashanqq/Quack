"""Fixtures for the pure Quack rules (§13.1)."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.schemas.knowledge import (
    ExamFormat,
    ForecastOut,
    KnowledgeStateOut,
    Section,
    SkillRef,
    SkillWeight,
    TestDate,
)
from app.schemas.profile import Profile
from app.schemas.programs import Deadline, Program, Requirement

pytestmark = pytest.mark.phase4

TODAY = date(2026, 9, 19)
NOW = datetime(2026, 9, 19, 12, tzinfo=UTC)


def make_forecast(**overrides) -> ForecastOut:
    base = {
        "exam_id": "SAT_MATH",
        "predicted_raw": 30.0,
        "predicted_scaled": 600.0,
        "coverage": 0.8,
        "hours_needed": 40.0,
        "ready_by": date(2026, 11, 20),
        "test_date": date(2026, 11, 7),
        "on_track": False,
        "as_of_event_id": 7,
        "note": "по модели знаний",
    }
    return ForecastOut(**{**base, **overrides})


def make_program(index: int, threshold: float | None = None, **overrides) -> Program:
    requirements = []
    if threshold is not None:
        requirements.append(
            Requirement(
                type="exam_score",
                exam_id="SAT_MATH",
                threshold=threshold,
                comparator=">=",
                description=f"SAT Math ≥ {int(threshold)}",
            )
        )
    base = {
        "id": f"program-{index}",
        "university": f"University {index}",
        "country": "US",
        "city": "Boston",
        "direction": "math",
        "language": "en",
        "currency": "USD",
        "requirements": requirements,
        "deadlines": [
            Deadline(
                kind="application",
                date=date(2026, 12, 1 + index),
                round=None,
                source="https://example.com",
                checked_at=TODAY,
                is_demo=False,
            )
        ],
        "source_url": "https://example.com",
        "checked_at": TODAY,
        "is_demo": False,
        "extracted_auto": False,
        "flagged": False,
    }
    return Program(**{**base, **overrides})


def make_state(skill_id: str, p_recall: float, confidence: float = 0.8):
    return KnowledgeStateOut(
        skill_id=skill_id,
        exam_id="SAT_MATH",
        p_recall=p_recall,
        p_at_obs=p_recall,
        half_life_h=48,
        confidence=confidence,
        evidence_mass=3.0,
        n_correct=3,
        n_incorrect=1,
        n_partial=0,
        has_strong=True,
        last_observed_at=NOW,
        created_at=NOW,
    )


def make_skill_weight(skill_id: str, effort_h: float = 4.0, weight: float = 1.0):
    return SkillWeight(
        skill=SkillRef(
            id=skill_id,
            name=skill_id,
            description="",
            exam_ids=["SAT_MATH"],
            effort_h=effort_h,
        ),
        area_id="algebra",
        weight=weight,
    )


def make_exam_format() -> ExamFormat:
    return ExamFormat(
        exam_id="SAT_MATH",
        name="SAT Math",
        max_raw_score=44.0,
        sections=[
            Section(
                name="Math",
                n_items=44,
                minutes=70,
                item_types={"mcq4": 33, "numeric": 11},
                scoring_rule="raw",
                calculator=True,
                adaptive=True,
                area_shares={"algebra": 1.0},
                difficulty_shares={"1": 1.0},
                answer_forms=["mcq4", "numeric"],
            )
        ],
        scale_table={"0": 200, "22": 500, "44": 800},
        scale_note=None,
        source="collegeboard",
        checked_at=TODAY,
        is_demo=False,
    )


def make_test_dates() -> list[TestDate]:
    return [
        TestDate(
            exam_id="SAT_MATH",
            date=date(2026, 11, 7),
            registration_deadline=date(2026, 10, 7),
            source="collegeboard",
            checked_at=TODAY,
            is_demo=False,
        ),
        TestDate(
            exam_id="SAT_MATH",
            date=date(2026, 12, 5),
            registration_deadline=date(2026, 11, 5),
            source="collegeboard",
            checked_at=TODAY,
            is_demo=False,
        ),
    ]


@pytest.fixture
def profile() -> Profile:
    return Profile(student_id=uuid4())


@pytest.fixture
def today() -> date:
    return TODAY


@pytest.fixture
def now() -> datetime:
    return NOW
