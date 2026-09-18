"""Half-life regression formulas — memory-architecture-quack.md §4.1–4.2.

Pure functions, no I/O. Parameters come from KnowledgeParams (config.py).
All numbers verify against 20-B1.md §7.1.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from app.config import KnowledgeParams
from app.schemas.knowledge import EvidenceIn, KnowledgeStateOut


def recall_p(half_life_h: float, last_observed_at: datetime, now: datetime) -> float:
    """P(recall now) = 2 ** (-Δt_h / half_life_h). Δt < 0 → 1.0."""
    delta_h = (now - last_observed_at).total_seconds() / 3600.0
    if delta_h <= 0:
        return 1.0
    return 2.0 ** (-delta_h / half_life_h)


def difficulty_factor(difficulty: int, max_difficulty: int = 5) -> float:
    """Normalize difficulty to [0.7, 1.3] linearly.

    difficulty=1 → 0.7, difficulty=max → 1.3.
    """
    if max_difficulty <= 1:
        return 1.0
    return 0.7 + 0.6 * (difficulty - 1) / (max_difficulty - 1)


def updated_half_life(
    h: float,
    *,
    direction: int,
    weight: float,
    difficulty_factor: float,
    share: float | None,
    params: KnowledgeParams,
) -> float:
    """Apply one evidence to half-life.

    direction=1 (correct):   h *= (1 + alpha * weight * difficulty_factor)
    direction=-1 (incorrect): h *= max(0.25, 1 - beta * weight)
    direction=0 (partial):   correct with weight*share, then incorrect
    Then clamp to [h_min, h_max].
    """
    if direction == 1:
        h_new = h * (1 + params.alpha * weight * difficulty_factor)
    elif direction == -1:
        h_new = h * max(0.25, 1 - params.beta * weight)
    else:
        if share is None:
            raise ValueError("partial evidence requires share")
        h_after_correct = h * (1 + params.alpha * weight * share * difficulty_factor)
        h_new = h_after_correct * max(0.25, 1 - params.beta * weight * (1 - share))
    return max(params.h_min, min(params.h_max, h_new))


def updated_p_at_obs(
    p_before: float,
    *,
    direction: int,
    weight: float,
    share: float | None,
) -> float:
    """Apply one evidence to p_at_obs.

    correct:   min(1, p + (1-p) * weight * 0.5)
    incorrect: p * (1 - weight * 0.5)
    partial:   correct with weight*share, then incorrect with weight*(1-share)
    """
    if direction == 1:
        return min(1.0, p_before + (1 - p_before) * weight * 0.5)
    if direction == -1:
        return p_before * (1 - weight * 0.5)
    if share is None:
        raise ValueError("partial evidence requires share")
    p_after_correct = min(1.0, p_before + (1 - p_before) * weight * share * 0.5)
    return p_after_correct * (1 - weight * (1 - share) * 0.5)


def confidence(evidence_mass: float, spread: float) -> float:
    """1 - exp(-mass/k), divided by spread (g). Clamped to [0, 1]."""
    # k_confidence is passed via params at the call site; here we read from settings.
    # To keep this pure, compute using a module-level default and let callers override.
    # Contract: confidence(0, spread) == 0.
    from app.config import settings  # local import to keep top-level pure

    k = settings.KNOWLEDGE.k_confidence
    if evidence_mass <= 0:
        return 0.0
    raw = 1.0 - math.exp(-evidence_mass / k)
    result = raw / spread
    return max(0.0, min(1.0, result))


def spread_factor(outcomes: list[int]) -> float:
    """1 + 0.5 * alternation_rate. Empty list → 1.0."""
    if not outcomes:
        return 1.0
    if len(outcomes) < 2:
        return 1.0
    alternations = sum(
        1
        for a, b in zip(outcomes, outcomes[1:], strict=False)
        if a != b and a != 0 and b != 0
    )
    # Normalize by number of comparisons to get rate in [0, 1]
    rate = alternations / (len(outcomes) - 1)
    return 1.0 + 0.5 * rate


def due_at(last_observed_at: datetime, half_life_h: float, p_target: float) -> datetime:
    """Moment when recall_p drops below p_target: last + h * log2(1/p_target)."""
    hours = half_life_h * math.log2(1.0 / p_target)
    return last_observed_at + timedelta(hours=hours)


def apply_evidence(
    state: KnowledgeStateOut | None,
    ev: EvidenceIn,
    *,
    params: KnowledgeParams,
) -> KnowledgeStateOut:
    """Apply one evidence to state, return a new state node.

    Starting state (state is None): h = params.h0, p_at_obs = 0.5, counters = 0,
    evidence_mass = 0, has_strong = False, last_observed_at = ev.observed_at.
    """
    if state is None:
        state = KnowledgeStateOut(
            skill_id=ev.skill_id,
            exam_id=ev.exam_id,
            p_recall=0.5,
            p_at_obs=0.5,
            half_life_h=params.h0,
            confidence=0.0,
            evidence_mass=0.0,
            n_correct=0,
            n_incorrect=0,
            n_partial=0,
            has_strong=False,
            last_observed_at=ev.observed_at,
            created_at=ev.observed_at,
        )

    p_before = recall_p(state.half_life_h, state.last_observed_at, ev.observed_at)

    new_h = updated_half_life(
        state.half_life_h,
        direction=ev.direction,
        weight=ev.weight,
        difficulty_factor=ev.difficulty_factor,
        share=ev.share,
        params=params,
    )

    new_p_at_obs = updated_p_at_obs(
        state.p_at_obs,
        direction=ev.direction,
        weight=ev.weight,
        share=ev.share,
    )

    # Chat cap: tier 3 cannot raise p above p_chat_cap
    if ev.tier == 3 and new_p_at_obs > params.p_chat_cap:
        new_p_at_obs = max(p_before, params.p_chat_cap)

    new_mass = state.evidence_mass + ev.weight
    new_n_correct = state.n_correct + (1 if ev.direction == 1 else 0)
    new_n_incorrect = state.n_incorrect + (1 if ev.direction == -1 else 0)
    new_n_partial = state.n_partial + (1 if ev.direction == 0 else 0)
    new_has_strong = state.has_strong or ev.tier in (1, 2)

    new_spread = spread_factor([ev.direction])
    new_confidence = confidence(new_mass, new_spread)

    new_p_recall = recall_p(new_h, ev.observed_at, ev.observed_at)

    return KnowledgeStateOut(
        skill_id=state.skill_id,
        exam_id=state.exam_id,
        p_recall=new_p_recall,
        p_at_obs=new_p_at_obs,
        half_life_h=new_h,
        confidence=new_confidence,
        evidence_mass=new_mass,
        n_correct=new_n_correct,
        n_incorrect=new_n_incorrect,
        n_partial=new_n_partial,
        has_strong=new_has_strong,
        last_observed_at=ev.observed_at,
        created_at=state.created_at,
    )
