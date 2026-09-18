"""B1 knowledge read-models — memory-architecture §4.5, §5.2, §10.5.

Read-only views: skill states, misconception states, evidence for one node.
No mutations. Soft-fail when graph is unavailable (empty lists).

Source: 00-contracts-phase2.md §7.2, 20-B1-phase2.md §7.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app.apply.targets import p_target_for
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical as canonical_q
from app.graph.queries import personal as personal_q
from app.knowledge import words
from app.knowledge.hlr import due_at as hlr_due_at
from app.knowledge.misconceptions import visible_to
from app.knowledge.roots import root_boost_skills
from app.schemas.common import ExamId
from app.schemas.knowledge import (
    EvidenceOut,
    MisconceptionStateOut,
    SkillStateView,
)

_logger = structlog.get_logger(__name__)


async def states_view(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, exam_id: ExamId
) -> list[SkillStateView]:
    """One SkillStateView per skill in the exam map, enriched with state + roots."""
    if deps.graph is None:
        _logger.warning("states_view_graph_unavailable", student_id=str(student_id))
        return []

    try:
        skill_weights = await canonical_q.list_exam_skills(deps.graph, exam_id)
        states = await personal_q.get_states(deps.graph, student_id, exam_id)
        root_causes = await personal_q.list_root_causes(
            deps.graph, student_id, deps.params.root_window_days
        )
    except (ServiceUnavailable, SessionExpired):
        _logger.warning(
            "states_view_graph_service_unavailable", student_id=str(student_id)
        )
        return []

    state_by_skill = {s.skill_id: s for s in states}
    root_ids = root_boost_skills(root_causes, deps.params, deps.now())

    # Целевой балл — из сохранённых программ (roadmap.requirements, B2)
    p_target = await p_target_for(session, deps, student_id, exam_id)

    out: list[SkillStateView] = []
    for sw in skill_weights:
        sid = sw.skill.id
        state = state_by_skill.get(sid)

        # История нужна для trend — обойдёмся только текущим, если нет истории
        history = await _history(deps, student_id, sid, exam_id)

        if state is not None:
            p_recall = state.p_recall
            confidence = state.confidence
            n_evidence = state.n_correct + state.n_incorrect + state.n_partial
            last_obs = state.last_observed_at
            h = state.half_life_h
            due = hlr_due_at(last_obs, h, p_target) if h > 0 else None
        else:
            p_recall = 0.5
            confidence = 0.0
            n_evidence = 0
            due = None

        level = words.skill_level(state, p_target, deps.params)
        trend = words.trend(history) if history else "flat"

        out.append(
            SkillStateView(
                skill_id=sid,
                name=sw.skill.name,
                area_id=sw.area_id,
                exam_id=exam_id,
                weight=sw.weight,
                p_target=p_target,
                level=level,
                p_recall=p_recall,
                confidence=confidence,
                trend=trend,
                due_at=due,
                is_root=sid in root_ids,
                n_evidence=n_evidence,
            )
        )
    return out


async def misconceptions_view(
    deps: RuleDeps, student_id: UUID, exam_id: ExamId
) -> list[MisconceptionStateOut]:
    """Visible-for-student misconception states across the exam's skills."""
    if deps.graph is None:
        return []
    try:
        skill_weights = await canonical_q.list_exam_skills(deps.graph, exam_id)
        skill_ids = [sw.skill.id for sw in skill_weights]
        states = await personal_q.get_misc_states(deps.graph, student_id, skill_ids)
    except (ServiceUnavailable, SessionExpired):
        return []

    now = deps.now()
    visible: list[MisconceptionStateOut] = []
    for s in states:
        if visible_to(s, "student", deps.params, now):
            visible.append(s)
    return visible


async def explain(deps: RuleDeps, student_id: UUID, node_id: str) -> list[EvidenceOut]:
    """All Evidence for a node (skill_id or misconception_id)."""
    if deps.graph is None:
        return []

    # Если node_id — заблуждение, то нужно собрать evidence по его навыкам
    if node_id.startswith(("lib.", "pers.")):
        try:
            skill_ids = await _skills_for_misconception(deps, student_id, node_id)
        except (ServiceUnavailable, SessionExpired):
            return []
        out: list[EvidenceOut] = []
        for sid in skill_ids:
            try:
                items = await personal_q.list_evidence(
                    deps.graph, student_id, sid, limit=50
                )
            except (ServiceUnavailable, SessionExpired):
                continue
            out.extend(items)
        return out

    try:
        return await personal_q.list_evidence(deps.graph, student_id, node_id, limit=50)
    except (ServiceUnavailable, SessionExpired):
        return []


# --- helpers ---


async def _history(
    deps: RuleDeps, student_id: UUID, skill_id: str, exam_id: ExamId
) -> list:
    if deps.graph is None:
        return []
    try:
        return await personal_q.get_state_history(
            deps.graph, student_id, skill_id, exam_id, n=3
        )
    except (ServiceUnavailable, SessionExpired):
        return []


async def _skills_for_misconception(
    deps: RuleDeps, student_id: UUID, misconception_id: str
) -> list[str]:
    """Find which skills a misconception is ABOUT.

    Personal miscons live under canonical parents; library ones are canon.
    """
    # Собираем все состояния заблуждений ученика, ищем нужный,
    # и берём его skill_ids.
    for exam_id in ("SAT_MATH", "ENT_MATH"):
        try:
            skill_weights = await canonical_q.list_exam_skills(deps.graph, exam_id)
        except (ServiceUnavailable, SessionExpired):
            return []
        skill_ids = [sw.skill.id for sw in skill_weights]
        try:
            states = await personal_q.get_misc_states(deps.graph, student_id, skill_ids)
        except (ServiceUnavailable, SessionExpired):
            return []
        for s in states:
            if s.misconception_id == misconception_id:
                return list(s.skill_ids)
    return []
