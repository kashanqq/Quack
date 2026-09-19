"""B1 profile-updated apply — memory-architecture §4.8, product-logic §6.1.

I/O wrapper: при изменении ключевых полей профиля пересобирает сеты
для всех экзаменов, где у ученика есть сохранённые программы.

Приоры из анкеты (self_assessment, пробный балл) идут через
`knowledge.reconcile.reconcile_prior` (§4.8): слабое свидетельство
(tier 3, вес 0.1) и стартовое состояние для навыков, о которых пока нет
ничего сильнее.

Source: 00-contracts-phase2.md §7.2, 20-B1-phase2.md §7.
"""

from __future__ import annotations

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app.apply.sets import rebuild_sets
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical as canonical_q
from app.graph.queries import personal as personal_q
from app.knowledge.reconcile import reconcile_prior
from app.schemas.common import ExamId
from app.schemas.events import Event, EventType

_logger = structlog.get_logger(__name__)

# Поля профиля, при изменении которых пересобираем сеты
_REBUILD_PATHS: set[str] = {
    "pace.hours_per_week",
    "academics.sat_date",
    "academics.sat_target",
    "academics.ent_trial_score",
    "academics.sat_score",
    "academics.ielts_score",
    "academics.self_assessment",
    "preferences.countries",
    "preferences.budget_per_year",
    "preferences.grant_need",
    "direction.field",
}

_EXAMS: tuple[ExamId, ...] = ("SAT_MATH", "ENT_MATH")

# Поля, из которых §4.8 делает приоры знаний
_PRIOR_PATHS: set[str] = {
    "academics.self_assessment",
    "academics.ent_trial_score",
    "academics.sat_score",
}


async def apply_profile_updated(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> None:
    """При изменении ключевых полей профиля — пересобрать сеты всех экзаменов."""
    if event.type != EventType.profile_updated:
        return

    payload = event.payload or {}
    field = payload.get("field", "")
    if field not in _REBUILD_PATHS:
        # Не ключевое поле — ничего не делаем, но и не падаем
        _logger.debug(
            "profile_updated_ignored",
            student_id=str(event.student_id),
            field=field,
        )
        return

    if field in _PRIOR_PATHS:
        await _write_priors(event, deps, field, payload.get("value"))

    for exam_id in _EXAMS:
        try:
            await rebuild_sets(session, deps, event.student_id, exam_id)
        except NotImplementedError:
            _logger.info(
                "rebuild_sets_skipped_phase2",
                student_id=str(event.student_id),
                exam_id=exam_id,
            )
        except Exception:  # noqa: BLE001
            _logger.exception(
                "rebuild_sets_failed",
                student_id=str(event.student_id),
                exam_id=exam_id,
                field=field,
            )


async def _write_priors(
    event: Event, deps: RuleDeps, field: str, value: object
) -> None:
    """Приоры §4.8: слабое свидетельство + стартовое состояние по анкете.

    Пишем только навыкам, у которых ещё нет уверенного состояния — это
    решает сама `reconcile_prior`. Граф недоступен — молча пропускаем:
    анкета уже сохранена, а приор не критичен.
    """
    if deps.graph is None:
        return
    now = deps.now()
    try:
        for exam_index, exam_id in enumerate(_EXAMS):
            skill_weights = await canonical_q.list_exam_skills(deps.graph, exam_id)
            if not skill_weights:
                continue
            areas = await canonical_q.list_areas(deps.graph, exam_id)
            states = {
                state.skill_id: state
                for state in await personal_q.get_states(
                    deps.graph, event.student_id, exam_id
                )
            }
            pairs = reconcile_prior(
                field, value, skill_weights, areas, states, deps.params, now
            )
            for evidence, state in pairs:
                # Один навык может входить в оба экзамена: ordinal по экзамену
                # разводит два приора одного события по разным узлам.
                stamped = evidence.model_copy(
                    update={"event_id": event.id, "ordinal": exam_index}
                )
                await personal_q.merge_evidence(deps.graph, event.student_id, stamped)
                await personal_q.upsert_state(
                    deps.graph, event.student_id, state, source_event_id=event.id
                )
    except (ServiceUnavailable, SessionExpired):
        _logger.warning(
            "profile_priors_graph_unavailable", student_id=str(event.student_id)
        )
