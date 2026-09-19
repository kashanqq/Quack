"""Health-check contract from the shared Phase 1 specification (00-contracts.md §6)."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.llm import LLMStatus


class HealthOut(BaseModel):
    """The §6 contract, kept in step with what `app/api/health.py` returns.

    `checks` carries counters as well as statuses: phase 4 added
    `graph_pending` and phase 5 `jobs_pending`, both integers and both
    omitted when zero. The field names of the original contract are
    unchanged — this only stops the declared type from disagreeing with the
    route (phase 5 §23 "Health").
    """

    status: Literal["ok", "degraded"]
    checks: dict[str, Literal["ok", "down", "skipped"] | int]
    llm_status: LLMStatus
    version: str
