"""Deterministic LLMLike implementation for tests — no network, no Redis.

Each call consumes the next item from a scripted queue instead of talking to
a provider, so the whole team can drive ``LLMClient``-shaped code with
predictable inputs.
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
from app.schemas.chat import StreamEvent, TextDelta
from app.schemas.llm import LLMMessage, LLMResult, LLMStatus, ModelSlot

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

FakeTurn = LLMResult | list[StreamEvent] | Exception | BaseModel


@dataclass
class FakeCall:
    method: str
    messages: list[LLMMessage]
    slot: ModelSlot
    tools: list[dict] | None


class FakeLLMClient:
    """Satisfies ``LLMLike`` (app.llm.client) by replaying a scripted queue.

    ``script`` holds one ``FakeTurn`` per expected call, consumed in order:
    an ``LLMResult`` for ``complete``/``structured``, a ``list[StreamEvent]``
    for ``stream``, an ``Exception`` to be raised, or (for ``structured``
    only) a ``BaseModel`` instance to return as-is.

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
            FakeCall(method="complete", messages=messages, slot=slot, tools=tools)
        )
        turn = self._pop()
        if isinstance(turn, Exception):
            raise turn
        if turn is None:
            return LLMResult(
                text="(fake)", tool_calls=[], usage=None, finish_reason="stop"
            )
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
            FakeCall(method="stream", messages=messages, slot=slot, tools=tools)
        )
        turn = self._pop()
        if isinstance(turn, Exception):
            raise turn
        if turn is None:
            yield TextDelta(type="text_delta", text="(fake)")
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
                    messages=current_messages,
                    slot=slot,
                    tools=None,
                )
            )
            turn = self._pop()
            if isinstance(turn, Exception):
                raise turn
            if turn is None:
                raise LLMUnavailable("structured output failed")
            if isinstance(turn, LLMResult):
                parsed, error = parse_structured_output(turn.text, schema)
                if parsed is not None:
                    return parsed
                last_raw_text = turn.text
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
