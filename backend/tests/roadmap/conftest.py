"""Shared fixture data for app.roadmap tests."""

from dataclasses import dataclass
from datetime import date
from uuid import uuid4

import pytest

from app.schemas.knowledge import TestDate
from app.schemas.profile import Profile
from app.schemas.programs import Deadline, Program, Requirement


def _program(
    program_id: str,
    university: str,
    requirements: list[Requirement],
    deadlines: list[Deadline],
) -> Program:
    return Program(
        id=program_id,
        university=university,
        country="XX",
        city="City",
        direction="CS",
        language="en",
        currency="USD",
        requirements=requirements,
        deadlines=deadlines,
        source_url=f"https://example.org/{program_id}",
        checked_at=date(2026, 9, 1),
        is_demo=False,
        extracted_auto=False,
        flagged=False,
    )


@dataclass(frozen=True)
class RoadmapFixture:
    programs: list[Program]
    sat_calendar: list[TestDate]
    ent_calendar: list[TestDate]
    profile: Profile


@pytest.fixture
def roadmap_fixture() -> RoadmapFixture:
    eth = _program(
        "eth-cs",
        "ETH Zurich",
        requirements=[
            Requirement(
                type="exam_score",
                exam_id="SAT_MATH",
                threshold=650,
                comparator=">=",
                description="SAT Math >= 650",
            )
        ],
        deadlines=[
            Deadline(
                kind="application",
                date=date(2026, 12, 15),
                source="eth.ch",
                checked_at=date(2026, 9, 1),
                is_demo=False,
            )
        ],
    )
    mit = _program(
        "mit-cs",
        "МИТ",
        requirements=[
            Requirement(
                type="exam_score",
                exam_id="SAT_MATH",
                threshold=720,
                comparator=">=",
                description="SAT Math >= 720",
            )
        ],
        deadlines=[
            Deadline(
                kind="application",
                date=date(2026, 11, 1),
                round="early",
                source="mit.edu",
                checked_at=date(2026, 9, 1),
                is_demo=False,
            )
        ],
    )
    kaznu = _program(
        "kaznu-cs",
        "КазНУ",
        requirements=[
            Requirement(
                type="exam_score",
                exam_id="ENT_MATH",
                threshold=30,
                comparator=">=",
                description="ЕНТ математика >= 30",
            ),
            Requirement(
                type="other",
                comparator="present",
                description="грант при поступлении",
            ),
        ],
        deadlines=[
            Deadline(
                kind="scholarship",
                date=date(2026, 12, 20),
                source="kaznu.kz",
                checked_at=date(2026, 9, 1),
                is_demo=False,
            )
        ],
    )
    valencia = _program(
        "valencia-cs",
        "Valencia",
        requirements=[
            Requirement(
                type="language",
                comparator="present",
                description="B2 Spanish",
            )
        ],
        deadlines=[
            Deadline(
                kind="application",
                date=date(2026, 12, 10),
                source="valencia.es",
                checked_at=date(2026, 9, 1),
                is_demo=False,
            )
        ],
    )

    sat_calendar = [
        TestDate(
            exam_id="SAT_MATH",
            date=date(2026, 11, 7),
            registration_deadline=date(2026, 10, 10),
            late_deadline=date(2026, 10, 24),
            source="collegeboard.org",
            checked_at=date(2026, 9, 1),
            is_demo=False,
        ),
        TestDate(
            exam_id="SAT_MATH",
            date=date(2026, 12, 5),
            registration_deadline=date(2026, 11, 7),
            source="collegeboard.org",
            checked_at=date(2026, 9, 1),
            is_demo=False,
        ),
    ]
    ent_calendar = [
        TestDate(
            exam_id="ENT_MATH",
            date=date(2027, 6, 5),
            registration_deadline=date(2027, 5, 1),
            source="nis.edu.kz",
            checked_at=date(2026, 9, 1),
            is_demo=False,
        ),
    ]

    profile = Profile(student_id=uuid4())
    profile.questionnaire.academics.sat_date.value = date(2026, 11, 7)
    profile.questionnaire.academics.sat_date.mark = "stated"
    profile.questionnaire.academics.sat_target.value = 680
    profile.questionnaire.academics.sat_target.mark = "stated"

    return RoadmapFixture(
        programs=[eth, mit, kaznu, valencia],
        sat_calendar=sat_calendar,
        ent_calendar=ent_calendar,
        profile=profile,
    )
