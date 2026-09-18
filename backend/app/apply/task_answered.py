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

from app.apply.targets import p_target_for
from app.db.repo import tasks as tasks_repo
from app.events.dispatch import RuleDeps
from app.events.version import bump
from app.events.version import get as version_get
from app.graph.queries import canonical as canonical_q
from app.graph.queries import personal as personal_q
from app.knowledge import reconcile
from app.schemas.common import ExamId
from app.schemas.events import Event, EventType, TaskAnsweredPayload
from app.schemas.tasks import AnswerResult, Grade

_logger = structlog.get_logger(__name__)


async def apply_task_answered(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> AnswerResult:
    """Steps 2–11 of §8.2 for one task.answered event.

    Step 1 (write event) and the transaction are handled by events.store.dispatch.
    """
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
            instance, grade_fn(instance, payload.answer), deps
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

    # 3. собрать входы (граф)
    if deps.graph is None:
        _logger.warning("graph_unavailable_task_answered", event_id=event.id)
        # Событие не processed, роутер отдаст результат без состояния
        return _answer_result_without_state(instance, grade, deps)

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

    except (ServiceUnavailable, SessionExpired):
        _logger.warning("graph_service_unavailable_task_answered", event_id=event.id)
        return _answer_result_without_state(instance, grade, deps)

    # 9. seen
    await tasks_repo.bump_seen(session, event.student_id, instance.template_id)

    # 9b. mark answered
    await tasks_repo.mark_answered(
        session, payload.instance_id, deps.now(), correct=grade.correct
    )

    # 10. rebuild sets (best-effort — repo.sets может быть ещё стабом)
    try:
        from app.apply.sets import rebuild_sets

        await rebuild_sets(session, deps, event.student_id, instance.exam_id)
    except NotImplementedError:
        _logger.info("rebuild_sets_skipped_phase2_repo_not_ready", event_id=event.id)

    # 11. bump version
    version = await bump(deps.redis, event.student_id)

    return AnswerResult(
        grade=grade,
        solution=instance.solution_rendered,
        state_after=result.state_after,
        misconception_change=result.misconception_change,
        state_words=result.words,
        knowledge_version=version,
    )


async def apply_task_skipped(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> None:
    """Task skipped / timed out — log only, no state change (§8.2)."""
    if event.type not in (EventType.task_skipped, EventType.task_timed_out):
        return
    _logger.info("task_skipped", event_id=event.id, type=event.type.value)


def _answer_result_without_state(
    instance: Any, grade: Grade, deps: RuleDeps
) -> AnswerResult:
    return AnswerResult(
        grade=grade,
        solution=instance.solution_rendered,
        state_after=None,
        misconception_change=None,
        state_words="",
        knowledge_version=0,
    )
