"""Structured output: fence stripping, validation retry, tool mode
(docs/tz/30-B2.md §3.5, §6, tests/llm/test_structured.py)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, SecretStr

from app.config import Settings
from app.errors import LLMUnavailable
from app.llm.client import LLMClient
from app.llm.fake import FakeLLMClient
from app.schemas.llm import LLMMessage, LLMResult

pytestmark = pytest.mark.phase1


class Foo(BaseModel):
    a: int


async def test_first_invalid_second_valid_retries_and_records_validation_message():
    client = FakeLLMClient(
        [
            LLMResult(
                text='```json\n{"a": "x"}\n```',
                tool_calls=[],
                usage=None,
                finish_reason="stop",
            ),
            LLMResult(text='{"a": 1}', tool_calls=[], usage=None, finish_reason="stop"),
        ]
    )

    result = await client.structured(
        [LLMMessage(role="user", content="go")], Foo, "bulk"
    )

    assert result == Foo(a=1)
    assert "Ответ не прошёл валидацию" in client.calls[1].messages[-1].content


async def test_two_invalid_responses_raise_llm_unavailable():
    client = FakeLLMClient(
        [
            LLMResult(
                text="not json at all", tool_calls=[], usage=None, finish_reason="stop"
            ),
            LLMResult(
                text="still not json", tool_calls=[], usage=None, finish_reason="stop"
            ),
        ]
    )

    with pytest.raises(LLMUnavailable):
        await client.structured([LLMMessage(role="user", content="go")], Foo, "bulk")


async def test_valid_json_with_fence_and_surrounding_text_is_parsed():
    client = FakeLLMClient(
        [
            LLMResult(
                text='Вот ответ:\n```json\n{"a": 42}\n```\nСпасибо',
                tool_calls=[],
                usage=None,
                finish_reason="stop",
            )
        ]
    )

    result = await client.structured(
        [LLMMessage(role="user", content="go")], Foo, "bulk"
    )

    assert result == Foo(a=42)


def _make_response(*, tool_calls=None, content=""):
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice], usage=None)


def _make_tool_call(call_id: str, name: str, args: dict):
    function = SimpleNamespace(name=name, arguments=json.dumps(args))
    return SimpleNamespace(id=call_id, function=function)


async def test_tool_mode_sends_emit_tool_and_parses_tool_call_args(redis, monkeypatch):
    settings = Settings(
        LLM_API_KEY=SecretStr("test-key"),
        LLM_BASE_URL="http://test",
        LLM_STRUCTURED_MODE="tool",
    )
    client = LLMClient(settings, redis)

    calls: list[dict] = []

    async def fake_create(**kwargs):
        calls.append(kwargs)
        return _make_response(tool_calls=[_make_tool_call("c1", "emit", {"a": 7})])

    monkeypatch.setattr(client._client.chat.completions, "create", fake_create)

    result = await client.structured(
        [LLMMessage(role="user", content="go")], Foo, "bulk"
    )

    assert result == Foo(a=7)
    assert calls[0]["tools"] == [
        {
            "type": "function",
            "function": {"name": "emit", "parameters": Foo.model_json_schema()},
        }
    ]
    assert calls[0]["tool_choice"] == {"type": "function", "function": {"name": "emit"}}
