"""Human-facing words for skill states — memory-architecture §4.5, §4.7.

Pure functions, no I/O. Thresholds from KnowledgeParams.
Source: 00-contracts-phase2.md §4.3.
"""

from __future__ import annotations

from typing import Literal

from app.config import KnowledgeParams
from app.schemas.knowledge import KnowledgeStateOut

# Temporary: SkillLevel is B3's zone (schemas/common.py, phase 2 skeleton).
# When the skeleton is merged, replace with `from app.schemas.common import SkillLevel`.
SkillLevel = Literal["low_data", "weak", "shaky", "solid", "closed"]


def skill_level(
    state: KnowledgeStateOut | None,
    p_target: float,
    params: KnowledgeParams,
) -> SkillLevel:
    """One word per state, same thresholds everywhere.

    - no state or confidence < c_vis → low_data
    - p_recall < 0.5 → weak
    - p_recall < p_target → shaky
    - p_recall >= p_target and confidence >= c_close → closed
    - otherwise → solid
    """
    if state is None or state.confidence < params.c_vis:
        return "low_data"
    if state.p_recall < 0.5:
        return "weak"
    if state.p_recall < p_target:
        return "shaky"
    if state.confidence >= params.c_close:
        return "closed"
    return "solid"


def trend(states: list[KnowledgeStateOut]) -> str:
    """Direction of the last 3 states: 'up' | 'flat' | 'down'.

    Compares p_at_obs of the newest to the oldest. Fewer than 2 states — 'flat'.
    """
    if len(states) < 2:
        return "flat"
    window = states[-3:]
    first, last = window[0], window[-1]
    diff = last.p_at_obs - first.p_at_obs
    if diff > 0.05:
        return "up"
    if diff < -0.05:
        return "down"
    return "flat"


def state_words(
    state: KnowledgeStateOut | None, p_target: float, params: KnowledgeParams
) -> str:
    """Short phrase for messages: '<навык>: шатко → уверенно' style."""
    level = skill_level(state, p_target, params)
    return {
        "low_data": "мало данных",
        "weak": "слабо",
        "shaky": "шатко",
        "solid": "уверенно",
        "closed": "закрыто",
    }[level]
