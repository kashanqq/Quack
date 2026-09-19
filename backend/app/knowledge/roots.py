"""Root-cause rules — memory-architecture-quack.md §6, §10.1.

Pure functions, no I/O. Sources of ROOT_CAUSE: diagnostic (0.8), observer (0.6),
rule (0.4). This module owns the rule source and the boost used by the queue.

Source: 20-B1-phase2.md §2.3.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.config import KnowledgeParams
from app.schemas.knowledge import (
    KnowledgeStateOut,
    Prerequisite,
    RootCauseOut,
)

_WEAK_P_THRESHOLD = 0.5
_WEAK_CONF_THRESHOLD = 0.5
_RULE_CONFIDENCE = 0.4
_DIAGNOSTIC_CONFIDENCE = 0.8


def rule_root(
    error_skill_id: str,
    prereq_states: list[tuple[Prerequisite, KnowledgeStateOut | None]],
    params: KnowledgeParams,
) -> RootCauseOut | None:
    """When an error is on a skill whose prerequisite is weak, point the root there.

    Condition: prerequisite p < 0.5 and confidence > 0.5. Among several, pick
    the one with the largest `strength`. Confidence 0.4, source 'rule'.

    Returns:
        RootCauseOut or None if no prerequisite meets the condition.
    """
    candidates: list[tuple[float, str]] = []
    for prereq, state in prereq_states:
        if state is None:
            continue
        if state.p_recall >= _WEAK_P_THRESHOLD:
            continue
        if state.confidence <= _WEAK_CONF_THRESHOLD:
            continue
        candidates.append((prereq.strength, prereq.skill_id))

    if not candidates:
        return None

    # наибольшая strength
    _, root_skill_id = max(candidates, key=lambda x: x[0])

    return RootCauseOut(
        from_skill_id=error_skill_id,
        root_skill_id=root_skill_id,
        confidence=_RULE_CONFIDENCE,
        source="rule",
        created_at=datetime.now().astimezone(),
    )


def diagnostic_root(error_skill_id: str, prereq_skill_id: str) -> RootCauseOut:
    """Root found by the diagnostic descent. Confidence 0.8, source 'diagnostic'."""
    return RootCauseOut(
        from_skill_id=error_skill_id,
        root_skill_id=prereq_skill_id,
        confidence=_DIAGNOSTIC_CONFIDENCE,
        source="diagnostic",
        created_at=datetime.now().astimezone(),
    )


def root_boost_skills(
    root_causes: list[RootCauseOut],
    params: KnowledgeParams,
    now: datetime,
) -> set[str]:
    """Skills that roots point to within root_window_days with Σ confidence ≥ 1.0.

    Used by sets.queue to boost need of skills that are roots of recent errors.
    """
    cutoff = now - timedelta(days=params.root_window_days)
    totals: dict[str, float] = {}

    for root in root_causes:
        if root.created_at < cutoff:
            continue
        totals[root.root_skill_id] = (
            totals.get(root.root_skill_id, 0.0) + root.confidence
        )

    return {sid for sid, total in totals.items() if total >= 1.0}
