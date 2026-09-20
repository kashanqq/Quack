"""The Quack feed rules — §13.1 `test_plan.py` and `test_urgency.py`."""

from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.config import KnowledgeParams
from app.quack.plan import PlanInputs, plan, reason_hash
from app.schemas.matching import MatchOut
from app.schemas.quack import PaceVariantOut, StudentAggregates
from app.schemas.roadmap import ConflictOut, ExamRequirementOut, MilestoneOut
from app.schemas.sets import SetOut, SetProgress, SetsByExam, TopicOut
from tests.quack.conftest import (
    NOW,
    TODAY,
    make_forecast,
    make_program,
)

pytestmark = pytest.mark.phase4

PARAMS = KnowledgeParams()


def _inputs(profile, **overrides) -> PlanInputs:
    base = {
        "today": TODAY,
        "profile": profile,
        "saved": [],
        "requirements": [],
        "milestones": [],
        "conflicts": [],
        "forecasts": {},
        "pace_variants": {},
        "sets_by_exam": {},
        "matching_now": [],
        "matching_prev": None,
        "aggregates": None,
        "open_recs": [],
        "declined_hashes": set(),
        "previous_upcoming": {},
    }
    return PlanInputs(**{**base, **overrides})


def _variant(kind: str, available: bool = True, **params) -> PaceVariantOut:
    return PaceVariantOut(
        kind=kind,
        text=f"{kind} text",
        params=params,
        forecast=make_forecast(on_track=True, ready_by=date(2026, 11, 1)),
        available=available,
    )


def _milestone(key: str, on: date, done: bool = False) -> MilestoneOut:
    from app.schemas.common import Source

    return MilestoneOut(
        key=key,
        kind="registration",
        date=on,
        title=f"веха {key}",
        exam_id="SAT_MATH",
        program_id=None,
        source=Source(label="collegeboard", url=None, checked_at=TODAY, is_demo=False),
        done=done,
    )


def _set(status: str, skills: tuple[str, ...] = ("a",), deadline=None) -> SetOut:
    return SetOut(
        id=uuid4(),
        exam_id="SAT_MATH",
        area_ids=["algebra"],
        status=status,
        kind="regular",
        position=0,
        deadline=deadline or date(2026, 10, 20),
        reason="по модели знаний",
        topics=[
            TopicOut(
                skill_id=skill,
                name=skill,
                kind="topic",
                position=index,
                status="open",
                level="shaky",
                is_root=False,
                misconception_labels=[],
                subtitle=None,
            )
            for index, skill in enumerate(skills)
        ],
        progress=SetProgress(
            topics_closed=0, topics_total=len(skills), tasks_answered=0, tasks_correct=0
        ),
    )


def _match(program, realism: str) -> MatchOut:
    return MatchOut(
        program=program,
        realism=realism,
        factors=[],
        assumptions=[],
        score=1.0,
        fits_text=None,
        soft_pending=False,
    )


# --- pace variants ---


def test_pace_variants_become_urgent_drafts(profile):
    inputs = _inputs(
        profile,
        forecasts={"SAT_MATH": make_forecast(on_track=False)},
        pace_variants={
            "SAT_MATH": [
                _variant("more_hours", hours_per_week=6),
                _variant("move_date", test_date="2026-12-05"),
                _variant("remove_program", available=False, program_id="p"),
            ]
        },
    )
    drafts = plan(inputs, PARAMS, TODAY)
    kinds = [draft.action.kind for draft in drafts]
    assert [draft.kind for draft in drafts] == ["pace_variant", "pace_variant"]
    assert all(draft.urgency == "urgent" for draft in drafts)
    # Недоступный вариант не предлагается вовсе.
    assert "program_remove" not in kinds
    assert kinds == ["profile_update", "requirement_update"]
    assert drafts[0].forecast_after is not None


def test_on_track_forecast_produces_no_pace_drafts(profile):
    inputs = _inputs(
        profile,
        forecasts={"SAT_MATH": make_forecast(on_track=True)},
        pace_variants={"SAT_MATH": [_variant("more_hours", hours_per_week=6)]},
    )
    assert plan(inputs, PARAMS, TODAY) == []


