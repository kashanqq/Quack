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

from app.config import KnowledgeParams
from app.db.repo import forecast as forecast_repo
from app.db.repo import profiles as profiles_repo
from app.db.repo import programs as programs_repo
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical as canonical_q
from app.graph.queries import kb as kb_q
from app.roadmap.requirements import build_requirements
from app.schemas.common import ExamId
from app.schemas.knowledge import ExamFormat

_logger = structlog.get_logger(__name__)


def raw_from_scaled(scaled: float, exam_format: ExamFormat) -> float | None:
    """Inverse of `sets.forecast._scale` — scaled score back to raw points."""
    table = exam_format.scale_table
    if not table:
        return None
    points: list[tuple[float, float]] = []
    for raw_key, scaled_value in table.items():
        try:
            points.append((float(raw_key), float(scaled_value)))
        except (ValueError, TypeError):
            continue
    if len(points) < 2:
        return None
    points.sort(key=lambda point: point[1])

    if scaled <= points[0][1]:
        return points[0][0]
    if scaled >= points[-1][1]:
        return points[-1][0]
    for (raw0, scaled0), (raw1, scaled1) in zip(points, points[1:], strict=False):
        if scaled0 <= scaled <= scaled1:
            if scaled1 == scaled0:
                return raw0
            share = (scaled - scaled0) / (scaled1 - scaled0)
            return raw0 + share * (raw1 - raw0)
    return None


def p_target_from(
    target_score: float, exam_format: ExamFormat | None, params: KnowledgeParams
) -> float:
    """Turn one exam target into the recall every skill of that exam aims at."""
    if exam_format is None or exam_format.max_raw_score <= 0:
        return params.p_target_max
    raw_target = target_score
    if target_score > exam_format.max_raw_score:
        converted = raw_from_scaled(target_score, exam_format)
        if converted is None:
            return params.p_target_max
        raw_target = converted
    share = raw_target / exam_format.max_raw_score
    return max(0.0, min(params.p_target_max, share))


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
