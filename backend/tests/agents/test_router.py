"""agents.router.run_chat — branching, history window, 503 semantics
(docs/tz/phase3-agents.md §3.1, §6.3)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents import router
from app.agents.router import run_chat
from app.errors import LLMUnavailable
from app.graph.context import TopicContext
from app.llm.fake import FakeLLMClient
from app.schemas.chat import ChatMessageIn, Done, StreamError, ToolCall, ToolResult
from tests.agents._scripts import TC, TXT, collect, patch_selection_io

pytestmark = pytest.mark.phase3


def _patch_history(monkeypatch, history, profile):
    async def list_messages(_session, _sid, _chat, limit=50):
        return history[-limit:]

    monkeypatch.setattr(router.messages_repo, "list_messages", list_messages)
    monkeypatch.setattr(
        router.profiles_repo, "get_profile", AsyncMock(return_value=profile)
    )


async def test_router_selection_branch(
    monkeypatch, agent_deps, chat_ctx, history_factory, profile_factory
):
    profile = profile_factory()
    history = history_factory(
        [("user", "привет"), ("assistant", "здравствуй", "opening")]
    )
    _patch_history(monkeypatch, history, profile)
    patch_selection_io(monkeypatch, profile=profile)
    agent_deps.llm = FakeLLMClient([TXT("ок")])

    events = await collect(
        run_chat(
            "selection", chat_ctx(), ChatMessageIn(text="хочу учиться"), agent_deps
        )
    )

    messages = agent_deps.llm.calls[0].messages
    assert messages[0].role == "system"
    assert [m.content for m in messages[1:3]] == ["привет", "здравствуй"]
    assert messages[-1].role == "user" and messages[-1].content == "хочу учиться"
    assert isinstance(events[-1], Done)
    assert events[-1].mode in {"opening", "intake", "summary", "matching", "refine"}


async def test_router_prep_branch_uses_tutor(
    monkeypatch, agent_deps, chat_ctx, profile_factory
):
    from uuid import uuid4

    from app.agents import tutor

    _patch_history(monkeypatch, [], profile_factory())
    monkeypatch.setattr(
        tutor.apply_context,
        "get_topic_context",
        AsyncMock(return_value=TopicContext(topic=["x"], skill_ids=["math.a"])),
    )
    agent_deps.llm = FakeLLMClient([TXT("Давай разберём.")])
    ctx = chat_ctx("prep", set_id=uuid4(), topic_skill_id="math.a")

    await collect(run_chat("prep", ctx, ChatMessageIn(text="объясни"), agent_deps))

    system = agent_deps.llm.calls[0].messages[0].content
    assert "<learner_model" in system
    assert "<session" in system


async def test_router_drops_duplicate_current_message(
    monkeypatch, agent_deps, chat_ctx, history_factory, profile_factory
):
    profile = profile_factory()
    history = history_factory(
        [("user", "раз"), ("assistant", "два", "opening"), ("user", "привет")]
    )
    _patch_history(monkeypatch, history, profile)
    patch_selection_io(monkeypatch, profile=profile)
    agent_deps.llm = FakeLLMClient([TXT("ок")])

    await collect(
        run_chat("selection", chat_ctx(), ChatMessageIn(text="привет"), agent_deps)
    )

    users = [m for m in agent_deps.llm.calls[0].messages if m.content == "привет"]
    assert len(users) == 1
    assert agent_deps.llm.calls[0].messages[-1].content == "привет"


async def test_router_history_window(
    monkeypatch, agent_deps, chat_ctx, history_factory, profile_factory
):
    profile = profile_factory()
    pairs = [
        ("user" if i % 2 == 0 else "assistant", f"m{i}", "intake") for i in range(15)
    ]
    _patch_history(monkeypatch, history_factory(pairs), profile)
    patch_selection_io(monkeypatch, profile=profile)
    agent_deps.llm = FakeLLMClient([TXT("ок")])

    await collect(
        run_chat("selection", chat_ctx(), ChatMessageIn(text="новое"), agent_deps)
    )

    messages = agent_deps.llm.calls[0].messages
    window = router.settings.knowledge.chat_window
    assert len(messages) == 1 + window + 1  # system + window + current
    assert messages[1].content == f"m{15 - window}"


async def test_router_llm_unavailable_before_first_event_is_raised(
    monkeypatch, agent_deps, chat_ctx, profile_factory
):
    profile = profile_factory()
    _patch_history(monkeypatch, [], profile)
    patch_selection_io(monkeypatch, profile=profile)

    agent_deps.llm = FakeLLMClient([LLMUnavailable("down")])
    with pytest.raises(LLMUnavailable):
        await collect(
            run_chat("selection", chat_ctx(), ChatMessageIn(text="hi"), agent_deps)
        )

    from app.agents import selection

    monkeypatch.setattr(
        selection.profiles_repo,
        "apply_profile_update",
        AsyncMock(return_value=profile),
    )
    monkeypatch.setattr(selection.store, "append", AsyncMock())
    agent_deps.llm = FakeLLMClient(
        [
            TC("update_profile", {"path": "traits.summary", "value": "тепло"}),
            LLMUnavailable("down"),
        ]
    )
    events = await collect(
        run_chat("selection", chat_ctx(), ChatMessageIn(text="hi"), agent_deps)
    )
    assert [type(e) for e in events] == [ToolCall, ToolResult, StreamError]
    assert events[-1].code == "llm_unavailable"
