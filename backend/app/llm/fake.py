"""Deterministic LLMLike implementation for tests — no network, no Redis.

Each call consumes the next item from a scripted queue instead of talking to
a provider, so the whole team can drive ``LLMClient``-shaped code with
predictable inputs.

Phase-3 scenarios (30-B2-phase2.md §4) are scripted with the helpers at the
bottom of this module: ``tool_call_turn`` / ``text_turn`` build the two stream
turns of a «tool_calls -> tool results -> text» round; the «invalid then
valid» structured pair needs no helper — the invalid half is a bare string
that fails schema validation, which exercises the built-in single retry.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel

from app.errors import LLMUnavailable
from app.llm.structured import (
    parse_structured_output,
    structured_validation_retry_message,
)
from app.schemas.chat import StreamEvent, TextDelta, ToolCall
from app.schemas.llm import LLMMessage, LLMResult, LLMStatus, ModelSlot, ToolCallOut

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

FakeTurn = LLMResult | list[StreamEvent] | Exception | BaseModel | str
"""One scripted call. A bare ``str`` is shorthand: raw model text for
``complete``/``structured`` (so an invalid-JSON turn is just the string), and
a single ``TextDelta`` for ``stream``."""


@dataclass
class FakeCall:
    """One recorded call. ``messages`` is a snapshot: ``run_tool_loop`` keeps
    appending to the very list it passes in, so storing the reference would
    make every recorded call show the conversation's final state instead of
    what the model saw at that step."""

    method: str
    messages: list[LLMMessage]
    slot: ModelSlot
    tools: list[dict] | None


class FakeLLMClient:
    """Satisfies ``LLMLike`` (app.llm.client) by replaying a scripted queue.

    ``script`` holds one ``FakeTurn`` per expected call, consumed in order:
    an ``LLMResult`` for ``complete``/``structured``, a ``list[StreamEvent]``
    for ``stream``, a bare ``str`` as shorthand for either (raw text, or one
    ``TextDelta``), an ``Exception`` to be raised, or (for ``structured``
    only) a ``BaseModel`` instance to return as-is.

    Two phase-3 scenarios the script is expected to cover:

    * «tool_calls -> tool results -> text» — two ``stream`` turns, the first
      carrying ``ToolCall`` events, the second only text. ``run_tool_loop``
      calls the tools between them and feeds the results back, so the second
      recorded call's ``messages`` already contain the ``role="tool"``
      entries; ``tool_messages()`` returns them for assertions.
    * «invalid then valid structured» — two turns for a single ``structured``
      call: text that fails schema validation, then a value that passes. One
      ``structured`` call consumes both, matching the single retry the real
      client performs.

    Empty-queue behaviour: ``stream`` yields a single ``TextDelta("(fake)")``
    turn. ``complete`` synthesizes a neutral ``LLMResult(text="(fake)")`` —
    there is no schema to violate, so a placeholder success is the least
    surprising default. ``structured`` cannot synthesize an arbitrary
    Pydantic model, so an empty queue raises the same
    ``LLMUnavailable("structured output failed")`` the real client raises
    after exhausting its retries.
    """

    def __init__(self, script: list[FakeTurn] | None = None) -> None:
        self._script: list[FakeTurn] = list(script) if script else []
        self.calls: list[FakeCall] = []
        self.forced_status: LLMStatus = "ok"

    def _pop(self) -> FakeTurn | None:
        if not self._script:
            return None
        return self._script.pop(0)

    async def complete(
        self,
        messages: list[LLMMessage],
        slot: ModelSlot,
        tools: list[dict] | None = None,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> LLMResult:
        self.calls.append(
            FakeCall(method="complete", messages=list(messages), slot=slot, tools=tools)
        )
        turn = self._pop()
        if isinstance(turn, Exception):
            raise turn
        if turn is None:
            return LLMResult(
                text="(fake)", tool_calls=[], usage=None, finish_reason="stop"
            )
        if isinstance(turn, str):
            return LLMResult(text=turn, tool_calls=[], usage=None, finish_reason="stop")
        if isinstance(turn, LLMResult):
            return turn
        raise TypeError(f"unexpected script item for complete(): {turn!r}")

    async def stream(
        self,
        messages: list[LLMMessage],
        slot: ModelSlot,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        self.calls.append(
            FakeCall(method="stream", messages=list(messages), slot=slot, tools=tools)
        )
        turn = self._pop()
        if isinstance(turn, Exception):
            raise turn
        if turn is None:
            yield TextDelta(type="text_delta", text="(fake)")
            return
        if isinstance(turn, str):
            yield TextDelta(type="text_delta", text=turn)
            return
        if isinstance(turn, list):
            for event in turn:
                yield event
            return
        raise TypeError(f"unexpected script item for stream(): {turn!r}")

    async def structured(
        self, messages: list[LLMMessage], schema: type[T], slot: ModelSlot
    ) -> T:
        current_messages = list(messages)
        last_raw_text = ""

        for _attempt in range(2):
            self.calls.append(
                FakeCall(
                    method="structured",
                    messages=list(current_messages),
                    slot=slot,
                    tools=None,
                )
            )
            turn = self._pop()
            if isinstance(turn, Exception):
                raise turn
            if turn is None:
                raise LLMUnavailable("structured output failed")
            if isinstance(turn, str | LLMResult):
                raw_text = turn if isinstance(turn, str) else turn.text
                parsed, error = parse_structured_output(raw_text, schema)
                if parsed is not None:
                    return parsed
                last_raw_text = raw_text
                current_messages = [
                    *current_messages,
                    structured_validation_retry_message(error or ""),
                ]
                continue
            if isinstance(turn, BaseModel):
                return turn  # type: ignore[return-value]
            raise TypeError(f"unexpected script item for structured(): {turn!r}")

        logger.warning("structured output failed: %s", last_raw_text[:200])
        raise LLMUnavailable("structured output failed")

    async def status(self) -> LLMStatus:
        return self.forced_status

    # --- assertions helpers for scripted scenarios ---

    @property
    def remaining(self) -> int:
        """Turns left in the script — zero means every scripted turn was used."""
        return len(self._script)

    def tool_messages(self) -> list[LLMMessage]:
        """Every ``role="tool"`` message this client was ever called with.

        In a «tool_calls -> tool results -> text» round these are the results
        ``run_tool_loop`` fed back before the text turn, so a test asserts on
        what the model actually saw rather than on the loop's internals.
        """
        return [
            message
            for call in self.calls
            for message in call.messages
            if message.role == "tool"
        ]


def text_turn(text: str) -> list[StreamEvent]:
    """A stream turn with text and no tool calls — ends ``run_tool_loop``."""
    return [TextDelta(type="text_delta", text=text)]


def tool_call_turn(
    tool: str,
    args: dict | None = None,
    call_id: str = "call_1",
    text: str = "",
) -> list[StreamEvent]:
    """A stream turn that requests one tool, optionally after some text.

    ``run_tool_loop`` runs the tool, appends its result to the messages and
    calls the client again — so this turn is always followed by another one
    in the script.
    """
    events: list[StreamEvent] = []
    if text:
        events.append(TextDelta(type="text_delta", text=text))
    events.append(
        ToolCall(type="tool_call", tool=tool, args=args or {}, call_id=call_id)
    )
    return events


def tool_call_result(call_id: str, name: str, args: dict | None = None) -> ToolCallOut:
    """The ``tool_calls`` entry of a non-streaming ``complete`` turn."""
    return ToolCallOut(call_id=call_id, name=name, args=args or {})
