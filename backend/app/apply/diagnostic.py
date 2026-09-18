"""B1 diagnostic apply — memory-architecture §8.4.

I/O layer: gather inputs, call the pure state machine, issue tasks,
save state via repo.diagnostic, append diagnostic.* events.

Source: 00-contracts-phase2.md §7.2, 20-B1-phase2.md §7.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DiagnosticRun
from app.db.repo import diagnostic as diag_repo
from app.db.repo import tasks as tasks_repo
from app.errors import NotFound, ValidationFailed
from app.events import store as events_store
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical as canonical_q
from app.graph.queries import personal as personal_q
from app.knowledge import diagnostic as diag_logic
from app.schemas.common import ExamId
from app.schemas.diagnostic import (
    DiagnosticOut,
    DiagnosticResult,
    DiagnosticState,
)
from app.schemas.events import EventIn, EventType
from app.schemas.tasks import (
    AnswerResult,
    TaskInstanceOut,
    TaskRequestIn,
)

_logger = structlog.get_logger(__name__)


async def start(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    exam_id: ExamId,
    n_tasks: int | None,
) -> DiagnosticOut:
    """Build initial state, create run, issue the first task."""
    if deps.graph is None:
        raise ValidationFailed("graph unavailable")

    try:
        exam_skills = await canonical_q.list_exam_skills(deps.graph, exam_id)
        areas = await canonical_q.list_areas(deps.graph, exam_id)
    except (ServiceUnavailable, SessionExpired) as exc:
        raise ValidationFailed("graph unavailable") from exc

    if not exam_skills:
        raise NotFound("no skills for exam")

    prereqs: list = []
    seen_pairs: set[str] = set()
    for sw in exam_skills:
        try:
            subs = await canonical_q.get_prerequisites(deps.graph, sw.skill.id, depth=1)
        except (ServiceUnavailable, SessionExpired):
            subs = []
        for p in subs:
            key = f"{p.skill_id}:{p.depth}"
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            prereqs.append(p)

    try:
        known_roots = await personal_q.list_root_causes(
            deps.graph, student_id, deps.params.root_window_days
        )
    except (ServiceUnavailable, SessionExpired):
        known_roots = []

    state = diag_logic.start(
        exam_skills=exam_skills,
        areas=areas,
        prerequisites=prereqs,
        known_roots=known_roots,
        budget=n_tasks,
        params=deps.params,
    )

    row = await diag_repo.create_run(session, student_id, exam_id, state)
    run_id = row.id

    next_task = await _issue_next(session, deps, student_id, exam_id, state)

    return DiagnosticOut(
        run_id=run_id,
        status="active",
        state=state,
        next_task=next_task,
    )


async def answer(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    run_id: UUID,
    result: AnswerResult,
) -> DiagnosticOut:
    """Advance the diagnostic after an answered task."""
    row = await _get_run(session, student_id, run_id)
    state = DiagnosticState.model_validate(row.state)

    if not state.asked:
        raise ValidationFailed("no asked tasks")

    last_instance_id = state.asked[-1]
    instance = await tasks_repo.get_instance(session, student_id, last_instance_id)
    if instance is None:
        raise NotFound("instance not found")

    prereqs_for_skill: list = []
    if deps.graph is not None:
        try:
            prereqs_for_skill = await canonical_q.get_prerequisites(
                deps.graph, instance.skill_id, depth=1
            )
        except (ServiceUnavailable, SessionExpired):
            prereqs_for_skill = []

    new_state = diag_logic.apply_answer(
        state,
        instance.skill_id,
        result.grade,
        prereqs_for_skill,
        deps.params,
    )

    await _persist_indirect(deps, student_id, instance.exam_id, new_state)

    await events_store.append(
        session,
        deps.redis,
        EventIn(
            type=EventType.diagnostic_progress,
            payload={"run_id": str(run_id)},
            student_id=student_id,
            exam_id=instance.exam_id,
            set_id=None,
            topic_skill_id=instance.skill_id,
            chat_id=None,
            occurred_at=None,
            extractor_version=None,
            source_event_ids=None,
        ),
    )

    await diag_repo.save_state(session, student_id, run_id, new_state)

    next_task = await _issue_next(
        session, deps, student_id, instance.exam_id, new_state
    )

    return DiagnosticOut(
        run_id=run_id,
        status="active",
        state=new_state,
        next_task=next_task,
    )


async def finish(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, run_id: UUID
) -> DiagnosticResult:
    """Finalize: compute result, persist, complete the run, emit event."""
    row = await _get_run(session, student_id, run_id)
    state = DiagnosticState.model_validate(row.state)

    states_map: dict = {}
    if deps.graph is not None:
        try:
            state_list = await personal_q.get_states(
                deps.graph, student_id, state.exam_id
            )
            states_map = {s.skill_id: s for s in state_list}
        except (ServiceUnavailable, SessionExpired):
            pass

    result = diag_logic.finish(state, states_map, deps.params)

    await events_store.append(
        session,
        deps.redis,
        EventIn(
            type=EventType.diagnostic_completed,
            payload={"run_id": str(run_id)},
            student_id=student_id,
            exam_id=state.exam_id,
            set_id=None,
            topic_skill_id=None,
            chat_id=None,
            occurred_at=None,
            extractor_version=None,
            source_event_ids=None,
        ),
    )

    await diag_repo.complete_run(session, student_id, run_id, result)
    return result


# --- helpers ---


async def _get_run(session: AsyncSession, student_id: UUID, run_id: UUID):
    """Read a student-owned diagnostic run.

    B3's repo.diagnostic.py only exposes get_active_run — we add a local
    helper (see docs/sync-log.md request to add get_run).
    """
    row = await session.get(DiagnosticRun, run_id)
    if row is None or row.student_id != student_id:
        raise NotFound("diagnostic run not found")
    return row


async def _issue_next(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    exam_id: ExamId,
    state: DiagnosticState,
) -> TaskInstanceOut | None:
    """Найти следующий навык и выдать задачу; None если замер завершён."""
    prereqs: list = []
    if deps.graph is not None:
        try:
            weights = await canonical_q.list_exam_skills(deps.graph, exam_id)
            for sw in weights:
                subs = await canonical_q.get_prerequisites(
                    deps.graph, sw.skill.id, depth=1
                )
                prereqs.extend(subs)
        except (ServiceUnavailable, SessionExpired):
            pass

    skill_id = diag_logic.next_skill(state, prereqs, deps.params)
    if skill_id is None:
        return None

    from app.apply import tasks as apply_tasks

    req = TaskRequestIn(
        skill_id=skill_id,
        set_id=None,
        mode="diagnostic",
        with_trap=None,
        exclude_seen=False,
    )
    try:
        return await apply_tasks.issue(session, deps, student_id, req)
    except (NotFound, ValidationFailed):
        return None


async def _persist_indirect(
    deps: RuleDeps,
    student_id: UUID,
    exam_id: ExamId,
    state: DiagnosticState,
) -> None:
    """Записать косвенные свидетельства предпосылкам (kind='indirect')."""
    if deps.graph is None or not state.indirect:
        return
    from app.schemas.knowledge import EvidenceContext, EvidenceIn

    for skill_id, weight in state.indirect[-5:]:
        ev = EvidenceIn(
            event_id=0,
            skill_id=skill_id,
            exam_id=exam_id,
            kind="indirect",
            tier=3,  # type: ignore[arg-type]
            source="diagnostic",
            weight=weight,
            direction=1,  # type: ignore[arg-type]
            share=None,
            difficulty_factor=1.0,
            summary="indirect via prerequisite",
            context=EvidenceContext(),
            observed_at=deps.now(),
            extractor_version=None,
        )
        try:
            await personal_q.merge_evidence(deps.graph, student_id, ev)
        except (ServiceUnavailable, SessionExpired):
            return
