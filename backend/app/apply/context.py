"""The tutor's topic context with its Postgres inputs — B1.

Source: docs/tz/phase3-agents.md §3.7 (`apply.context.get_topic_context`), F4.

`graph.context.build_topic_context` reads only the graph (and its Redis
cache); the set, the profile, the previous set's summary and the target
recall come from here. `None` means "no context" — a foreign or missing set,
a topic outside the set, or the graph being down — and the tutor then teaches
without a `<learner_model>` block: an incomplete block is worse than none.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app.apply.targets import p_target_for
from app.db.repo import profiles as profiles_repo
from app.db.repo import sets as sets_repo
from app.db.repo import summaries as summaries_repo
from app.events.dispatch import RuleDeps
from app.graph.context import ContextExtras, TopicContext, build_topic_context
from app.sets.report import stats_words

_logger = structlog.get_logger(__name__)


async def get_topic_context(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    set_id: UUID,
    topic_skill_id: str | None,
) -> TopicContext | None:
    set_out = await sets_repo.get_set(session, student_id, set_id)
    if set_out is None:
        return None
    if topic_skill_id is not None and topic_skill_id not in {
        topic.skill_id for topic in set_out.topics
    }:
        return None
    profile = await profiles_repo.get_profile(session, student_id)
    # Фаза 4 (§4.5): контекст не пустеет из-за недоступной модели — при
    # `failed`/`generating` слот заполняется фактами статистики словами.
    previous = await summaries_repo.get_previous(
        session, student_id, before_set_id=set_id
    )
    previous_summary = None
    if previous is not None:
        previous_summary = (
            previous.text
            if previous.status == "ready" and previous.text
            else stats_words(previous.stats)
        )
    if deps.graph is None:
        return None
    try:
        p_target = await p_target_for(session, deps, student_id, set_out.exam_id)
        return await build_topic_context(
            deps.graph,
            deps.redis,
            student_id,
            topic_skill_id,
            set_id,
            exam_id=set_out.exam_id,
            extras=ContextExtras(
                set=set_out,
                profile=profile,
                previous_summary=previous_summary,
                p_target=p_target,
            ),
            params=deps.params,
            now=deps.now(),
        )
    except (ServiceUnavailable, SessionExpired):
        _logger.warning(
            "ctx_topic", error="graph_unavailable", student_id=str(student_id)
        )
        return None
