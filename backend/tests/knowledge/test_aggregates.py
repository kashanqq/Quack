"""Daily activity aggregates — §13.1 `test_aggregates.py`."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.config import KnowledgeParams
from app.knowledge.aggregates import answer_shares, daily, is_active, summarize
from app.schemas.events import Event, EventType
from app.schemas.knowledge import MisconceptionStateOut
from app.schemas.profile import Profile

pytestmark = pytest.mark.phase4

PARAMS = KnowledgeParams()
TZ = PARAMS.activity_tz  # Asia/Almaty, UTC+5
STUDENT = uuid4()
SESSION_A = uuid4()
SESSION_B = uuid4()


def _event(
    event_id: int,
    event_type: EventType,
    when: datetime,
    *,
    session_id: UUID | None = SESSION_A,
    payload: dict | None = None,
) -> Event:
    return Event(
        id=event_id,
        type=event_type,
        payload=payload or {},
        student_id=STUDENT,
        session_id=session_id,
        occurred_at=when,
        ingested_at=when,
    )


def test_day_boundary_follows_the_student_timezone():
    # 22:30 UTC — это уже 03:30 следующего дня в Алматы (§9.3).
    events = [
        _event(1, EventType.task_answered, datetime(2026, 9, 10, 22, 30, tzinfo=UTC))
    ]
    days = daily(events, {}, TZ, (date(2026, 9, 10), date(2026, 9, 11)), PARAMS)
    by_day = {item.day: item for item in days}
    assert by_day[date(2026, 9, 10)].tasks_answered == 0
    assert by_day[date(2026, 9, 11)].tasks_answered == 1


def test_window_contains_every_day_even_the_empty_ones():
    days = daily([], {}, TZ, (date(2026, 9, 1), date(2026, 9, 5)), PARAMS)
    assert [item.day for item in days] == [
        date(2026, 9, 1) + timedelta(days=offset) for offset in range(5)
    ]
    assert all(not is_active(item, PARAMS) for item in days)


def test_active_minutes_are_measured_per_session():
    start = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)  # 11:00 Алматы
    events = [
        _event(1, EventType.task_answered, start),
        _event(2, EventType.task_answered, start + timedelta(minutes=25)),
        _event(3, EventType.message_user, start + timedelta(minutes=40)),
        _event(
            4, EventType.task_answered, start + timedelta(hours=3), session_id=SESSION_B
        ),
        _event(
            5,
            EventType.task_answered,
            start + timedelta(hours=3, minutes=10),
            session_id=SESSION_B,
        ),
    ]
    [day] = daily(events, {}, TZ, (date(2026, 9, 10), date(2026, 9, 10)), PARAMS)
    assert day.sessions == 2
    assert day.active_minutes == 50
    assert day.tasks_answered == 4
    assert day.chat_messages == 1
    assert is_active(day, PARAMS)


def test_a_session_across_midnight_belongs_to_the_day_it_started():
    # 18:40 UTC = 23:40 Алматы; следующее событие уже после полуночи там.
    events = [
        _event(1, EventType.task_answered, datetime(2026, 9, 10, 18, 40, tzinfo=UTC)),
        _event(2, EventType.task_answered, datetime(2026, 9, 10, 19, 20, tzinfo=UTC)),
    ]
    days = daily(events, {}, TZ, (date(2026, 9, 10), date(2026, 9, 11)), PARAMS)
    by_day = {item.day: item for item in days}
    assert by_day[date(2026, 9, 10)].tasks_answered == 1
    assert by_day[date(2026, 9, 11)].tasks_answered == 1


def test_correctness_comes_from_the_task_instance():
    instance_id = uuid4()
    events = [
        _event(
            1,
            EventType.task_answered,
            datetime(2026, 9, 10, 6, tzinfo=UTC),
            payload={"instance_id": str(instance_id)},
        )
    ]
    instances = {instance_id: SimpleNamespace(correct=True, time_reference_sec=60)}
    [day] = daily(events, instances, TZ, (date(2026, 9, 10), date(2026, 9, 10)), PARAMS)
    assert (day.tasks_answered, day.tasks_correct) == (1, 1)


def test_recomputing_the_window_gives_the_same_rows():
    events = [
        _event(
            index, EventType.task_answered, datetime(2026, 9, 10, 6, index, tzinfo=UTC)
        )
        for index in range(1, 6)
    ]
    window = (date(2026, 9, 8), date(2026, 9, 11))
    first = daily(events, {}, TZ, window, PARAMS)
    second = daily(events, {}, TZ, window, PARAMS)
    assert [item.model_dump() for item in first] == [
        item.model_dump() for item in second
    ]


def test_hours_per_week_covers_the_last_seven_full_days():
    now = datetime(2026, 9, 12, 9, tzinfo=UTC)
    # Шаг между событиями меньше `session_gap_min`, иначе сессия режется
    # на куски и минуты между ними по правилу не считаются.
    events = [
        _event(
            index,
            EventType.task_answered,
            datetime(2026, 9, 10, 6, 0, tzinfo=UTC) + timedelta(minutes=20 * index),
        )
        for index in range(4)
    ]
    days = daily(events, {}, TZ, (date(2026, 9, 1), date(2026, 9, 12)), PARAMS)
    summary = summarize(days, [], Profile(student_id=STUDENT), [], now, PARAMS)
    assert summary.hours_per_week_actual == pytest.approx(1.0)
    assert summary.active_days == 1
    assert summary.active_days_by_day["2026-09-10"] is True


def test_error_class_distribution_sums_to_one():
    states = [
        MisconceptionStateOut(
            misconception_id="m1",
            name="m1",
            status="confirmed",
            occurrence_count=3,
            strong_count=1,
            consecutive_avoided=0,
            triggers={"error_class": "conceptual"},
            first_seen_at=datetime(2026, 9, 1, tzinfo=UTC),
            updated_at=datetime(2026, 9, 5, tzinfo=UTC),
            skill_ids=["a"],
        ),
        MisconceptionStateOut(
            misconception_id="m2",
            name="m2",
            status="confirmed",
            occurrence_count=1,
            strong_count=0,
            consecutive_avoided=0,
            triggers={"error_class": "computational"},
            first_seen_at=datetime(2026, 9, 1, tzinfo=UTC),
            updated_at=datetime(2026, 9, 5, tzinfo=UTC),
            skill_ids=["a"],
        ),
        # Оспоренное заблуждение в распределение не входит (§9.1).
        MisconceptionStateOut(
            misconception_id="m3",
            name="m3",
            status="disputed",
            occurrence_count=10,
            strong_count=0,
            consecutive_avoided=0,
            triggers={"error_class": "attention"},
            first_seen_at=datetime(2026, 9, 1, tzinfo=UTC),
            updated_at=datetime(2026, 9, 5, tzinfo=UTC),
            skill_ids=["a"],
        ),
    ]
    summary = summarize(
        [], states, Profile(student_id=STUDENT), [], datetime(2026, 9, 12, tzinfo=UTC)
    )
    assert sum(summary.error_class_dist.values()) == pytest.approx(1.0)
    assert summary.error_class_dist["conceptual"] == pytest.approx(0.75)
    assert "attention" not in summary.error_class_dist


def test_no_misconceptions_means_an_empty_distribution():
    summary = summarize(
        [], [], Profile(student_id=STUDENT), [], datetime(2026, 9, 12, tzinfo=UTC)
    )
    assert summary.error_class_dist == {}


def test_pace_signals_count_timeouts_and_observer_hints():
    now = datetime(2026, 9, 12, 9, tzinfo=UTC)
    events = [_event(1, EventType.task_timed_out, datetime(2026, 9, 10, 6, tzinfo=UTC))]
    days = daily(events, {}, TZ, (date(2026, 9, 6), date(2026, 9, 12)), PARAMS)
    observations = [
        _event(
            2,
            EventType.observation_extracted,
            datetime(2026, 9, 11, 6, tzinfo=UTC),
            payload={"observations": [{"kind": "pace_signal"}, {"kind": "other"}]},
        )
    ]
    summary = summarize(
        days, [], Profile(student_id=STUDENT), observations, now, PARAMS
    )
    assert summary.pace_signals.timeouts_7d == 1
    assert summary.pace_signals.asked_to_slow_down_7d == 1


def test_answer_shares_report_hurry_and_late_sessions():
    fast, slow = uuid4(), uuid4()
    events = [
        _event(
            1,
            EventType.task_answered,
            datetime(2026, 9, 10, 6, tzinfo=UTC),
            payload={
                "instance_id": str(fast),
                "time_spent_sec": 10,
                "session_minute": 90,
            },
        ),
        _event(
            2,
            EventType.task_answered,
            datetime(2026, 9, 10, 7, tzinfo=UTC),
            payload={
                "instance_id": str(slow),
                "time_spent_sec": 80,
                "session_minute": 5,
            },
        ),
    ]
    instances = {
        fast: SimpleNamespace(correct=True, time_reference_sec=100),
        slow: SimpleNamespace(correct=False, time_reference_sec=100),
    }
    hurried, late = answer_shares(events, instances)
    assert hurried == pytest.approx(0.5)
    assert late == pytest.approx(0.5)
    assert answer_shares([], {}) == (None, None)
