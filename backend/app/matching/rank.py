"""Ranking within a realism level — product-logic §3.3, §5.3.

Pure function: weighted hard score with the student's priority ranking.
Higher level first (possible > try > impossible), then score descending.

Source: 20-B1-phase2.md §5.3, 00-contracts-phase2.md §7.1.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import KnowledgeParams
from app.matching.hard import HardResult
from app.matching.realism import realism
from app.schemas.common import FactorStatus
from app.schemas.profile import Profile

_STATUS_VALUE: dict[FactorStatus, float] = {
    "above": 1.0,
    "in_range": 0.8,
    "unknown": 0.5,
    "below": 0.0,
}

_LEVEL_RANK = {"possible": 0, "try": 1, "impossible": 2}


class Ranked(BaseModel):
    program_id: str
    score: float
    factors: dict[str, float] = Field(default_factory=dict)
    realism: str = "try"


def rank(
    profile: Profile,
    hard_results: list[HardResult],
    soft_scores: dict[str, float],
    params: KnowledgeParams,
) -> list[Ranked]:
    """Order programs: realism level first, then weighted score descending."""
    weights = _priority_weights(profile, params)

    ranked: list[Ranked] = []
    for h in hard_results:
        level = realism(h, params)
        score = 0.0
        per_factor: dict[str, float] = {}

        for factor in h.factors:
            w = _weight_for(factor.id, weights)
            v = _STATUS_VALUE.get(factor.status, 0.5)
            contribution = w * v
            per_factor[factor.id] = contribution
            score += contribution

        soft = soft_scores.get(h.program_id)
        if soft is not None:
            program_weight = weights.get("program", 2.0)
            score += program_weight * soft
            per_factor["soft"] = program_weight * soft

        ranked.append(
            Ranked(
                program_id=h.program_id,
                score=score,
                factors=per_factor,
                realism=level,
            )
        )

    ranked.sort(key=lambda r: (_LEVEL_RANK.get(r.realism, 3), -r.score))
    return ranked


# --- weights ---


def _priority_weights(profile: Profile, params: KnowledgeParams) -> dict[str, float]:
    """Start from matching_priority_weights, then reorder by student's ranking.

    Первый в priorities.ranking ×2, последний ×0.5, остальные линейно.
    """
    base = dict(params.matching_priority_weights)
    ranking = profile.questionnaire.priorities.ranking.value or []
    if not ranking:
        return base

    n = len(ranking)
    if n == 1:
        base[ranking[0]] = base.get(ranking[0], 1.0) * 2.0
        return base

    for i, key in enumerate(ranking):
        # 2.0 → 0.5 линейно
        t = i / (n - 1)
        factor = 2.0 - 1.5 * t
        base[key] = base.get(key, 1.0) * factor
    return base


def _weight_for(factor_id: str, weights: dict[str, float]) -> float:
    """Map a FactorOut.id to one of the weight buckets."""
    if factor_id == "realism":
        return weights.get("realism", 3.0)
    if factor_id.startswith("exam_score"):
        return weights.get("realism", 3.0)
    if factor_id == "language":
        return weights.get("language", 1.0)
    if factor_id in ("budget", "cost"):
        return weights.get("cost", 2.0)
    if factor_id in ("country", "city"):
        return weights.get("location", 1.0)
    if factor_id == "direction":
        return weights.get("program", 2.0)
    if factor_id == "rank" or factor_id == "ranking":
        return weights.get("ranking", 1.0)
    if factor_id == "research":
        return weights.get("research", 1.0)
    if factor_id == "mobility":
        return weights.get("mobility", 1.0)
    if factor_id.startswith("deadline"):
        return weights.get("realism", 3.0)
    return 1.0
