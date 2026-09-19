"""B1 task answer apply — memory-architecture §8.2, 11 steps.

I/O layer: reads instance, state, prerequisites, misconception states;
calls the pure reconcile function; writes back to graph and Postgres.

Source: 00-contracts-phase2.md §7.2, 20-B1-phase2.md §7.
"""

from __future__ import annotations

from typing import Any

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app.apply._lock import student_lock
from app.apply.targets import p_target_for
from app.db.repo import tasks as tasks_repo
from app.events.dispatch import RuleDeps
from app.events.version import bump
from app.events.version import get as version_get
from app.graph.queries import applied as applied_q
from app.graph.queries import canonical as canonical_q
from app.graph.queries import personal as personal_q
from app.knowledge import reconcile, words
from app.schemas.common import ExamId
from app.schemas.events import Event, EventType, TaskAnsweredPayload
from app.schemas.tasks import AnswerResult, Grade

_logger = structlog.get_logger(__name__)

#: Name of this handler in `AppliedEvent` (D02). Never renamed casually — an
#: old marker under a different name would read as "not applied".
HANDLER = "apply_task_answered"


async def apply_task_answered(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> AnswerResult:
    """Steps 2–11 of §8.2 for one task.answered event.

    Step 1 (write event) and the transaction are handled by events.store.dispatch.
    Runs under the student's write lock (phase3 F9): the observer rule writes
    the same skill states from its job.
    """
    async with student_lock(deps.redis, event.student_id) as got_lock:
        return await _apply_task_answered(session, event, deps, got_lock)


async def _apply_task_answered(
    session: AsyncSession, event: Event, deps: RuleDeps, got_lock: bool = True
) -> AnswerResult:
    payload = TaskAnsweredPayload.model_validate(event.payload)
    instance = await tasks_repo.get_instance(
        session, event.student_id, payload.instance_id
    )
    if instance is not None and await tasks_repo.get_answered_at(
        session, payload.instance_id
    ):
        # Повторный dispatch того же события (или второй ответ на тот же
        # экземпляр): счётчики уже учтены — пересчитывать нечего. Граф тоже
        # идемпотентен (ключи свидетельств и source_event_id состояния), но
        # `bump_seen` и `mark_answered` — нет, поэтому выходим здесь.
        from app.tasks.answer import grade as grade_fn

        _logger.info("task_answered_replay", event_id=event.id)
        result = _answer_result_without_state(
            instance, grade_fn(instance, payload.answer), deps, projection="applied"
        )
        return result.model_copy(
            update={
                "knowledge_version": await version_get(deps.redis, event.student_id)
            }
        )
    if instance is None:
        # Чужой экземпляр / не найден — не падаем, но и работать не с чем.
        _logger.warning("task_instance_not_found", event_id=event.id)
        return AnswerResult(
            grade=Grade(correct=False),
            solution=[],
            state_after=None,
            misconception_change=None,
            state_words="",
            knowledge_version=0,
        )

    # 2. grade
    from app.tasks.answer import grade as grade_fn

    grade = grade_fn(instance, payload.answer)

    # 2a. D10: without the student lock this read-modify-write can interleave
    # with the observer writing the same skill states, and one of the two
    # updates is silently lost. Phase 4 treated an unavailable lock as "go
    # ahead"; phase 5 fails closed — the answer and its grade are already
    # durable, the projection is owed, and `recover_graph_events` does it
    # later under a real lock.
    if not got_lock and deps.graph is not None:
        _logger.warning("task_answered_lock_unavailable", event_id=event.id)
        return _answer_result_without_state(instance, grade, deps)

    # 3. собрать входы (граф)
    if deps.graph is None:
        _logger.warning("graph_unavailable_task_answered", event_id=event.id)
        # Событие не processed, роутер отдаст результат без состояния
        return _answer_result_without_state(instance, grade, deps)

    # 3a. Фаза 5 (D02): проекция этого события уже завершилась, а SQL-часть —
    # нет (падение между коммитом Neo4j и `mark_answered`). Повторять
    # графовые записи незачем: достраиваем только недостающее в Postgres.
    try:
        already = await applied_q.is_applied(
            deps.graph, event.student_id, event.id, HANDLER
        )
    except (ServiceUnavailable, SessionExpired):
        _logger.warning("graph_service_unavailable_task_answered", event_id=event.id)
        return _answer_result_without_state(instance, grade, deps)
    if already:
        _logger.info("task_answered_graph_already_applied", event_id=event.id)
        return await _finish_sql(session, deps, event, instance, grade)

    try:
        state = await personal_q.get_state(
            deps.graph, event.student_id, instance.skill_id, instance.exam_id
        )
        prereqs = await canonical_q.get_prerequisites(
            deps.graph, instance.skill_id, depth=1
        )
        prereq_states = []
        for p in prereqs:
            s = await personal_q.get_state(
                deps.graph, event.student_id, p.skill_id, instance.exam_id
            )
            prereq_states.append((p, s))
        misc_states = await personal_q.get_misc_states(
            deps.graph, event.student_id, [instance.skill_id]
        )
        seen = await tasks_repo.get_seen(session, event.student_id, instance.skill_id)
        n_seen = seen.get(instance.template_id, 0)
        exam_ids: list[ExamId] = ["SAT_MATH", "ENT_MATH"]
        p_target = await p_target_for(session, deps, event.student_id, instance.exam_id)

        # 4. reconcile
        result = reconcile.reconcile_task_answer(
            instance,
            grade,
            payload,
            state,
            prereq_states,
            misc_states,
            n_seen,
            exam_ids,
            deps.params,
            deps.now(),
            event_id=event.id,
            p_target=p_target,
        )

        # 5. evidence ×N
        for ev in result.evidence:
            await personal_q.merge_evidence(deps.graph, event.student_id, ev)

        # 6. состояние
        await personal_q.upsert_state(
            deps.graph, event.student_id, result.state_after, source_event_id=event.id
        )
        if result.cross_exam_state is not None:
            await personal_q.upsert_state(
                deps.graph,
                event.student_id,
                result.cross_exam_state,
                source_event_id=event.id,
            )

        # 7. misconception
        if result.misconception_change is not None:
            mc = result.misconception_change
            await personal_q.upsert_misc_state(
                deps.graph,
                event.student_id,
                mc.misconception_id,
                mc.to_status,
                mc.counters,
                triggers=None,
            )

        # 8. root causes
        for root in result.root_causes:
            primary = result.evidence[0]
            await personal_q.add_root_cause(
                deps.graph,
                personal_q.evidence_id(
                    primary.event_id, primary.skill_id, primary.ordinal
                ),
                root.root_skill_id,
                root.confidence,
                root.source,
            )

        # 8b. Фаза 5 (D02): маркер пишется последним. Его наличие значит,
        # что всё выше закоммичено; его отсутствие — что можно безопасно
        # повторить, потому что каждая запись выше идемпотентна.
        await applied_q.mark_applied(deps.graph, event.student_id, event.id, HANDLER)

    except (ServiceUnavailable, SessionExpired):
        _logger.warning("graph_service_unavailable_task_answered", event_id=event.id)
        return _answer_result_without_state(instance, grade, deps)

    # 9–11. Postgres-часть и инвалидация версии.
    await _sql_after_graph(session, deps, event, instance, grade)

    return AnswerResult(
        grade=grade,
        solution=instance.solution_rendered,
        state_after=result.state_after,
        misconception_change=result.misconception_change,
        state_words=result.words,
        knowledge_version=await version_get(deps.redis, event.student_id),
    )


async def _sql_after_graph(
    session: AsyncSession, deps: RuleDeps, event: Event, instance: Any, grade: Grade
) -> None:
    """Steps 9–11: what still has to land in Postgres once the graph is done."""
    # 9. seen
    await tasks_repo.bump_seen(session, event.student_id, instance.template_id)

    # 9b. mark answered
    await tasks_repo.mark_answered(
        session, instance.id, deps.now(), correct=grade.correct
    )

    # 10. rebuild sets (best-effort — repo.sets может быть ещё стабом)
    try:
        from app.apply.sets import rebuild_sets

        await rebuild_sets(session, deps, event.student_id, instance.exam_id)
    except NotImplementedError:
        _logger.info("rebuild_sets_skipped_phase2_repo_not_ready", event_id=event.id)

    # 11. bump version
    await bump(deps.redis, event.student_id)


async def _finish_sql(
    session: AsyncSession, deps: RuleDeps, event: Event, instance: Any, grade: Grade
) -> AnswerResult:
    """The graph is already projected: rebuild only the Postgres read-model."""
    await _sql_after_graph(session, deps, event, instance, grade)
    state = await personal_q.get_state(
        deps.graph, event.student_id, instance.skill_id, instance.exam_id
    )
    p_target = await p_target_for(session, deps, event.student_id, instance.exam_id)
    return AnswerResult(
        grade=grade,
        solution=instance.solution_rendered,
        state_after=state,
        misconception_change=None,
        state_words=words.state_words(state, p_target, deps.params),
        knowledge_version=await version_get(deps.redis, event.student_id),
    )


async def apply_task_skipped(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> None:
    """Task skipped / timed out — log only, no state change (§8.2)."""
    if event.type not in (EventType.task_skipped, EventType.task_timed_out):
        return
    _logger.info("task_skipped", event_id=event.id, type=event.type.value)


def _answer_result_without_state(
    instance: Any,
    grade: Grade,
    deps: RuleDeps,
    *,
    projection: str = "pending",
) -> AnswerResult:
    """A result with no state attached — for two different reasons.

    `projection="pending"` is the outage: the graph could not be reached, the
    answer is kept and the state is owed. Phase 5 (D03) uses that flag to tell
    the client the difference between "nothing changed" and "we have not
    looked yet", and the dispatcher reads it to keep the event in the recovery
    backlog.

    `projection="applied"` is the replay of an event that was already applied.
    Nothing is owed there, and saying `pending` would park the event forever:
    every recovery pass would see it as still outstanding.

    Either way `state_words` stays empty — a level here would be a guess.
    """
    return AnswerResult(
        grade=grade,
        solution=instance.solution_rendered,
        state_after=None,
        misconception_change=None,
        state_words="",
        knowledge_version=0,
        projection_status=projection,  # type: ignore[arg-type]
    )
