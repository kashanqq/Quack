"""Observer — output schema for the prep-chat observer (docs/tz/30-B2.md §5.4).

The observer reads a window of unprocessed chat messages and turns what
happened into a list of observations; it never draws conclusions about
skill state itself (memory-architecture §8.1) — aggregation into evidence,
skill states and forecasts is done by rule-based code in phase 2.
``ObservationOut`` here is only the structured-output contract the model
must fill; nothing in this module reads from or writes to the graph.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.llm.client import LLMLike
from app.schemas.common import ErrorClass

ObservationKind = Literal[
    "solution_step",
    "task_in_chat",
    "applied",
    "confusion",
    "question",
    "avoided_trap",
    "root_hint",
    "proposed_misconception",
    "pace_signal",
]

# Fields each kind must fill, beyond `kind` itself — mirrors the promises
# made to the model in app/agents/prompts/observer_v1.md ("Виды наблюдений
# (kind) и что для каждого обязательно заполнить"), which is the source of
# truth here: ТЗ §5.4's own list of examples is not exhaustive (it says
# "например"), so this table also covers applied/confusion/question/
# avoided_trap, which the ТЗ examples don't mention but the prompt does.
_REQUIRED_FIELDS: dict[ObservationKind, tuple[str, ...]] = {
    "solution_step": ("outcome", "skill_id"),
    "task_in_chat": ("instance_id", "answer"),
    "applied": ("skill_id",),
    "confusion": ("skill_id",),
    "question": ("skill_id",),
    "avoided_trap": ("skill_id", "misconception_id"),
    "root_hint": ("skill_id", "root_skill_id"),
    "proposed_misconception": ("name", "description", "error_class"),
    "pace_signal": ("signal",),
}


class Observation(BaseModel):
    kind: ObservationKind
    outcome: Literal["correct", "incorrect"] | None = None
    skill_id: str | None = None
    misconception_id: str | None = None
    root_skill_id: str | None = None
    instance_id: str | None = None
    answer: str | None = None
    name: str | None = None
    description: str | None = None
    error_class: ErrorClass | None = None
    signal: str | None = None
    summary: str | None = Field(default=None, max_length=300)
    event_ids: list[int]
    # `pace_signal` is the one kind the memory-architecture §8.1 example
    # emits without a confidence field at all (payload has only `signal`
    # and `event_ids`) — since that example must validate byte-for-byte,
    # confidence needs a default rather than being required for every kind.
    # Defaulting to 1.0 (not 0.5): an omitted confidence reads as the model
    # not having felt a need to hedge, and pace_signal never gates evidence
    # weight downstream (§8.1's kind table has "—" for it), so the default
    # is inert either way. Logged in docs/sync-log.md.
    confidence: float = Field(default=1.0, ge=0, le=1)

    @model_validator(mode="after")
    def _check_required_for_kind(self) -> Observation:
        missing = [
            field_name
            for field_name in _REQUIRED_FIELDS[self.kind]
            if getattr(self, field_name) is None
        ]
        if missing:
            raise ValueError(
                f"observation kind {self.kind!r} is missing required "
                f"field(s): {', '.join(missing)}"
            )
        return self


class ObservationOut(BaseModel):
    observations: list[Observation]


async def observe(client: LLMLike, window: Any, context: Any) -> ObservationOut:
    """Run the observer over one window of chat messages (phase 2).

    Not implemented in phase 1 — this function stays a stub until the
    observer is wired into the `observe_chat` job (docs/tz/30-B2.md §5.5).
    In phase 2 it will: load `observer_v1` via `app.llm.prompts.load_prompt`,
    render it with `window` (the unprocessed message window) and the lists
    from `context` (topic/prerequisite skills, misconceptions, the chat's
    `task.issued` instance if any, the previous set's summary — see
    memory-architecture §8.1 "Вход наблюдателя"), call
    `client.structured(messages, ObservationOut, "bulk")`, and drop
    observations below `observer_min_confidence` before returning them for
    the rule layer to turn into evidence. `window` and `context` are left
    untyped here because their real shapes belong to that phase-2 wiring,
    not to this schema module.
    """
    raise NotImplementedError("phase 2")
