"""run_chat echo mode (docs/tz/30-B2.md §5.1, §6, tests/agents/test_router.py)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agents.router import AgentDeps, run_chat
from app.errors import LLMUnavailable
from app.llm.fake import FakeLLMClient
from app.llm.prompts import load_prompt
from app.schemas.chat import ChatCtx, ChatMessageIn, Done, StreamError, TextDelta

pytestmark = pytest.mark.phase1


def _ctx(kind: str) -> ChatCtx:
    return ChatCtx(
        student_id=uuid4(),
        kind=kind,
        chat_id=uuid4(),
        session_id=uuid4(),
        request_id="r1",
    )


def _deps(fake_llm: FakeLLMClient) -> AgentDeps:
    return AgentDeps(llm=fake_llm, pg=None, graph=None, redis=None)


async def test_selection_echo_streams_text_then_done_with_no_tools():
    fake_llm = FakeLLMClient([[TextDelta(text="Привет!")]])

    events = [
        event
        async for event in run_chat(
            "selection",
            _ctx("selection"),
            ChatMessageIn(text="привет"),
            _deps(fake_llm),
        )
    ]

    assert isinstance(events[0], TextDelta)
    assert isinstance(events[-1], Done)
    assert events[-1].referenced_skill_ids == []
    assert fake_llm.calls[0].messages[0].role == "system"
    assert fake_llm.calls[0].slot == "chat"
    assert fake_llm.calls[0].tools is None


async def test_prep_kind_uses_tutor_system_prompt():
    fake_llm = FakeLLMClient([[TextDelta(text="Давай разберём.")]])

    [
        event
        async for event in run_chat(
            "prep", _ctx("prep"), ChatMessageIn(text="привет"), _deps(fake_llm)
        )
    ]

    assert fake_llm.calls[0].messages[0].content == load_prompt("tutor").text


async def test_llm_unavailable_before_first_token_propagates_after_it_streams_error():
    fake_llm_before = FakeLLMClient([LLMUnavailable("down")])
    with pytest.raises(LLMUnavailable):
        [
            event
            async for event in run_chat(
                "selection",
                _ctx("selection"),
                ChatMessageIn(text="привет"),
                _deps(fake_llm_before),
            )
        ]

    fake_llm_after = FakeLLMClient()

    async def _stream_then_fail(messages, slot, tools=None):
        yield TextDelta(text="hi")
        raise LLMUnavailable("down")

    fake_llm_after.stream = _stream_then_fail

    events = [
        event
        async for event in run_chat(
            "selection",
            _ctx("selection"),
            ChatMessageIn(text="привет"),
            _deps(fake_llm_after),
        )
    ]

    assert isinstance(events[0], TextDelta)
    assert isinstance(events[-1], StreamError)
    assert events[-1].code == "llm_unavailable"
