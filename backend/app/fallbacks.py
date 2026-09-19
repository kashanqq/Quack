"""One place that decides what to show when a dependency is not there (§11 A1).

Pure policy: no I/O, no model call, no clock of its own. A route hands it the
cache rows it already read and the current LLM status, and gets back the DTO
to return. Keeping it pure is what makes the outage behaviour testable
without a provider, and what keeps it identical between `/texts`, the set
summary and the matching texts.

The two rules that matter:

- **A saved text is labelled as saved.** During an outage the last ready text
  of the same scope may be shown, but always with `mark="saved_version"` —
  even when its hash still matches. Phase 4 only used that mark for a stale
  hash; phase 5 widens it, because "this is what we had" is a different claim
  from "this is current" (§23 TextMark).
- **Nothing is invented.** No text is better than a plausible one: when there
  is nothing to show the answer is `text=None` with an explicit `reason`, and
  `status` is never `ready` for a placeholder.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from app.schemas.common import AvailabilityMode, AvailabilityOut, AvailabilityReason
from app.schemas.texts import GeneratedText, GeneratedTextOut

LLMStatus = Literal["ok", "degraded", "down"]


def select_text(
    *,
    kind: str,
    subject: str,
    set_id: UUID | None,
    current_hash: str | None,
    current: GeneratedText | None,
    last_ready: GeneratedText | None,
    llm_status: LLMStatus = "ok",
) -> GeneratedTextOut:
    """The §3.5 table, plus the outage column phase 5 adds.

    `current_hash is None` means the inputs could not even be computed (the
    graph is down): there is no honest hash to file a text under, so the
    answer says so rather than showing a text under someone else's key.
    """
    if current_hash is None:
        return GeneratedTextOut(
            kind=kind,  # type: ignore[arg-type]
            subject=subject,
            set_id=set_id,
            status="generating",
            input_hash="",
            reason="graph_unavailable",
        )

    base = {
        "kind": kind,
        "subject": subject,
        "set_id": set_id,
        "input_hash": current_hash,
    }
    if current is not None and current.status == "ready" and current.text:
        # Even a current text is marked as saved while the model is down: the
        # student is looking at what we had, and nothing can refresh it now.
        outage = llm_status == "down"
        return GeneratedTextOut(
            **base,
            status="ready",
            text=current.text,
            mark="saved_version" if outage else "generated",
            prompt_version=current.prompt_version,
            generated_at=current.created_at,
            reason="llm_unavailable" if outage else None,
        )
    if last_ready is not None and last_ready.text:
        return GeneratedTextOut(
            **base,
            status="stale",
            text=last_ready.text,
            mark="saved_version",
            prompt_version=last_ready.prompt_version,
            generated_at=last_ready.created_at,
            reason="llm_unavailable" if llm_status == "down" else None,
        )
    if current is not None and current.status == "failed":
        return GeneratedTextOut(
            **base, status="failed", reason=current.error or "llm_unavailable"
        )
    if current is not None:
        return GeneratedTextOut(**base, status="generating")
    return GeneratedTextOut(
        **base,
        status="generating",
        reason="llm_unavailable" if llm_status == "down" else "not_generated",
    )


def availability(
    *,
    graph_ok: bool,
    projection_pending: bool = False,
    search_ok: bool = True,
    cached: bool = False,
    as_of_event_id: int | None = None,
) -> AvailabilityOut:
    """How a read model was answered — `live`, `cached`, `static`, or not at all.

    The caller states facts it knows; the ranking of them lives here so two
    routes cannot disagree about what counts as `static`.
    """
    mode: AvailabilityMode
    reason: AvailabilityReason | None = None
    if not graph_ok:
        mode = "static"
        reason = "graph_unavailable"
    elif projection_pending:
        mode = "live"
        reason = "projection_pending"
    elif not search_ok:
        mode = "cached"
        reason = "search_unavailable"
    elif cached:
        mode = "cached"
    else:
        mode = "live"
    return AvailabilityOut(mode=mode, reason=reason, as_of_event_id=as_of_event_id)
