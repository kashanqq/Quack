"""Tool-calling loop: model -> tool call -> result back to model.

Drives ``client.stream`` until the model stops requesting tools, yielding
``StreamEvent``s as they happen. The final yielded item is a ``LoopEnd`` —
deliberately not a ``StreamEvent`` (it carries the accumulated text, tool
results and step count for the calling agent to build its own ``Done``),
so the return type is annotated ``AsyncIterator[StreamEvent | LoopEnd]``.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.errors import LLMUnavailable
from app.llm.client import LLMLike
from app.llm.tools import ToolCtx, ToolRegistry
from app.schemas.chat import StreamError, StreamEvent, TextDelta, ToolCall, ToolResult
from app.schemas.llm import LLMMessage, ModelSlot, ToolCallOut


@dataclass
class LoopEnd:
    text_full: str
    tool_results: list[ToolResult]
    steps: int


def _safe_json(value: object) -> str:
    return json.dumps(value, default=str)


async def run_tool_loop(
    client: LLMLike,
    registry: ToolRegistry,
    messages: list[LLMMessage],
    slot: ModelSlot,
    ctx: ToolCtx,
    max_steps: int = 6,
) -> AsyncIterator[StreamEvent | LoopEnd]:
    local_messages = list(messages)
    text_full = ""
    tool_results: list[ToolResult] = []
    steps = 0

    while True:
        steps += 1
        if steps > max_steps:
            yield StreamError(
                type="error",
                code="tool_loop_limit",
                message=f"tool loop exceeded max_steps={max_steps}",
            )
            return

        tools = registry.schemas() or None
        step_calls: list[ToolCall] = []
        try:
            async for event in client.stream(local_messages, slot, tools=tools):
                if isinstance(event, TextDelta):
                    text_full += event.text
                    yield event
                elif isinstance(event, ToolCall):
                    step_calls.append(event)
                    yield event
                else:
                    yield event
        except LLMUnavailable as exc:
            yield StreamError(type="error", code="llm_unavailable", message=str(exc))
            return

        if not step_calls:
            yield LoopEnd(text_full=text_full, tool_results=tool_results, steps=steps)
            return

        local_messages.append(
            LLMMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCallOut(call_id=call.call_id, name=call.tool, args=call.args)
                    for call in step_calls
                ],
            )
        )

        for call in step_calls:
            try:
                data = await registry.call(call.tool, call.args, ctx)
                result = ToolResult(
                    type="tool_result",
                    tool=call.tool,
                    call_id=call.call_id,
                    data=data,
                    error=None,
                )
            except Exception as exc:
                result = ToolResult(
                    type="tool_result",
                    tool=call.tool,
                    call_id=call.call_id,
                    data=None,
                    error=str(exc),
                )
            tool_results.append(result)
            yield result
            local_messages.append(
                LLMMessage(
                    role="tool",
                    content=_safe_json({"data": result.data, "error": result.error}),
                    tool_call_id=call.call_id,
                )
            )
