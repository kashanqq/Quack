"""Target recall per exam — p_target for queue, forecast and skill views.

`p_target` навыка = `min(p_target_max, target_score / max_raw_score)`
(00-contracts-phase2.md §2, memory-architecture §4.4). `target_score` даёт
`roadmap.requirements.build_requirements` (B2): максимальный порог среди
сохранённых программ, либо ручная цель из анкеты.

Порог программы обычно назван в шкалированных баллах (SAT 700), а
`max_raw_score` — в сырых: если у формата есть таблица перевода и цель
выходит за пределы сырой шкалы, цель сперва переводится в сырые баллы
обратной интерполяцией по той же таблице, что и прогноз
(`sets.forecast._scale`). Иначе доля вышла бы > 1 и всегда упиралась в
`p_target_max`, то есть цель программы ни на что бы не влияла.

Soft-fail: нет графа, формата экзамена или сохранённых программ —
возвращаем `p_target_max`, как это делала фаза 2 до появления B2.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import KnowledgeParams  # noqa: F401  (re-exported below)
from app.db.repo import forecast as forecast_repo
from app.db.repo import profiles as profiles_repo
from app.db.repo import programs as programs_repo
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical as canonical_q
from app.graph.queries import kb as kb_q
from app.roadmap.requirements import build_requirements
from app.schemas.common import ExamId
from app.schemas.knowledge import ExamFormat
from app.sets.scale import p_target_from, raw_from_scaled

__all__ = ["p_target_for", "p_target_from", "raw_from_scaled"]

_logger = structlog.get_logger(__name__)


async def p_target_for(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    exam_id: ExamId,
    exam_format: ExamFormat | None = None,
) -> float:
    """p_target for one exam, from the student's saved programs and profile."""
    if deps.graph is None:
        return deps.params.p_target_max
    try:
        if exam_format is None:
            exam_format = await canonical_q.get_exam_format(deps.graph, exam_id)
        test_dates = await kb_q.list_test_dates(deps.graph, exam_id)
    except (ServiceUnavailable, SessionExpired):
        _logger.warning("p_target_graph_unavailable", student_id=str(student_id))
        return deps.params.p_target_max

    saved = await programs_repo.list_saved_programs(session, student_id)
    profile = await profiles_repo.get_profile(session, student_id)
    cached_forecast = await forecast_repo.get(session, student_id, exam_id)

    requirements = build_requirements(
        saved=saved,
        profile=profile,
        exam_formats={exam_id: exam_format} if exam_format is not None else {},
        test_dates={exam_id: test_dates},
        forecasts={exam_id: cached_forecast},
        params=deps.params,
    )
    requirement = next((r for r in requirements if r.exam_id == exam_id), None)
    if requirement is None:
        return deps.params.p_target_max
    return p_target_from(requirement.target_score, exam_format, deps.params)
