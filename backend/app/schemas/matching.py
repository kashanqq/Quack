"""Phase 2 matching presentation contracts."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.common import FactorStatus, Realism, Source
from app.schemas.programs import Program


class FactorOut(BaseModel):
    id: str
    kind: Literal["hard", "soft"]
    status: FactorStatus
    text: str
    source: Source | None
    weight: float


class MatchOut(BaseModel):
    program: Program
    realism: Realism
    factors: list[FactorOut]
    assumptions: list[str]
    score: float
    fits_text: str | None
    soft_pending: bool


class MatchingOut(BaseModel):
    items: list[MatchOut]
    total: int
    profile_readiness: float
    forecast_used: bool
    empty_reason: str | None


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


class ShiftOut(BaseModel):
    program_id: str
    from_realism: Realism
    to_realism: Realism
    changed_factors: list[str]
