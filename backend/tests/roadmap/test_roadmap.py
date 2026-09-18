"""Phase 2 B2 — requirements, conflicts, progress. 00-contracts-phase2.md §7.3."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.config import KnowledgeParams
from app.roadmap.conflicts import find_conflicts
from app.roadmap.milestones import milestone_key
from app.roadmap.progress import exam_progress
from app.roadmap.requirements import build_requirements
from app.schemas.common import Source
from app.schemas.knowledge import ExamFormat, Section, SkillStateView
from app.schemas.profile import Profile
from app.schemas.programs import Deadline, Program, Requirement
from app.schemas.roadmap import ExamRequirementOut, MilestoneOut

pytestmark = pytest.mark.phase2


def _sat_format() -> ExamFormat:
    return ExamFormat(
        exam_id="SAT_MATH",
        name="SAT Math",
        max_raw_score=800,
        sections=[
            Section(
                name="Math",
                n_items=44,
                minutes=70,
                item_types={"mcq4": 33, "numeric": 11},
                scoring_rule="raw_to_scaled",
                calculator=True,
                adaptive=True,
                area_shares={"alg": 0.35, "adv": 0.35, "psda": 0.15, "geo": 0.15},
                difficulty_shares={"easy": 0.3, "medium": 0.4, "hard": 0.3},
                answer_forms=["mcq4", "numeric"],
            )
        ],
        source="collegeboard.org",
        checked_at=date(2026, 9, 1),
        is_demo=False,
    )


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


def _milestone(
    key: str,
    kind: str,
    on: date,
    program_id: str | None = None,
    exam_id: str | None = None,
    done: bool = False,
) -> MilestoneOut:
    return MilestoneOut(
        key=key,
        kind=kind,
        date=on,
        title=key,
        exam_id=exam_id,
        program_id=program_id,
        source=Source(label="test", url=None, checked_at=on, is_demo=True),
        done=done,
        done_at=datetime.now(UTC) if done else None,
    )


# 1. requirements: два экзамена, target_score = максимум порогов,
# program_ids по убыванию порога, программа без exam_score не создаёт экзамен.
def test_requirements_two_exams_ranked_by_threshold(roadmap_fixture):
    plain_profile = Profile(student_id=uuid4())

    requirements = build_requirements(
        saved=roadmap_fixture.programs,
        profile=plain_profile,
        exam_formats={"SAT_MATH": _sat_format()},
        test_dates={
            "SAT_MATH": roadmap_fixture.sat_calendar,
            "ENT_MATH": roadmap_fixture.ent_calendar,
        },
        forecasts={},
        params=KnowledgeParams(),
    )

    by_exam = {requirement.exam_id: requirement for requirement in requirements}
    assert set(by_exam) == {"SAT_MATH", "ENT_MATH"}

    sat = by_exam["SAT_MATH"]
    assert sat.target_score == 720
    assert sat.target_source == "programs"
    assert sat.program_ids == ["mit-cs", "eth-cs"]

    ent = by_exam["ENT_MATH"]
    assert ent.target_score == 30
    assert ent.program_ids == ["kaznu-cs"]

    assert all("valencia-cs" not in r.program_ids for r in requirements)


# 2. requirements: ручная цель stated перебивает порог, target_source="manual".
def test_requirements_manual_target_overrides_threshold(roadmap_fixture):
    requirements = build_requirements(
        saved=roadmap_fixture.programs,
        profile=roadmap_fixture.profile,
        exam_formats={"SAT_MATH": _sat_format()},
        test_dates={"SAT_MATH": roadmap_fixture.sat_calendar},
        forecasts={},
        params=KnowledgeParams(),
    )

    sat = next(r for r in requirements if r.exam_id == "SAT_MATH")
    assert sat.target_score == 680
    assert sat.target_source == "manual"


# 6a. conflicts: exam_after_deadline на фикстуре "SAT 7 ноября против
# early-подачи 1 ноября" с текстом из product-logic.
def test_conflicts_exam_after_deadline(roadmap_fixture):
    conflicts = find_conflicts(
        milestones=[],
        saved=roadmap_fixture.programs,
        planned_test_dates={"SAT_MATH": date(2026, 11, 7)},
    )

    matches = [c for c in conflicts if c.kind == "exam_after_deadline"]
    assert len(matches) == 1
    assert (
        matches[0].text
        == "Конфликт: SAT 7 ноября не успевает к early-подаче МИТ 1 ноября"
    )
    assert (
        milestone_key("test", "SAT_MATH", date(2026, 11, 7))
        in matches[0].milestone_keys
    )
    assert (
        milestone_key("application", "mit-cs", date(2026, 11, 1))
        in matches[0].milestone_keys
    )


# 6b. conflicts: same_day_applications на двух программах с
# document-требованием в один день.
def test_conflicts_same_day_applications():
    same_day = date(2026, 12, 1)
    programs = [
        _program(
            "prog-a",
            "Program A",
            requirements=[
                Requirement(
                    type="document", comparator="present", description="транскрипт"
                )
            ],
            deadlines=[
                Deadline(
                    kind="application",
                    date=same_day,
                    source="a.edu",
                    checked_at=date(2026, 9, 1),
                    is_demo=False,
                )
            ],
        ),
        _program(
            "prog-b",
            "Program B",
            requirements=[
                Requirement(type="document", comparator="present", description="эссе")
            ],
            deadlines=[
                Deadline(
                    kind="application",
                    date=same_day,
                    source="b.edu",
                    checked_at=date(2026, 9, 1),
                    is_demo=False,
                )
            ],
        ),
    ]
    key_a = milestone_key("application", "prog-a", same_day)
    key_b = milestone_key("application", "prog-b", same_day)
    milestones = [
        _milestone(key_a, "application", same_day, program_id="prog-a"),
        _milestone(key_b, "application", same_day, program_id="prog-b"),
    ]

    conflicts = find_conflicts(
        milestones=milestones, saved=programs, planned_test_dates={}
    )

    matches = [c for c in conflicts if c.kind == "same_day_applications"]
    assert len(matches) == 1
    assert set(matches[0].milestone_keys) == {key_a, key_b}


# 6c. conflicts: негативный случай без конфликтов.
def test_conflicts_none_on_clean_data(roadmap_fixture):
    non_conflicting = [
        program
        for program in roadmap_fixture.programs
        if program.id in ("eth-cs", "kaznu-cs")
    ]

    conflicts = find_conflicts(
        milestones=[], saved=non_conflicting, planned_test_dates={}
    )

    assert conflicts == []


# 7. conflicts: exclusive_rounds — позитив и негатив в одном параметризованном тесте.
@pytest.mark.parametrize(
    ("binding_b", "same_date", "expected_count"),
    [
        pytest.param(True, True, 1, id="positive"),
        pytest.param(False, True, 0, id="negative"),
    ],
)
def test_conflicts_exclusive_rounds(binding_b, same_date, expected_count):
    date_a = date(2026, 11, 1)
    date_b = date_a if same_date else date(2026, 11, 15)

    requirements_b = (
        [
            Requirement(
                type="other", comparator="present", description="binding обязательство"
            )
        ]
        if binding_b
        else []
    )

    programs = [
        _program(
            "early-a",
            "Early University A",
            requirements=[
                Requirement(
                    type="other", comparator="present", description="binding commitment"
                )
            ],
            deadlines=[
                Deadline(
                    kind="application",
                    date=date_a,
                    round="early_decision",
                    source="a.edu",
                    checked_at=date(2026, 9, 1),
                    is_demo=False,
                )
            ],
        ),
        _program(
            "early-b",
            "Early University B",
            requirements=requirements_b,
            deadlines=[
                Deadline(
                    kind="application",
                    date=date_b,
                    round="early_decision",
                    source="b.edu",
                    checked_at=date(2026, 9, 1),
                    is_demo=False,
                )
            ],
        ),
    ]

    conflicts = find_conflicts(milestones=[], saved=programs, planned_test_dates={})

    matches = [c for c in conflicts if c.kind == "exclusive_rounds"]
    assert len(matches) == expected_count


# 8. progress: readiness на трёх SkillStateView с числами, посчитанными
# руками; milestones_done/total.
def test_progress_readiness_and_milestone_counts():
    states = [
        SkillStateView(
            skill_id="s1",
            name="s1",
            area_id="alg",
            exam_id="SAT_MATH",
            weight=2.0,
            p_target=0.8,
            level="shaky",
            p_recall=0.6,
            confidence=0.5,
            trend="flat",
            due_at=None,
            is_root=False,
            n_evidence=5,
        ),
        SkillStateView(
            skill_id="s2",
            name="s2",
            area_id="alg",
            exam_id="SAT_MATH",
            weight=1.0,
            p_target=0.5,
            level="solid",
            p_recall=0.9,
            confidence=0.5,
            trend="flat",
            due_at=None,
            is_root=False,
            n_evidence=5,
        ),
        SkillStateView(
            skill_id="s3",
            name="s3",
            area_id="alg",
            exam_id="SAT_MATH",
            weight=3.0,
            p_target=0.7,
            level="solid",
            p_recall=0.7,
            confidence=0.5,
            trend="flat",
            due_at=None,
            is_root=False,
            n_evidence=5,
        ),
    ]
    # closed = 2*min(0.6,0.8) + 1*min(0.9,0.5) + 3*min(0.7,0.7) = 1.2 + 0.5 + 2.1 = 3.8
    # total  = 2*0.8 + 1*0.5 + 3*0.7 = 1.6 + 0.5 + 2.1 = 4.2
    expected_readiness = 3.8 / 4.2

    requirement = ExamRequirementOut(
        exam_id="SAT_MATH",
        target_score=720,
        target_source="programs",
        max_raw_score=800,
        program_ids=["mit-cs"],
        test_dates=[],
        has_knowledge_model=True,
        current_estimate=None,
        estimate_note="нет данных",
    )
    milestones = [
        _milestone(
            "m1", "registration", date(2026, 10, 10), exam_id="SAT_MATH", done=True
        ),
        _milestone("m2", "test", date(2026, 11, 7), exam_id="SAT_MATH", done=True),
        _milestone(
            "m3",
            "application",
            date(2026, 12, 15),
            exam_id=None,
            program_id="mit-cs",
            done=True,
        ),
        _milestone("m4", "window", date(2026, 12, 1), exam_id="SAT_MATH", done=False),
        _milestone("m5", "test", date(2027, 6, 5), exam_id="ENT_MATH", done=False),
    ]

    progress = exam_progress(
        requirement=requirement, states=states, forecast=None, milestones=milestones
    )

    assert progress.readiness == pytest.approx(expected_readiness)
    assert progress.milestones_done == 2
    assert progress.milestones_total == 3
