"""Comparison — product-logic §3.4. Phase 2 stub."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.profile import Profile
from app.schemas.programs import Program


class Comparison(BaseModel):
    rows: list[dict]
    conclusion: str


def compare(profile: Profile, programs: list[Program]) -> Comparison:
    """Phase 2: side-by-side table across student-relevant and standard factors."""
    raise NotImplementedError("phase 2")
