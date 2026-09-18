"""B1 set apply — memory-architecture §10.1, apply contract §7.2.

I/O layer: gather inputs from graph + Postgres, call pure functions
(build_queue, assemble_sets, forecast), persist via repo.sets / repo.forecast.

Source: 00-contracts-phase2.md §7.2, 20-B1-phase2.md §7.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app.apply.targets import p_target_for
from app.db.repo import forecast as forecast_repo
from app.db.repo import profiles as profiles_repo
from app.db.repo import sets as sets_repo
from app.events import store as events_store
from app.events.dispatch import RuleDeps
from app.events.version import bump
from app.graph.queries import canonical as canonical_q
from app.graph.queries import kb as kb_q
from app.graph.queries import personal as personal_q
from app.schemas.common import ExamId
from app.schemas.events import Event, EventType
from app.schemas.knowledge import Prerequisite, TestDate
from app.schemas.sets import SetOut, SetsByExam
from app.sets.assemble import assemble_sets
from app.sets.forecast import forecast as forecast_fn
from app.sets.queue import build_queue

_logger = structlog.get_logger(__name__)

_REBUILD_LOCK_TTL = 10  # seconds
_ALL_EXAMS: tuple[ExamId, ...] = ("SAT_MATH", "ENT_MATH")


async def rebuild_sets(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    exam_id: ExamId,
) -> SetsByExam:
    """Rebuild the whole plan for one exam and return SetsByExam.

    Soft-fails when graph is unavailable (returns empty SetsByExam).
    Locks on `rebuild:{sid}` for 10 s: a nested call during another rebuild
    is a no-op returning the current state from Postgres.
    """
    if deps.graph is None:
        _logger.warning("rebuild_sets_graph_unavailable", student_id=str(student_id))
        return await _empty_sets_by_exam(session, student_id, exam_id)

    lock_key = f"rebuild:{student_id}"
    got_lock = await _try_lock(deps, lock_key)
    if not got_lock:
        _logger.info("rebuild_sets_skipped_locked", student_id=str(student_id))
        return await _current_sets_by_exam(session, student_id, exam_id)

    try:
        result = await _rebuild_sets_locked(session, deps, student_id, exam_id)
        await bump(deps.redis, student_id)
        return result
    except (ServiceUnavailable, SessionExpired):
        _logger.warning(
            "rebuild_sets_graph_service_unavailable", student_id=str(student_id)
        )
        return await _empty_sets_by_exam(session, student_id, exam_id)
    finally:
        await _release_lock(deps, lock_key)


async def open_set(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, set_id: UUID
) -> SetOut:
    """Mark set as current; demote the previous current to upcoming (unless done).

    Raises NotFound if the set does not belong to the student.
    """
    target = await sets_repo.get_set(session, student_id, set_id)
    if target is None:
        from app.errors import NotFound

        raise NotFound("set not found")

    for s in await sets_repo.list_sets(session, student_id, target.exam_id):
        if s.status == "current" and s.id != set_id:
            await sets_repo.set_status(session, student_id, s.id, "upcoming")

    await sets_repo.set_status(session, student_id, set_id, "current")
    updated = await sets_repo.get_set(session, student_id, set_id)
    assert updated is not None
    return updated


async def on_program_change(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> None:
    """program.saved / program.removed → rebuild both exams (cheap, safe)."""
    if event.type not in (EventType.program_saved, EventType.program_removed):
        return
    for exam_id in _ALL_EXAMS:
        await rebuild_sets(session, deps, event.student_id, exam_id)


async def on_set_change(session: AsyncSession, event: Event, deps: RuleDeps) -> None:
    """set.switched_by_user / set.deadline_changed → rebuild that exam."""
    if event.type not in (
        EventType.set_switched_by_user,
        EventType.set_deadline_changed,
    ):
        return
    exam_id: ExamId = event.exam_id or "SAT_MATH"
    await rebuild_sets(session, deps, event.student_id, exam_id)


async def on_run_completed(session: AsyncSession, event: Event, deps: RuleDeps) -> None:
    """diagnostic.completed / mock.completed → rebuild that exam."""
    if event.type not in (EventType.diagnostic_completed, EventType.mock_completed):
        return
    exam_id: ExamId = event.exam_id or "SAT_MATH"
    await rebuild_sets(session, deps, event.student_id, exam_id)


# --- internals ---


async def _rebuild_sets_locked(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    exam_id: ExamId,
) -> SetsByExam:
    today = deps.now().date()

    # 1. Skill weights
    skill_weights = await canonical_q.list_exam_skills(deps.graph, exam_id)  # type: ignore[arg-type]

    # 2. Prerequisites (one level deep)
    prereqs: list[Prerequisite] = []
    seen_prereqs: set[str] = set()
    for sw in skill_weights:
        subs = await canonical_q.get_prerequisites(deps.graph, sw.skill.id, depth=1)  # type: ignore[arg-type]
        for p in subs:
            key = f"{p.skill_id}:{p.depth}"
            if key in seen_prereqs:
                continue
            seen_prereqs.add(key)
            prereqs.append(p)

    # 3. States + misc states + roots
    states = await personal_q.get_states(deps.graph, student_id, exam_id)  # type: ignore[arg-type]
    skill_ids = [sw.skill.id for sw in skill_weights]
    misc_states = await personal_q.get_misc_states(deps.graph, student_id, skill_ids)  # type: ignore[arg-type]
    root_causes = await personal_q.list_root_causes(
        deps.graph,
        student_id,
        deps.params.root_window_days,  # type: ignore[arg-type]
    )

    # 4. Profile: hours_per_week
    profile = await profiles_repo.get_profile(session, student_id)
    hours_per_week = profile.questionnaire.pace.hours_per_week.value or 5

    # 5. Test dates
    test_dates: list[TestDate] = await kb_q.list_test_dates(deps.graph, exam_id)  # type: ignore[arg-type]
    future_dates = sorted(d.date for d in test_dates if d.date >= today)
    next_test_date: date | None = future_dates[0] if future_dates else None
    days_to_test = (next_test_date - today).days if next_test_date else 365

    # 6. Exam format (for forecast scaled)
    exam_format = await canonical_q.get_exam_format(deps.graph, exam_id)  # type: ignore[arg-type]

    # 7. Effort map
    effort = {sw.skill.id: sw.skill.effort_h for sw in skill_weights}

    # 8. p_target — из целей сохранённых программ (roadmap.requirements, B2);
    # без программ и формата экзамена остаётся params.p_target_max
    p_target = await p_target_for(
        session, deps, student_id, exam_id, exam_format=exam_format
    )

    # 9. Current set (keep it during rebuild)
    existing_sets = await sets_repo.list_sets(session, student_id, exam_id)
    current = next((s for s in existing_sets if s.status == "current"), None)
    done_skill_ids = {
        t.skill_id for s in existing_sets if s.status == "done" for t in s.topics
    }

    # 10. Queue
    queue = build_queue(
        states=states,
        skill_weights=skill_weights,
        prerequisites=prereqs,
        days_to_test=days_to_test,
        p_target=p_target,
        root_causes=root_causes,
        params=deps.params,
    )

    # 11. Assemble
    plans = assemble_sets(
        queue=queue,
        effort=effort,
        hours_per_week=hours_per_week,
        next_test_date=next_test_date,
        misc_states=misc_states,
        current=current,
        done_skill_ids=done_skill_ids,
        params=deps.params,
        today=today,
    )

    # 12. Persist
    if plans:
        await sets_repo.replace_plan(
            session, student_id, exam_id, plans, keep_current=True
        )

    # 13. Forecast
    if exam_format is not None:
        forecast_out = forecast_fn(
            states=states,
            skill_weights=skill_weights,
            exam_format=exam_format,
            p_target=p_target,
            hours_per_week=hours_per_week,
            test_date=next_test_date,
            effort=effort,
            params=deps.params,
            now=today,
        )
        await forecast_repo.put(
            session,
            student_id,
            exam_id,
            forecast_out,
            as_of_event_id=await events_store.last_event_id(session, student_id),
        )
    else:
        forecast_out = None

    # 14. Return SetsByExam from fresh state
    refreshed = await sets_repo.list_sets(session, student_id, exam_id)
    by_status: dict[str, list[SetOut]] = {"current": [], "upcoming": [], "done": []}
    for s in refreshed:
        by_status[s.status].append(s)

    return SetsByExam(
        exam_id=exam_id,
        forecast=forecast_out,
        current=by_status["current"][0] if by_status["current"] else None,
        upcoming=by_status["upcoming"],
        done=by_status["done"],
    )


async def _empty_sets_by_exam(
    session: AsyncSession, student_id: UUID, exam_id: ExamId
) -> SetsByExam:
    existing = await sets_repo.list_sets(session, student_id, exam_id)
    by_status: dict[str, list[SetOut]] = {"current": [], "upcoming": [], "done": []}
    for s in existing:
        by_status[s.status].append(s)
    return SetsByExam(
        exam_id=exam_id,
        forecast=await forecast_repo.get(session, student_id, exam_id),
        current=by_status["current"][0] if by_status["current"] else None,
        upcoming=by_status["upcoming"],
        done=by_status["done"],
    )


async def _current_sets_by_exam(
    session: AsyncSession, student_id: UUID, exam_id: ExamId
) -> SetsByExam:
    return await _empty_sets_by_exam(session, student_id, exam_id)


async def _try_lock(deps: RuleDeps, key: str) -> bool:
    try:
        return bool(await deps.redis.set(key, "1", ex=_REBUILD_LOCK_TTL, nx=True))
    except Exception:  # noqa: BLE001
        # если Redis недоступен — не блокируемся
        return True


async def _release_lock(deps: RuleDeps, key: str) -> None:
    try:
        await deps.redis.delete(key)
    except Exception:  # noqa: BLE001
        pass
