"""Misconception statuses, triggers, visibility — memory-architecture §5.1–§5.3.

Pure functions, no I/O.
Source: 20-B1-phase2.md §2.2.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.config import KnowledgeParams
from app.schemas.knowledge import (
    EvidenceIn,
    MisconceptionStateOut,
    MisconceptionStatus,
)

Event = Literal["hit", "avoided", "dispute", "undispute"]
Audience = Literal["student", "tutor", "sets"]


def next_status(
    current: MisconceptionStatus | None,
    *,
    event: Event,
    strong: bool,
    occurrence_count: int,
    strong_count: int,
    consecutive_avoided: int,
    strong_at_dispute: int,
    disputed_at: datetime | None,
    previous_status: MisconceptionStatus | None,
    params: KnowledgeParams,
) -> MisconceptionStatus:
    """Transitions from §5.1.

    - None + hit → suspected
    - suspected + occurrence_count >= misc_confirm_min_occ and strong_count >= 1
      → confirmed
    - confirmed + consecutive_avoided >= misc_resolve_avoided → resolved
    - resolved + hit → confirmed (relapse)
    - любой + dispute → disputed
    - disputed + undispute → previous_status (fallback suspected)
    - disputed + hit and strong_count - strong_at_dispute >= 2 → confirmed
    """
    if event == "dispute":
        return "disputed"
    if event == "undispute":
        return previous_status or "suspected"

    if current is None:
        return "suspected" if event == "hit" else "suspected"

    if current == "suspected":
        if (
            event == "hit"
            and occurrence_count >= params.misc_confirm_min_occ
            and strong_count >= 1
        ):
            return "confirmed"
        return "suspected"

    if current == "confirmed":
        if event == "avoided" and consecutive_avoided >= params.misc_resolve_avoided:
            return "resolved"
        return "confirmed"

    if current == "resolved":
        if event == "hit":
            return "confirmed"
        return "resolved"

    if current == "disputed":
        if event == "hit" and (strong_count - strong_at_dispute) >= 2:
            return "confirmed"
        return "disputed"

    return current


def update_triggers(
    evidences: list[EvidenceIn],
    *,
    params: KnowledgeParams,
) -> dict:
    """Aggregate triggers from evidence contexts (§5.3).

    Stores (hits, total) pairs, где `total` — общее число свидетельств n
    (как в §5.3: `by_task_type: {mcq4: 3/4}` — 4 это n, а не число mcq4).
    """
    n = len(evidences)

    by_task_type: dict[str, int] = {}
    by_difficulty: dict[str, int] = {}
    by_tag: dict[str, int] = {}
    hurried_hits = 0
    late_session_hits = 0
    after_guideline_hits = 0

    for ev in evidences:
        ctx = ev.context
        if ctx is None:
            continue
        if ctx.task_type is not None:
            by_task_type[ctx.task_type] = by_task_type.get(ctx.task_type, 0) + 1
        if ctx.difficulty is not None:
            key = "≥4" if ctx.difficulty >= 4 else str(ctx.difficulty)
            by_difficulty[key] = by_difficulty.get(key, 0) + 1
        if ctx.tags:
            for tag in ctx.tags:
                by_tag[tag] = by_tag.get(tag, 0) + 1
        if ctx.time_ratio is not None and ctx.time_ratio < 0.7:
            hurried_hits += 1
        if ctx.session_minute is not None and ctx.session_minute > 30:
            late_session_hits += 1
        if ctx.after_guideline:
            after_guideline_hits += 1

    return {
        "by_task_type": {k: (v, n) for k, v in by_task_type.items()},
        "by_difficulty": {k: (v, n) for k, v in by_difficulty.items()},
        "by_tag": {k: (v, n) for k, v in by_tag.items()},
        "hurried": (hurried_hits, n),
        "late_session": (late_session_hits, n),
        "after_guideline": (after_guideline_hits, n),
        "n": n,
    }


def visible_label(
    state: MisconceptionStateOut,
    params: KnowledgeParams,
    now: datetime,
) -> str:
    """Short label for the student (§5.2)."""
    if state.status == "disputed":
        return "оспорено"
    if state.status == "suspected":
        return f"подозрение, {state.occurrence_count} из {params.misc_confirm_min_occ}"
    if state.status == "confirmed":
        return f"подтверждено, {state.occurrence_count} наблюдений"
    if state.status == "resolved":
        age_days = (now - state.updated_at).days
        if age_days < params.under_watch_days:
            return "исправлено, следим"
        return ""
    return ""


def visible_to(
    state: MisconceptionStateOut,
    audience: Audience,
    params: KnowledgeParams,
    now: datetime,
) -> bool:
    """§5.2 visibility table."""
    age_days = (now - state.updated_at).days
    fresh = age_days < params.under_watch_days

    if audience == "student":
        if state.status == "resolved" and not fresh:
            return False
        if state.status == "disputed":
            return False
        return True

    if audience == "tutor":
        if state.status == "confirmed":
            return True
        if state.status == "resolved" and fresh:
            return True
        return False

    if audience == "sets":
        if state.status == "confirmed":
            return True
        if state.status == "resolved" and fresh:
            return True
        return False

    return False


def trigger_words(triggers: dict, *, params: KnowledgeParams) -> str | None:
    """Human phrase from triggers (§5.3). Only when n ≥ 3 and share ≥ 0.75."""
    n = triggers.get("n", 0)
    if n < params.trigger_min_n:
        return None

    parts: list[str] = []
    for tag, pair in (triggers.get("by_tag") or {}).items():
        hits, total = pair
        if total > 0 and hits / total >= params.trigger_min_share:
            parts.append(f"на задачах с тегом {tag}")

    hurried_hits, hurried_total = triggers.get("hurried", (0, 0))
    if hurried_total > 0 and hurried_hits / hurried_total >= params.trigger_min_share:
        parts.append("когда торопится")

    late_hits, late_total = triggers.get("late_session", (0, 0))
    if late_total > 0 and late_hits / late_total >= params.trigger_min_share:
        parts.append("в конце сессии")

    if not parts:
        return None
    return "обычно — " + " и ".join(parts)
