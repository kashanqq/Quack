"""B1 profile-updated apply — memory-architecture §4.8, product-logic §6.1.

I/O wrapper: при изменении ключевых полей профиля пересобирает сеты
для всех экзаменов, где у ученика есть сохранённые программы.

Приоры из анкеты (self_assessment, пробный балл) — TODO: reconcile_prior
в knowledge/reconcile пока не реализован, оставляем для синка (см.
docs/sync-log.md).

Source: 00-contracts-phase2.md §7.2, 20-B1-phase2.md §7.
"""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.apply.sets import rebuild_sets
from app.events.dispatch import RuleDeps
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
