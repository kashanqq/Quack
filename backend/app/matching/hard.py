"""Hard factors — product-logic §3.3, memory-architecture §10.3. Phase 2 stub."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.profile import Profile
from app.schemas.programs import Program


class HardResult(BaseModel):
    program_id: str
    status: str  # ниже / в диапазоне / выше / неизвестно
    factors: list[dict]


def hard_filter(profile: Profile, programs: list[Program]) -> list[HardResult]:
    """Phase 2: score each program on requirements vs profile."""
    raise NotImplementedError("phase 2")


def explain_empty(hard_results: list[HardResult]) -> str:
    """Which factor cut everything and what loosening it would give.

    product-logic §6.3: when no program fits, name the hard factor that is
    `below` for every program and say what relaxing it would open up.

    Returns:
        A short phrase for the student, or a generic fallback if no single
        factor dominates.
    """
    raise NotImplementedError("phase 2")
