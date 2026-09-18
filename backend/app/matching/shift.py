"""Detect shifts between two matchings — product-logic §3.3, §3.6.

Pure function: compare "before" and "after" matchings and list programs whose
realism level or factor statuses changed.

Source: 20-B1-phase2.md §5.4, 00-contracts-phase2.md §7.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # B3's phase-2 skeleton: MatchOut lives in schemas/matching.py.
    from app.schemas.matching import MatchOut


@dataclass
class ShiftOut:
    """One program whose realism or factors changed between two matchings."""

    program_id: str
    from_realism: str
    to_realism: str
    changed_factors: list[str]


def diff(before: list[MatchOut], after: list[MatchOut]) -> list[ShiftOut]:
    """List programs whose realism level or factor statuses changed.

    Compares by program_id. A program missing on one side is not reported
    (it just appeared or disappeared from the candidate list — that is not
    a shift in the sense of product-logic §3.3).

    Returns:
        list of ShiftOut, sorted by program_id.
    """
    raise NotImplementedError("phase 2")
