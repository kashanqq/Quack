"""B1 misconception dispute — memory-architecture §5.1.

I/O wrapper over knowledge.misconceptions.next_status: flip a state to
`disputed` (or back), persist via personal.upsert_misc_state, bump version.

Source: 00-contracts-phase2.md §7.2, 20-B1-phase2.md §7.
"""

from __future__ import annotations

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app.apply._lock import student_lock
from app.events.dispatch import RuleDeps
from app.events.version import bump
from app.graph.queries import canonical as canonical_q
from app.graph.queries import personal as personal_q
from app.knowledge.misconceptions import next_status
from app.schemas.events import Event, EventType
from app.schemas.knowledge import MisconceptionStateOut

_logger = structlog.get_logger(__name__)

_EXAMS = ("SAT_MATH", "ENT_MATH")


async def apply_dispute(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> MisconceptionStateOut:
    """Handle misconception.disputed / misconception.undisputed.

    Роутер уже записал событие; здесь — только переход статуса. Под локом
    ученика (phase3 F9): наблюдатель пишет те же состояния заблуждений.
    """
    async with student_lock(deps.redis, event.student_id):
        return await _apply_dispute(session, event, deps)


async def _apply_dispute(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> MisconceptionStateOut:
    if event.type not in (
        EventType.misconception_disputed,
        EventType.misconception_undisputed,
    ):
        raise ValueError(f"unexpected event type: {event.type}")

    if deps.graph is None:
        raise RuntimeError("graph unavailable")

    payload = event.payload or {}
    misconception_id = payload.get("misconception_id")
    if not misconception_id:
        raise ValueError("misconception_id missing in payload")

    is_dispute = event.type == EventType.misconception_disputed

    state = await _find_state(deps, event.student_id, misconception_id)
    if state is None:
        raise ValueError(f"misconception {misconception_id} not found for student")

    event_kind = "dispute" if is_dispute else "undispute"

    new_status = next_status(
        state.status,
        event=event_kind,  # type: ignore[arg-type]
        strong=False,
        occurrence_count=state.occurrence_count,
        strong_count=state.strong_count,
        consecutive_avoided=state.consecutive_avoided,
        strong_at_dispute=state.strong_count if is_dispute else 0,
        disputed_at=deps.now() if is_dispute else None,
        previous_status=state.status if not is_dispute else None,
        params=deps.params,
    )

    updated = await personal_q.upsert_misc_state(
        deps.graph,
        event.student_id,
        misconception_id,
        new_status,
        counters={
            "occurrence_count": state.occurrence_count,
            "strong_count": state.strong_count,
            "consecutive_avoided": state.consecutive_avoided,
        },
        triggers=state.triggers,
    )

    await bump(deps.redis, event.student_id)
    return updated


async def _find_state(
    deps: RuleDeps, student_id, misconception_id: str
) -> MisconceptionStateOut | None:
    """Найти состояние заблуждения по всем навыкам обоих экзаменов."""
    for exam_id in _EXAMS:
        try:
            weights = await canonical_q.list_exam_skills(deps.graph, exam_id)
        except (ServiceUnavailable, SessionExpired):
            return None
        skill_ids = [w.skill.id for w in weights]
        try:
            states = await personal_q.get_misc_states(deps.graph, student_id, skill_ids)
        except (ServiceUnavailable, SessionExpired):
            return None
        for s in states:
            if s.misconception_id == misconception_id:
                return s
    return None
