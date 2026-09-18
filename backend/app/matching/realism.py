"""Realism levels — product-logic §3.3. Phase 2 stub."""

from __future__ import annotations

from typing import Literal

from app.schemas.profile import Profile
from app.schemas.programs import Program

Realism = Literal["impossible", "try", "possible"]


def realism(profile: Profile, program: Program, forecast) -> Realism:
    """Phase 2: aggregate hard factors into one of three word-level labels."""
    raise NotImplementedError("phase 2")
