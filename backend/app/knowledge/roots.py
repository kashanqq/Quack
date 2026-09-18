"""Root-cause rules — memory-architecture-quack.md §6, §10.1.

Pure functions, no I/O. Sources of ROOT_CAUSE: diagnostic (0.8), observer (0.6),
rule (0.4). This module owns the rule source and the boost used by the queue.

Source: 20-B1-phase2.md §2.3.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.config import KnowledgeParams
from app.schemas.knowledge import KnowledgeStateOut, Prerequisite

if TYPE_CHECKING:
    # These models live in B3's phase-2 skeleton (schemas/knowledge.py).
    # Until the skeleton is merged, they exist only as forward-reference strings.
    from app.schemas.knowledge import RootCauseOut


def rule_root(
    error_skill_id: str,
    prereq_states: list[tuple[Prerequisite, KnowledgeStateOut | None]],
    params: KnowledgeParams,
) -> RootCauseOut | None:
    """When an error is on a skill whose prerequisite is weak, point the root there.

    Condition: prerequisite p < 0.5 and confidence > 0.5. Among several, pick
    the one with the largest `strength`. Confidence 0.4, source 'rule'.

    Args:
        error_skill_id: the skill where the error happened
        prereq_states: list of (Prerequisite, state-or-None) for direct prerequisites
        params: KnowledgeParams

    Returns:
        RootCauseOut or None if no prerequisite meets the condition.
    """
    raise NotImplementedError("phase 2")


def diagnostic_root(error_skill_id: str, prereq_skill_id: str) -> RootCauseOut:
    """Root found by the diagnostic descent. Confidence 0.8, source 'diagnostic'."""
    raise NotImplementedError("phase 2")


def root_boost_skills(
    root_causes: list[RootCauseOut],
    params: KnowledgeParams,
    now: datetime,
) -> set[str]:
    """Skills that roots point to within root_window_days with Σ confidence ≥ 1.0.

    Used by sets.queue to boost need of skills that are roots of recent errors.
    """
    raise NotImplementedError("phase 2")
