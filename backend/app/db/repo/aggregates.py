"""Daily per-student aggregates and the window summary (§9).

`daily_aggregates` keeps one row per (student, day); `student_aggregates`
keeps the single window row the pace block and the tutor context read.
The nightly job recomputes the whole window, so every write is an upsert.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DailyAggregate, StudentAggregate
from app.schemas.quack import (
    ActivityDay,
    ActivityOut,
    DailyAggregatePayload,
    StudentAggregates,
)


async def add_pace_signal(
    session: AsyncSession,
    student_id: UUID,
    day: date,
    signal: str,
    source_event_id: int,
    ordinal: int,
) -> None:
    """Upsert one signal; `(source_event_id, ordinal)` already there — no-op."""
    row = await session.get(DailyAggregate, (student_id, day))
    entry = {"signal": signal, "event_id": source_event_id, "ordinal": ordinal}
    if row is None:
        session.add(
            DailyAggregate(
                student_id=student_id,
                day=day,
                active_minutes=0,
                tasks_answered=0,
                messages=0,
                payload={"pace_signals": [entry]},
            )
        )
        await session.flush()
        return
    payload = dict(row.payload or {})
    signals = list(payload.get("pace_signals") or [])
    if any(
        item.get("event_id") == source_event_id and item.get("ordinal") == ordinal
        for item in signals
    ):
        return
    signals.append(entry)
    payload["pace_signals"] = signals
    # JSONB column: assign a new object so SQLAlchemy sees the change.
    row.payload = payload
    await session.flush()


async def upsert_days(
    session: AsyncSession, student_id: UUID, days: list[DailyAggregatePayload]
) -> None:
    """Rewrite the window, preserving the observer's `pace_signals`."""
    for day in days:
        row = await session.get(DailyAggregate, (student_id, day.day))
        payload = day.model_dump(mode="json")
        if row is None:
            session.add(
                DailyAggregate(
                    student_id=student_id,
                    day=day.day,
                    active_minutes=day.active_minutes,
                    tasks_answered=day.tasks_answered,
                    messages=day.chat_messages,
                    payload=payload,
                )
            )
            continue
        existing = dict(row.payload or {})
        if existing.get("pace_signals"):
            payload["pace_signals"] = existing["pace_signals"]
        row.active_minutes = day.active_minutes
        row.tasks_answered = day.tasks_answered
        row.messages = day.chat_messages
        row.payload = payload
    await session.flush()


async def list_days(
    session: AsyncSession, student_id: UUID, since: date, until: date
) -> list[DailyAggregatePayload]:
    rows = (
        await session.scalars(
            select(DailyAggregate)
            .where(
                DailyAggregate.student_id == student_id,
                DailyAggregate.day >= since,
                DailyAggregate.day <= until,
            )
            .order_by(DailyAggregate.day)
        )
    ).all()
    out: list[DailyAggregatePayload] = []
    for row in rows:
        payload = dict(row.payload or {})
        payload.setdefault("day", row.day)
        payload.setdefault("tz", "")
        payload.pop("pace_signals", None)
        out.append(DailyAggregatePayload.model_validate(payload))
    return out


async def put_summary(
    session: AsyncSession,
    student_id: UUID,
    summary: StudentAggregates,
) -> None:
    row = await session.get(StudentAggregate, student_id)
    payload = summary.model_dump(mode="json")
    if row is None:
        session.add(
            StudentAggregate(
                student_id=student_id,
                payload=payload,
                computed_at=summary.computed_at,
                as_of_event_id=summary.as_of_event_id,
            )
        )
    else:
        row.payload = payload
        row.computed_at = summary.computed_at
        row.as_of_event_id = summary.as_of_event_id
    await session.flush()


async def get_summary(
    session: AsyncSession, student_id: UUID
) -> StudentAggregates | None:
    row = await session.get(StudentAggregate, student_id)
    return StudentAggregates.model_validate(row.payload) if row is not None else None


async def activity(
    session: AsyncSession,
    student_id: UUID,
    *,
    today: date,
    days: int,
    tz: str,
    hours_declared: int | None,
) -> ActivityOut:
    """The calendar as the front draws it — every day of the window present."""
    from datetime import timedelta

    since = today - timedelta(days=days - 1)
    rows = await list_days(session, student_id, since, today)
    by_day = {item.day: item for item in rows}
    summary = await get_summary(session, student_id)
    calendar: list[ActivityDay] = []
    active_days = 0
    for offset in range(days):
        day = since + timedelta(days=offset)
        item = by_day.get(day)
        active = bool(item and item.active_minutes >= 0 and _has_activity(item))
        active_days += int(active)
        calendar.append(
            ActivityDay(
                day=day,
                active=active,
                tasks_answered=item.tasks_answered if item else 0,
                mocks_completed=item.mocks_completed if item else 0,
                chat_messages=item.chat_messages if item else 0,
                active_minutes=item.active_minutes if item else 0,
            )
        )
    return ActivityOut(
        days=calendar,
        window_days=days,
        active_days=active_days,
        hours_per_week_actual=(
            summary.hours_per_week_actual if summary is not None else None
        ),
        hours_per_week_declared=hours_declared,
        computed_at=summary.computed_at if summary is not None else None,
        tz=tz,
    )


def _has_activity(item: DailyAggregatePayload) -> bool:
    return bool(
        item.tasks_answered
        or item.mocks_completed
        or item.chat_messages
        or item.tasks_timed_out
        or item.guidelines_opened
        or item.sessions
    )