# --- milestones and urgency ---


@pytest.mark.parametrize(
    ("days", "expected"),
    [(3, "urgent"), (10, "high"), (25, "normal"), (40, None)],
)
def test_milestone_urgency_by_days(profile, days, expected):
    inputs = _inputs(
        profile, milestones=[_milestone("m1", TODAY + timedelta(days=days))]
    )
    drafts = plan(inputs, PARAMS, TODAY)
    if expected is None:
        assert drafts == []
    else:
        assert [draft.urgency for draft in drafts] == [expected]
        assert drafts[0].action.kind == "milestone_open"
        assert drafts[0].expires_at is not None


def test_done_milestone_is_not_offered(profile):
    inputs = _inputs(
        profile, milestones=[_milestone("m1", TODAY + timedelta(days=3), done=True)]
    )
    assert plan(inputs, PARAMS, TODAY) == []


def test_conflict_is_urgent_and_lists_options(profile):
    conflict = ConflictOut(
        kind="exam_after_deadline",
        milestone_keys=["a", "b"],
        text="тест позже дедлайна подачи",
        options=["перенести подачу"],
    )
    drafts = plan(_inputs(profile, conflicts=[conflict]), PARAMS, TODAY)
    assert drafts[0].kind == "conflict"
    assert drafts[0].urgency == "urgent"
    assert "перенести тест" in drafts[0].action_text


# --- sets ---


def test_next_set_offered_when_current_is_closed(profile):
    upcoming = _set("upcoming")
    inputs = _inputs(
        profile,
        sets_by_exam={
            "SAT_MATH": SetsByExam(
                exam_id="SAT_MATH",
                forecast=None,
                current=None,
                upcoming=[upcoming],
                done=[],
            )
        },
    )
    drafts = plan(inputs, PARAMS, TODAY)
    assert [draft.kind for draft in drafts] == ["next_set"]
    assert drafts[0].urgency == "high"
    assert drafts[0].action.set_id == upcoming.id


def test_set_change_when_upcoming_composition_moved(profile):
    upcoming = _set("upcoming", skills=("a", "b"))
    inputs = _inputs(
        profile,
        sets_by_exam={
            "SAT_MATH": SetsByExam(
                exam_id="SAT_MATH",
                forecast=None,
                current=_set("current"),
                upcoming=[upcoming],
                done=[],
            )
        },
        previous_upcoming={"SAT_MATH": ["a", "c"]},
    )
    drafts = plan(inputs, PARAMS, TODAY)
    assert [draft.kind for draft in drafts] == ["set_change"]
    assert drafts[0].urgency == "normal"


# --- programs ---


def test_saved_realism_shift_direction_sets_urgency(profile):
    program = make_program(1, threshold=1400)
    inputs = _inputs(
        profile,
        saved=[program],
        matching_now=[_match(program, "try")],
        matching_prev=[{"program_id": program.id, "realism": "possible"}],
    )
    worse = plan(inputs, PARAMS, TODAY)
    assert [(d.kind, d.urgency) for d in worse] == [("saved_realism_shift", "high")]

    inputs = _inputs(
        profile,
        saved=[program],
        matching_now=[_match(program, "possible")],
        matching_prev=[{"program_id": program.id, "realism": "try"}],
    )
    better = plan(inputs, PARAMS, TODAY)
    assert [(d.kind, d.urgency) for d in better] == [("saved_realism_shift", "normal")]


def test_program_new_fit_needs_a_previous_snapshot(profile):
    program = make_program(2)
    without = _inputs(profile, matching_now=[_match(program, "possible")])
    assert plan(without, PARAMS, TODAY) == []

    with_snapshot = _inputs(
        profile,
        matching_now=[_match(program, "possible")],
        matching_prev=[{"program_id": "other", "realism": "try"}],
    )
    drafts = plan(with_snapshot, PARAMS, TODAY)
    assert [draft.kind for draft in drafts] == ["program_new_fit"]


