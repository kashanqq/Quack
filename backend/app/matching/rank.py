"""Ranking — product-logic §3.3. Phase 2 stub."""

from __future__ import annotations

from pydantic import BaseModel

from app.matching.hard import HardResult
from app.schemas.profile import Profile


class Ranked(BaseModel):
    program_id: str
    score: float
    factors: dict


def rank(
    profile: Profile, hard_results: list[HardResult], soft_scores: dict[str, float]
) -> list[Ranked]:
    """Phase 2: order within realism level by weighted hard + soft scores."""
    raise NotImplementedError("phase 2")
