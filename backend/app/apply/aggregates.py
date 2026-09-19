"""Recomputing the activity window from the event log (§9.4).

Always the whole window, never an increment: the events are append-only, so
a full recompute is deterministic and a repeated run is a no-op. That is
what makes the nightly cron safe to miss and safe to run twice.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TaskInstance
from app.db.repo import aggregates as aggregates_repo
from app.db.repo import profiles as profiles_repo
from app.events import store as events_store
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical as canonical_q
from app.graph.queries import personal as personal_q
from app.knowledge.aggregates import ACTIVITY_TYPES, answer_shares, daily, summarize
from app.schemas.events import EventType
from app.schemas.quack import StudentAggregates

_logger = structlog.get_logger(__name__)

_EVENT_LIMIT = 5000


async def run(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    day: date | None = None,
    force: bool = False,
) -> StudentAggregates | None:
    """Recompute the window ending on `day`; skip when nothing new happened."""
    params = deps.params
    zone = ZoneInfo(params.activity_tz)
    now = deps.now()
    until = day or now.astimezone(zone).date()
    since = until - timedelta(days=params.aggregate_window_days - 1)

    as_of = await events_store.last_event_id(session, student_id)
    existing = await aggregates_repo.get_summary(session, student_id)
    if not force and existing is not None and existing.as_of_event_id >= as_of:
        _logger.info("aggregates_unchanged", student_id=str(student_id))
        return existing

    # Границы дня в поясе ученика, переведённые в UTC для выборки.
    window_start = datetime.combine(since, time.min, tzinfo=zone).astimezone(UTC)
    events = await events_store.list_events(
        session,
        student_id,
        types=list(ACTIVITY_TYPES),
        since=window_start,
        limit=_EVENT_LIMIT,
    )
    instance_ids = [
        _uuid(event.payload.get("instance_id"))
        for event in events
        if event.type == EventType.task_answered and (event.payload or {})
    ]
    instances = await _instances(session, [i for i in instance_ids if i is not None])

    days = daily(events, instances, params.activity_tz, (since, until), params)
    await aggregates_repo.upsert_days(session, student_id, days)

    profile = await profiles_repo.get_profile(session, student_id)
    observations = await events_store.list_events(
        session,
        student_id,
        types=[EventType.observation_extracted],
        since=window_start,
        limit=_EVENT_LIMIT,
    )
    misc_states, graph_stale = await _misconceptions(deps, student_id, existing)
    summary = summarize(
        days,
        misc_states,
        profile,
        observations,
        now,
        params,
        as_of_event_id=as_of,
        graph_stale=graph_stale,
    )
    if graph_stale and existing is not None:
        # Граф недоступен: распределение классов ошибок берём прошлое, с
        # пометкой, вместо того чтобы показать пустое (§2.3).
        summary = summary.model_copy(
            update={"error_class_dist": existing.error_class_dist}
        )
    hurried, late = answer_shares(events, instances)
    summary = summary.model_copy(
        update={
            "pace_signals": summary.pace_signals.model_copy(
                update={
                    "hurried_share_7d": hurried,
                    "late_session_share_7d": late,
                }
            )
        }
    )
    await aggregates_repo.put_summary(session, student_id, summary)
    return summary


async def _instances(
    session: AsyncSession, instance_ids: list[UUID]
) -> dict[UUID, TaskInstance]:
    if not instance_ids:
        return {}
    rows = (
        await session.scalars(
            select(TaskInstance).where(TaskInstance.id.in_(instance_ids))
        )
    ).all()
    return {row.id: row for row in rows}


async def _misconceptions(
    deps: RuleDeps, student_id: UUID, existing: StudentAggregates | None
) -> tuple[list, bool]:
    del existing
    if deps.graph is None:
        return [], True
    try:
        skill_ids: list[str] = []
        for exam_id in ("SAT_MATH", "ENT_MATH"):
            skill_ids += [
                weight.skill.id
                for weight in await canonical_q.list_exam_skills(deps.graph, exam_id)
            ]
        states = await personal_q.get_misc_states(deps.graph, student_id, skill_ids)
        return states, False
    except (ServiceUnavailable, SessionExpired):
        _logger.warning("aggregates_graph_unavailable", student_id=str(student_id))
        return [], True


def _uuid(value) -> UUID | None:
    if value is None:
        return None
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None
