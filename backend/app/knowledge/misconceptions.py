"""Misconception status logic — memory-architecture-quack.md §5.1–5.3.

Phase 1: signatures only, bodies raise NotImplementedError.
Status transitions and trigger aggregates are phase 2.
"""

from __future__ import annotations

from app.config import KnowledgeParams
from app.schemas.knowledge import EvidenceIn, MisconceptionStatus


def next_status(
    current: MisconceptionStatus | None,
    *,
    hit: bool,
    strong: bool,
    occurrence_count: int,
    strong_count: int,
    consecutive_avoided: int,
    params: KnowledgeParams,
) -> MisconceptionStatus:
    """Phase 2: transitions from §5.1 (suspected → confirmed → resolved).

    Rules:
      None + hit (any tier) → suspected
      suspected + occurrence_count >= misc_confirm_min_occ
          and strong_count >= 1 → confirmed
      confirmed + consecutive_avoided >= misc_resolve_avoided → resolved
      resolved + new hit → confirmed (relapse)
    """
    raise NotImplementedError("phase 2")


def update_triggers(evidences: list[EvidenceIn], *, params: KnowledgeParams) -> dict:
    """Phase 2: aggregate triggers from evidence contexts (§5.3).

    Returns a dict with by_task_type, by_difficulty, hurried, late_session,
    after_guideline, by_tag, n.
    """
    raise NotImplementedError("phase 2")
