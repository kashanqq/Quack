"""Daily per-student aggregates (`daily_aggregates`) — pace signals for now.

The nightly aggregation itself is phase 4; phase 3 only appends the
observer's `pace_signal` observations to `payload.pace_signals` of that day.
"""

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DailyAggregate


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
