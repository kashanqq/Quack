"""`set.completed` → the frozen facts of the set, in the same transaction (§4).

The statistics are written synchronously and the text is a job, deliberately:
the Overview must show what happened the moment the set closes, whether or
not the model is up (product-logic §6.3).
"""

from __future__ import annotations

import hashlib
from uuid import UUID

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app.apply.sets import rebuild_sets
from app.apply.targets import p_target_for
from app.config import settings
from app.db.repo import forecast as forecast_repo
from app.db.repo import sets as sets_repo
from app.db.repo import summaries as summaries_repo
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical as canonical_q
from app.graph.queries import personal as personal_q
from app.knowledge.text_inputs import canonical_json
from app.prompt_versions import version_of
from app.schemas.events import Event, EventType
from app.schemas.knowledge import ForecastOut
from app.schemas.sets import NextSetBrief, SetOut, SetStats
from app.sets.report import ReportInputs, SkillHistory, set_stats

_logger = structlog.get_logger(__name__)

_STATE_HISTORY_DEPTH = 6


def input_hash(stats: SetStats, prompt_version: str, model: str) -> str:
    return hashlib.sha256(
        canonical_json(
            {
                "stats": stats.model_dump(mode="json"),
                "prompt_version": prompt_version,
                "model": model,
            }
        ).encode("utf-8")
    ).hexdigest()


async def on_set_completed(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> SetStats | None:
    """Rebuild the plan, freeze the facts, queue the text."""
    if event.type != EventType.set_completed:
        return None
    set_id = (event.payload or {}).get("set_id")
    if not set_id:
        return None
    set_out = await sets_repo.get_set(session, event.student_id, UUID(str(set_id)))
    if set_out is None:
        return None

    # `forecast_after` и «следующий сет» должны быть свежими: на
    # `set.completed` пересборка в фазе 2 не зарегистрирована, поэтому
    # зовём её здесь явно (§4.3).
    try:
        await rebuild_sets(session, deps, event.student_id, set_out.exam_id)
    except (ServiceUnavailable, SessionExpired):
        _logger.warning("summary_rebuild_graph_unavailable", set_id=str(set_id))

    try:
        stats = await build_stats(session, deps, event.student_id, set_out)
    except Exception:  # noqa: BLE001 — закрытие сета важнее отчёта о нём
        # §2.2: обработчик фазы 4 не имеет права уронить запрос ученика.
        _logger.warning("summary_stats_failed", set_id=str(set_id), exc_info=True)
        return None
    version = version_of("summary")
    row_hash = input_hash(stats, version, settings.MODEL_BULK)
    await summaries_repo.upsert_stats(
        session,
        event.student_id,
        set_out.id,
        set_out.exam_id,
        stats,
        input_hash=row_hash,
    )
    deps.jobs.enqueue(
        "interactive",
        "set_summary",
        job_id=f"summary:{set_out.id}",
        set_id=str(set_out.id),
        student_id=str(event.student_id),
    )
    return stats


async def build_stats(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, set_out: SetOut
) -> SetStats:
    """Collect the inputs of `sets.report.set_stats` (§4.2)."""
    progress = await sets_repo.count_progress(session, student_id, set_out.id)
    mocks = await _mocks_completed(session, student_id, set_out.id)
    p_target = await p_target_for(session, deps, student_id, set_out.exam_id)

    skills: list[SkillHistory] = []
    misconceptions = []
    if deps.graph is not None:
        try:
            skills = await _skills(session, deps, student_id, set_out)
            misconceptions = await personal_q.get_misc_states(
                deps.graph,
                student_id,
                [topic.skill_id for topic in set_out.topics],
            )
        except (ServiceUnavailable, SessionExpired):
            _logger.warning("summary_stats_graph_unavailable", set_id=str(set_out.id))

    forecast_before = await _opened_forecast(session, student_id, set_out.id)
    forecast_after = await forecast_repo.get(session, student_id, set_out.exam_id)

    upcoming = [
        item
        for item in await sets_repo.list_sets(session, student_id, set_out.exam_id)
        if item.status == "upcoming"
    ]
    next_set = None
    if upcoming:
        first = sorted(upcoming, key=lambda item: item.position)[0]
        next_set = NextSetBrief(
            set_id=first.id,
            deadline=first.deadline,
            topic_names=[topic.name for topic in first.topics],
        )

    previous = await summaries_repo.get_latest(session, student_id, set_out.exam_id)

    return set_stats(
        ReportInputs(
            set_id=set_out.id,
            exam_id=set_out.exam_id,
            kind=set_out.kind,
            opened_at=set_out.opened_at,
            completed_at=set_out.completed_at or deps.now(),
            deadline=set_out.deadline,
            tasks_answered=progress.tasks_answered,
            tasks_correct=progress.tasks_correct,
            mocks_completed=mocks,
            skills=skills,
            misconceptions=misconceptions,
            p_target=p_target,
            forecast_before=forecast_before,
            forecast_after=forecast_after,
            next_set=next_set,
            previous_summary_id=None if previous is None else previous.set_id,
        ),
        deps.params,
        deps.now(),
    )


async def _skills(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, set_out: SetOut
) -> list[SkillHistory]:
    """«До» — первое состояние после открытия сета, «после» — текущее."""
    del session
    out: list[SkillHistory] = []
    for topic in set_out.topics:
        history = await personal_q.get_state_history(
            deps.graph,
            student_id,
            topic.skill_id,
            set_out.exam_id,
            n=_STATE_HISTORY_DEPTH,
        )
        ordered = sorted(history, key=lambda state: state.created_at)
        after = ordered[-1] if ordered else None
        before = None
        if set_out.opened_at is not None:
            earlier = [
                state for state in ordered if state.created_at <= set_out.opened_at
            ]
            before = earlier[-1] if earlier else None
        elif len(ordered) > 1:
            before = ordered[0]
        ref = await canonical_q.get_skill(deps.graph, topic.skill_id)
        out.append(
            SkillHistory(
                skill_id=topic.skill_id,
                name=ref.name if ref is not None else topic.name,
                before=before,
                after=after,
                closed=topic.status == "closed",
            )
        )
    return out


async def _mocks_completed(
    session: AsyncSession, student_id: UUID, set_id: UUID
) -> int:
    from sqlalchemy import func, select

    from app.db.models import MockRun

    return int(
        await session.scalar(
            select(func.count())
            .select_from(MockRun)
            .where(
                MockRun.student_id == student_id,
                MockRun.set_id == set_id,
                MockRun.status == "completed",
            )
        )
        or 0
    )


async def _opened_forecast(
    session: AsyncSession, student_id: UUID, set_id: UUID
) -> ForecastOut | None:
    from sqlalchemy import select

    from app.db.models import Set as SetRow

    payload = await session.scalar(
        select(SetRow.opened_forecast).where(
            SetRow.id == set_id, SetRow.student_id == student_id
        )
    )
    return ForecastOut.model_validate(payload) if payload else None
