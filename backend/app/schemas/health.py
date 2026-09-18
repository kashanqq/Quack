"""Health-check contract from the shared Phase 1 specification (00-contracts.md §6)."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.llm import LLMStatus


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, Literal["ok", "down", "skipped"]]
    llm_status: LLMStatus
    version: str
