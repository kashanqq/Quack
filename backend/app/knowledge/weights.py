"""Tiers and weights for evidence — memory-architecture-quack.md §4.3, §8.1.

Pure functions, no I/O. All numbers from §4.3 table.
"""

from __future__ import annotations

from app.config import KnowledgeParams
from app.schemas.knowledge import Tier

_CHAT_TIER_2_KINDS = {"solution_step", "task_in_chat", "avoided_trap"}

_BASE_WEIGHTS: dict[tuple[str, str | None, str | None], float] = {
    ("mock", "mock_set", None): 1.0,
    ("mock", "mock_topic", None): 1.0,
    ("mock", "mock_misconception", None): 1.0,
    ("diagnostic", "diagnostic", None): 1.0,
    ("task", "topic", None): 0.8,
    ("chat", "chat", "task_in_chat"): 0.8,
    ("chat", "chat", "solution_step"): 0.7,
    ("chat", "chat", "avoided_trap"): 0.7,
    ("chat", "chat", "confusion"): 0.6,
    ("chat", "chat", "applied"): 0.5,
    ("chat", "chat", "question"): 0.2,
    ("self_report", None, None): 0.1,
    ("task", "topic", "skipped"): 0.0,
    ("task", "topic", "timed_out"): 0.0,
}


def tier_for(source: str, mode: str | None, kind: str | None = None) -> Tier:
    """Tier 1 — mock/diagnostic; tier 2 — task, chat with a real solution;
    tier 3 — everything else in chat, self_report.
    """
    if source in ("mock", "diagnostic"):
        return 1
    if source == "task":
        return 2
    if source == "chat":
        if kind in _CHAT_TIER_2_KINDS:
            return 2
        return 3
    return 3


def base_weight(source: str, mode: str | None, kind: str | None) -> float:
    """Base weight from the §4.3 table. Falls back to 0.0 for unknown combos."""
    key = (source, mode, kind)
    if key in _BASE_WEIGHTS:
        return _BASE_WEIGHTS[key]
    key_no_kind = (source, mode, None)
    if key_no_kind in _BASE_WEIGHTS:
        return _BASE_WEIGHTS[key_no_kind]
    return 0.0


def evidence_weight(
    source: str,
    mode: str | None,
    kind: str | None,
    *,
    seen_before: bool,
    matched: bool,
    params: KnowledgeParams | None = None,
) -> float:
    """base * seen_template_factor (if repeated) * unmatched factor."""
    if params is None:
        from app.config import settings

        params = settings.KNOWLEDGE

    w = base_weight(source, mode, kind)
    if seen_before:
        w *= params.seen_template_factor
    if not matched:
        w *= params.unmatched_incorrect_factor
    return w


def is_strong(tier: Tier) -> bool:
    """Tiers 1 and 2 count as strong evidence; tier 3 does not."""
    return tier in (1, 2)
