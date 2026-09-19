"""Daily activity aggregates — §9.

Pure and deterministic: the job recomputes the whole window from the same
append-only event rows, so a repeat run produces byte-identical output. The
day boundary is `activity_tz`, not UTC — the calendar the student sees is
the one they live in.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.config import KnowledgeParams
from app.schemas.common import ErrorClass
from app.schemas.events import Event, EventType
from app.schemas.knowledge import MisconceptionStateOut
from app.schemas.profile import Profile
from app.schemas.quack import DailyAggregatePayload, PaceSignals, StudentAggregates

# Событие любого из этих типов считается активностью дня (§9.2).
ACTIVITY_TYPES: tuple[EventType, ...] = (
    EventType.task_answered,
    EventType.task_timed_out,
    EventType.mock_completed,
    EventType.message_user,
    EventType.guideline_opened,
    EventType.explanation_opened,
    EventType.set_opened,
    EventType.diagnostic_completed,
)

_NO_SESSION_MINUTES_CAP = 30
_HURRIED_RATIO = 0.5
_LATE_SESSION_MINUTE = 60
_FULL_WEEK_DAYS = 7


def _local_day(moment: datetime, tz: ZoneInfo) -> date:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(tz).date()


def _fact(instances: dict[Any, Any], instance_id: Any, name: str) -> Any:
    item = instances.get(instance_id)
    if item is None:
        return None
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def daily(
    events: list[Event],
    instances: dict[Any, Any],
    tz: str,
    window: tuple[date, date],
    params: KnowledgeParams | None = None,
) -> list[DailyAggregatePayload]:
    """One row per day of the window, every day present (§9.4)."""
    params = params or KnowledgeParams()
    zone = ZoneInfo(tz)
    since, until = window
    buckets: dict[date, list[Event]] = defaultdict(list)
    for event in events:
        if event.type not in ACTIVITY_TYPES:
            continue
        day = _local_day(event.occurred_at, zone)
        if since <= day <= until:
            buckets[day].append(event)

    out: list[DailyAggregatePayload] = []
    day = since
    while day <= until:
        out.append(_one_day(day, buckets.get(day, []), instances, tz, zone, params))
        day += timedelta(days=1)
    return out


def _one_day(
    day: date,
    events: list[Event],
    instances: dict[Any, Any],
    tz: str,
    zone: ZoneInfo,
    params: KnowledgeParams,
) -> DailyAggregatePayload:
    ordered = sorted(events, key=lambda event: (event.occurred_at, event.id))
    answered = correct = timed_out = mocks = messages = guidelines = 0
    for event in ordered:
        if event.type == EventType.task_answered:
            answered += 1
            instance_id = (event.payload or {}).get("instance_id")
            if _fact(instances, _key(instance_id), "correct") is True:
                correct += 1
        elif event.type == EventType.task_timed_out:
            timed_out += 1
        elif event.type == EventType.mock_completed:
            mocks += 1
        elif event.type == EventType.message_user:
            messages += 1
        elif event.type in (EventType.guideline_opened, EventType.explanation_opened):
            guidelines += 1

    sessions, minutes = _sessions(ordered, params)
    return DailyAggregatePayload(
        day=day,
        tz=tz,
        sessions=sessions,
        active_minutes=minutes,
        tasks_answered=answered,
        tasks_correct=correct,
        tasks_timed_out=timed_out,
        mocks_completed=mocks,
        chat_messages=messages,
        guidelines_opened=guidelines,
        first_event_at=(ordered[0].occurred_at.astimezone(zone) if ordered else None),
        last_event_at=(ordered[-1].occurred_at.astimezone(zone) if ordered else None),
    )


def _key(value: Any) -> Any:
    """Event payloads carry ids as strings; callers may key by UUID."""
    if value is None:
        return None
    from uuid import UUID

    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return value


def _sessions(events: list[Event], params: KnowledgeParams) -> tuple[int, int]:
    """Minutes of work: `last − first` per session, at least one per session.

    Events without a `session_id` are older rows: one minute each, capped so
    a long-ago import cannot invent a whole day of study.
    """
    by_session: dict[Any, list[datetime]] = defaultdict(list)
    loose = 0
    for event in events:
        if event.session_id is None:
            loose += 1
            continue
        by_session[event.session_id].append(event.occurred_at)

    minutes = 0
    for stamps in by_session.values():
        stamps.sort()
        # Разрыв длиннее session_gap_min режет сессию: по построению его не
        # бывает (TTL ключа продлевается), но replay старого журнала может
        # склеить два визита в один id.
        chunk_start = stamps[0]
        previous = stamps[0]
        for moment in stamps[1:]:
            if (moment - previous).total_seconds() > params.session_gap_min * 60:
                minutes += max(1, int((previous - chunk_start).total_seconds() // 60))
                chunk_start = moment
            previous = moment
        minutes += max(1, int((previous - chunk_start).total_seconds() // 60))
    minutes += min(loose, _NO_SESSION_MINUTES_CAP)
    sessions = len(by_session) + (1 if loose else 0)
    return sessions, minutes


def is_active(day: DailyAggregatePayload, params: KnowledgeParams) -> bool:
    events = (
        day.tasks_answered
        + day.tasks_timed_out
        + day.mocks_completed
        + day.chat_messages
        + day.guidelines_opened
    )
    return events >= params.active_day_min_events


def summarize(
    days: list[DailyAggregatePayload],
    misc_states: list[MisconceptionStateOut],
    profile: Profile,
    observations: list[Event],
    now: datetime,
    params: KnowledgeParams | None = None,
    *,
    as_of_event_id: int = 0,
    graph_stale: bool = False,
) -> StudentAggregates:
    """The window row the pace block and the tutor context read (§9.1)."""
    params = params or KnowledgeParams()
    ordered = sorted(days, key=lambda item: item.day)
    today = now.date()
    last_week = [
        item
        for item in ordered
        if today - timedelta(days=_FULL_WEEK_DAYS) <= item.day < today
    ]
    hours = round(sum(item.active_minutes for item in last_week) / 60, 4)
    active_by_day = {item.day.isoformat(): is_active(item, params) for item in ordered}

    return StudentAggregates(
        student_id=profile.student_id,
        window_days=params.aggregate_window_days,
        computed_at=now,
        as_of_event_id=as_of_event_id,
        hours_per_week_actual=hours,
        hours_per_week_declared=profile.questionnaire.pace.hours_per_week.value,
        active_days=sum(1 for value in active_by_day.values() if value),
        active_days_by_day=active_by_day,
        error_class_dist=_error_classes(misc_states),
        pace_signals=_pace_signals(ordered, observations, now),
        graph_stale=graph_stale,
    )


def _error_classes(
    misc_states: list[MisconceptionStateOut],
) -> dict[ErrorClass, float]:
    """Shares of Σ occurrence_count; `disputed` states do not count."""
    totals: dict[str, float] = defaultdict(float)
    for state in misc_states:
        if state.status == "disputed":
            continue
        error_class = state.triggers.get("error_class") if state.triggers else None
        if not error_class:
            continue
        totals[str(error_class)] += float(state.occurrence_count or 0)
    grand = sum(totals.values())
    if grand <= 0:
        return {}
    return {
        key: round(value / grand, 6)  # type: ignore[misc]
        for key, value in sorted(totals.items())
    }


def _pace_signals(
    days: list[DailyAggregatePayload], observations: list[Event], now: datetime
) -> PaceSignals:
    since = now.date() - timedelta(days=_FULL_WEEK_DAYS)
    week = [item for item in days if item.day >= since]
    slowed = 0
    for event in observations:
        if event.occurred_at.date() < since:
            continue
        for item in (event.payload or {}).get("observations", []) or []:
            if isinstance(item, dict) and item.get("kind") == "pace_signal":
                slowed += 1
    return PaceSignals(
        timeouts_7d=sum(item.tasks_timed_out for item in week),
        asked_to_slow_down_7d=slowed,
        hurried_share_7d=None,
        late_session_share_7d=None,
    )


def answer_shares(
    events: list[Event], instances: dict[Any, Any]
) -> tuple[float | None, float | None]:
    """(hurried share, late-session share) over `task.answered` (§9.2).

    Kept separate from `summarize` because it needs the task instances, and
    the caller may not have them when the graph is down.
    """
    total = hurried = late = 0
    for event in events:
        if event.type != EventType.task_answered:
            continue
        payload = event.payload or {}
        total += 1
        reference = _fact(
            instances, _key(payload.get("instance_id")), "time_reference_sec"
        )
        spent = payload.get("time_spent_sec")
        if reference and spent is not None and spent < _HURRIED_RATIO * reference:
            hurried += 1
        if (payload.get("session_minute") or 0) >= _LATE_SESSION_MINUTE:
            late += 1
    if total == 0:
        return None, None
    return round(hurried / total, 4), round(late / total, 4)