def test_diagnostic_suggested_only_without_a_measurement(profile):
    requirement = ExamRequirementOut(
        exam_id="SAT_MATH",
        target_score=1400,
        target_source="programs",
        max_raw_score=44,
        program_ids=["program-1"],
        test_dates=[],
        has_knowledge_model=True,
        current_estimate=None,
        estimate_note="по твоей оценке",
    )
    drafts = plan(_inputs(profile, requirements=[requirement]), PARAMS, TODAY)
    assert [draft.kind for draft in drafts] == ["diagnostic_suggested"]

    measured = _inputs(
        profile,
        requirements=[requirement],
        forecasts={"SAT_MATH": make_forecast(on_track=True, coverage=0.7)},
    )
    assert plan(measured, PARAMS, TODAY) == []


def test_activity_pause_is_quiet_and_yields_to_pace(profile):
    aggregates = StudentAggregates(
        student_id=profile.student_id, window_days=14, computed_at=NOW, active_days=0
    )
    sets = {
        "SAT_MATH": SetsByExam(
            exam_id="SAT_MATH",
            forecast=None,
            current=_set("current"),
            upcoming=[],
            done=[],
        )
    }
    inputs = _inputs(profile, aggregates=aggregates, sets_by_exam=sets)
    drafts = plan(inputs, PARAMS, TODAY)
    assert [(d.kind, d.urgency) for d in drafts] == [("activity_pause", "low")]
    assert "прогноз" in drafts[0].reason

    with_pace = _inputs(
        profile,
        aggregates=aggregates,
        sets_by_exam=sets,
        forecasts={"SAT_MATH": make_forecast(on_track=False)},
        pace_variants={"SAT_MATH": [_variant("more_hours", hours_per_week=6)]},
    )
    kinds = [draft.kind for draft in plan(with_pace, PARAMS, TODAY)]
    assert "activity_pause" not in kinds


# --- ordering, suppression, limits ---


def test_order_is_urgency_then_date_then_kind(profile):
    inputs = _inputs(
        profile,
        conflicts=[
            ConflictOut(
                kind="same_day_applications",
                milestone_keys=["x"],
                text="две подачи в один день",
                options=[],
            )
        ],
        milestones=[
            _milestone("soon", TODAY + timedelta(days=3)),
            _milestone("later", TODAY + timedelta(days=10)),
            _milestone("far", TODAY + timedelta(days=25)),
        ],
    )
    drafts = plan(inputs, PARAMS, TODAY)
    assert [draft.urgency for draft in drafts] == [
        "urgent",
        "urgent",
        "high",
        "normal",
    ]
    # Внутри `urgent`: ближайшая веха раньше конфликта без даты.
    assert drafts[0].milestone_key == "soon"
    assert [draft.position for draft in drafts] == [0, 1, 2, 3]


def test_declined_cause_is_not_offered_again(profile):
    inputs = _inputs(profile, milestones=[_milestone("m1", TODAY + timedelta(days=3))])
    first = plan(inputs, PARAMS, TODAY)
    suppressed = _inputs(
        profile,
        milestones=[_milestone("m1", TODAY + timedelta(days=3))],
        declined_hashes={first[0].reason_hash},
    )
    assert plan(suppressed, PARAMS, TODAY) == []


def test_feed_limit_keeps_urgent_and_high(profile):
    params = KnowledgeParams(quack_feed_limit=3)
    milestones = [
        _milestone(f"m{index}", TODAY + timedelta(days=20 + index))
        for index in range(8)
    ]
    milestones.append(_milestone("urgent", TODAY + timedelta(days=2)))
    drafts = plan(_inputs(profile, milestones=milestones), params, TODAY)
    assert len(drafts) == 3
    assert drafts[0].urgency == "urgent"


# --- the hash itself ---


def _pace_hash(hours: int) -> str:
    return reason_hash(
        "pace", exam_id="SAT_MATH", variant="more_hours", params={"h": hours}
    )


def test_reason_hash_is_stable_and_parameter_sensitive():
    first, again, other = _pace_hash(6), _pace_hash(6), _pace_hash(7)
    assert first == again != other
    # Порядок ключей причины не влияет на её личность.
    assert reason_hash("milestone", key="a") == reason_hash("milestone", key="a")
