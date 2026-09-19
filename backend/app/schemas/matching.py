"""Phase 2 matching presentation contracts."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.common import (
    AvailabilityOut,
    FactorStatus,
    GeneratedTextStatus,
    Realism,
    Source,
)
from app.schemas.programs import Program


class FactorOut(BaseModel):
    id: str
    kind: Literal["hard", "soft"]
    status: FactorStatus
    text: str
    source: Source | None
    weight: float


class SoftMatchOut(BaseModel):
    """One `soft_matches` row, as the job writes it and the route reads it."""

    program_id: str
    score: float
    fit_text: str | None = None
    caveat: str | None = None
    matched_traits: list[str] = []
    confidence: Literal["low", "medium", "high"] = "medium"
    prompt_version: str = ""
    stale: bool = False


class MatchOut(BaseModel):
    program: Program
    realism: Realism
    factors: list[FactorOut]
    assumptions: list[str]
    score: float
    # `fits_text` остаётся ради фронта фазы 2 и равен `soft.fit_text`.
    fits_text: str | None
    soft_pending: bool
    soft: SoftMatchOut | None = None
    realism_text: str | None = None
    realism_text_status: GeneratedTextStatus = "generating"


class MatchingOut(BaseModel):
    items: list[MatchOut]
    total: int
    profile_readiness: float
    forecast_used: bool
    empty_reason: str | None
    # Phase 5 (D03): `mode="cached"` with `reason="search_unavailable"` says
    # the list is what the cache and the verified floor hold, not a fresh
    # search. The hard factors and the comparison table stay usable (§10).
    availability: AvailabilityOut | None = None


class CompareRow(BaseModel):
    param: str
    values: dict[str, str]
    differs: bool
    relevant_to_student: bool
    source: Source | None


class CompareOut(BaseModel):
    program_ids: list[str]
    rows: list[CompareRow]
    collapsed_same: list[str]
    conclusion: str | None
    conclusion_status: GeneratedTextStatus = "generating"


class ShiftOut(BaseModel):
    program_id: str
    from_realism: Realism
    to_realism: Realism
    changed_factors: list[str]
