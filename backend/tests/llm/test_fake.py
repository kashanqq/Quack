"""FakeLLMClient scripted-queue behaviour (docs/tz/30-B2.md §6,
tests/llm/test_fake.py)."""

from __future__ import annotations

import pytest

from app.llm.fake import FakeLLMClient
from app.schemas.chat import TextDelta
from app.schemas.llm import LLMResult

pytestmark = pytest.mark.phase1


async def test_complete_returns_next_scripted_result_and_records_call():
    client = FakeLLMClient(
        [LLMResult(text="hi", tool_calls=[], usage=None, finish_reason="stop")]
    )

    result = await client.complete([], "chat")

    assert result.text == "hi"
    assert client.calls[0].method == "complete"


async def test_stream_yields_scripted_events_in_order():
    client = FakeLLMClient([[TextDelta(text="a"), TextDelta(text="b")]])

    events = [event async for event in client.stream([], "chat")]

    assert events == [TextDelta(text="a"), TextDelta(text="b")]


async def test_exception_in_script_is_raised_on_call():
    client = FakeLLMClient([ValueError("boom")])

    with pytest.raises(ValueError, match="boom"):
        await client.complete([], "chat")


async def test_empty_script_stream_yields_single_placeholder_delta():
    client = FakeLLMClient()

    events = [event async for event in client.stream([], "chat")]

    assert events == [TextDelta(text="(fake)")]
