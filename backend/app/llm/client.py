import json
import logging
from collections.abc import AsyncIterator
from typing import Any, Protocol, TypeVar, runtime_checkable

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel
from redis.asyncio import Redis

from app.config import Settings
from app.schemas.chat import StreamEvent, TextDelta, ToolCall
from app.schemas.llm import (
    LLMMessage,
    LLMResult,
    LLMStatus,
    LLMUsage,
    ModelSlot,
    ToolCallOut,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class LLMLike(Protocol):
    async def complete(
        self,
        messages: list[LLMMessage],
        slot: ModelSlot,
        tools: list[dict] | None = None,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> LLMResult: ...

    async def stream(
        self,
        messages: list[LLMMessage],
        slot: ModelSlot,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[StreamEvent]: ...

    async def structured(
        self, messages: list[LLMMessage], schema: type[T], slot: ModelSlot
    ) -> T: ...

    async def status(self) -> LLMStatus: ...


class LLMClient:
    def __init__(self, settings: Settings, redis: Redis) -> None:
        self._settings = settings
        self._redis = redis
        self._client = AsyncOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY.get_secret_value(),
            max_retries=0,
        )
        self._last_usage: LLMUsage | None = None

    def _model_for(self, slot: ModelSlot) -> str:
        if slot == "chat":
            return self._settings.MODEL_CHAT
        return self._settings.MODEL_BULK

    def _timeout_for(self, slot: ModelSlot) -> httpx.Timeout:
        seconds = (
            self._settings.LLM_TIMEOUT_CHAT_S
            if slot == "chat"
            else self._settings.LLM_TIMEOUT_BULK_S
        )
        return httpx.Timeout(seconds)

    def _to_openai_messages(self, messages: list[LLMMessage]) -> list[dict]:
        result: list[dict] = []
        for message in messages:
            entry: dict = {"role": message.role}
            if message.content is not None:
                entry["content"] = message.content
            if message.tool_calls is not None:
                entry["tool_calls"] = [
                    {
                        "id": call.call_id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.args),
                        },
                    }
                    for call in message.tool_calls
                ]
            if message.tool_call_id is not None:
                entry["tool_call_id"] = message.tool_call_id
            if message.name is not None:
                entry["name"] = message.name
            result.append(entry)
        return result

    async def _acquire(self, slot: ModelSlot) -> None:
        pass

    async def _check_breaker(self) -> None:
        pass

    async def _record(self, exc: Exception | None) -> None:
        pass

    async def complete(
        self,
        messages: list[LLMMessage],
        slot: ModelSlot,
        tools: list[dict] | None = None,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> LLMResult:
        await self._check_breaker()
        await self._acquire(slot)
        try:
            response = await self._client.chat.completions.create(
                model=self._model_for(slot),
                messages=self._to_openai_messages(messages),
                tools=tools,
                temperature=temperature,
                response_format=response_format,
                stream=False,
                timeout=self._timeout_for(slot),
            )
        except Exception as exc:
            await self._record(exc)
            raise
        await self._record(None)

        choice = response.choices[0]
        tool_calls: list[ToolCallOut] = []
        for call in choice.message.tool_calls or []:
            try:
                args = json.loads(call.function.arguments)
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "malformed tool_call arguments: %s", call.function.arguments
                )
                args = {}
            tool_calls.append(
                ToolCallOut(call_id=call.id, name=call.function.name, args=args)
            )

        usage = None
        if response.usage is not None:
            usage = LLMUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            )

        return LLMResult(
            text=choice.message.content or "",
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=choice.finish_reason,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        slot: ModelSlot,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        await self._check_breaker()
        await self._acquire(slot)

        pending: dict[int, dict[str, Any]] = {}
        emitted: set[int] = set()

        def build_tool_call(entry: dict[str, Any]) -> ToolCall:
            args = json.loads(entry["args"]) if entry["args"] else {}
            return ToolCall(
                type="tool_call",
                tool=entry["name"],
                args=args,
                call_id=entry["call_id"],
            )

        try:
            response = await self._client.chat.completions.create(
                model=self._model_for(slot),
                messages=self._to_openai_messages(messages),
                tools=tools,
                stream=True,
                timeout=self._timeout_for(slot),
            )
            async for chunk in response:
                usage = getattr(chunk, "usage", None)
                if usage is not None:
                    self._last_usage = LLMUsage(
                        prompt_tokens=usage.prompt_tokens,
                        completion_tokens=usage.completion_tokens,
                    )
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta
                if delta.content:
                    yield TextDelta(type="text_delta", text=delta.content)
                for tool_call_delta in delta.tool_calls or []:
                    index = tool_call_delta.index
                    entry = pending.setdefault(
                        index, {"call_id": None, "name": None, "args": ""}
                    )
                    if tool_call_delta.id:
                        entry["call_id"] = tool_call_delta.id
                    if tool_call_delta.function:
                        if tool_call_delta.function.name:
                            entry["name"] = tool_call_delta.function.name
                        if tool_call_delta.function.arguments:
                            entry["args"] += tool_call_delta.function.arguments
                if choice.finish_reason == "tool_calls":
                    for index, entry in pending.items():
                        if index not in emitted:
                            yield build_tool_call(entry)
                            emitted.add(index)
        except Exception as exc:
            await self._record(exc)
            raise

        for index, entry in pending.items():
            if index not in emitted:
                yield build_tool_call(entry)
                emitted.add(index)

        await self._record(None)

    async def structured(
        self, messages: list[LLMMessage], schema: type[T], slot: ModelSlot
    ) -> T:
        raise NotImplementedError

    async def status(self) -> LLMStatus:
        raise NotImplementedError
