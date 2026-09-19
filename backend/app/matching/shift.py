"""Detect shifts between two matchings — product-logic §3.3, §3.6.

Pure function: compare "before" and "after" matchings and list programs whose
realism level or factor statuses changed.

Source: 20-B1-phase2.md §5.4, 00-contracts-phase2.md §7.1; the snapshot form
of the input — docs/tz/phase3-agents.md §3.2–§3.3.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from app.schemas.matching import ShiftOut

__all__ = ["ShiftOut", "diff"]


def _get(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


def _normalize(item: Any) -> tuple[str, str, dict[str, str]]:
    """(program_id, realism, {factor_id: status}) of one matching item.

    Accepts a `MatchOut` (program nested), a snapshot item or a `MatchCard`
    (`program_id` flat), as objects or plain dicts — the selection assistant
    compares the Redis snapshot with a fresh `MatchingOut`.
    """
    program = _get(item, "program")
    program_id = _get(program, "id") if program is not None else None
    if program_id is None:
        program_id = _get(item, "program_id")
    factors = {
        str(_get(factor, "id")): str(_get(factor, "status"))
        for factor in (_get(item, "factors") or [])
    }
    return str(program_id), str(_get(item, "realism")), factors


def diff(before: Iterable[Any], after: Iterable[Any]) -> list[ShiftOut]:
    """List programs whose realism level or factor statuses changed.

    Compares by program_id. A program missing on one side is not reported
    (it just appeared or disappeared from the candidate list — that is not
    a shift in the sense of product-logic §3.3).

    Returns:
        list of ShiftOut, sorted by program_id.
    """
    old = {pid: (realism, factors) for pid, realism, factors in map(_normalize, before)}
    out: list[ShiftOut] = []
    for program_id, realism, factors in map(_normalize, after):
        if program_id not in old:
            continue
        old_realism, old_factors = old[program_id]
        changed = sorted(
            factor_id
            for factor_id in set(old_factors) | set(factors)
            if old_factors.get(factor_id) != factors.get(factor_id)
        )
        if old_realism == realism and not changed:
            continue
        out.append(
            ShiftOut(
                program_id=program_id,
                from_realism=old_realism,
                to_realism=realism,
                changed_factors=changed,
            )
        )
    return sorted(out, key=lambda shift: shift.program_id)
