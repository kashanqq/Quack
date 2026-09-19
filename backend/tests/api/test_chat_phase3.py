"""Chat transport of phase 3 (docs/tz/phase3-agents.md §3.12, §6.11, §6.12)."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4, uuid5

import fakeredis.aioredis
import httpx
import pytest
from fastapi.testclient import TestClient

from app import keys
from app.api import chat, deps
from app.api.auth import issue_token
from app.config import KnowledgeParams
from app.events.dispatch import RuleDeps
from app.main import create_app
from app.schemas.chat import Done, StreamError, TextDelta, ToolCall, ToolResult
from app.schemas.events import Event, EventType
from app.schemas.knowledge import SkillStateView
from tests.agents._jobs_fakes import set_out

pytestmark = pytest.mark.phase3

NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def commit(self):
        return None


def _frames(response):
    return [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


@pytest.fixture
def world(monkeypatch):
    student_id = uuid4()
    server = fakeredis.FakeServer()
    redis = fakeredis.aioredis.FakeRedis(server=server)
    state = SimpleNamespace(
        sync_redis=fakeredis.FakeRedis(server=server),
        events=[],
        messages=[],
        script=[],
        enqueued=[],
        count=0,
        student_id=student_id,
        redis=redis,
        dispatch_flags=[],
    )

    async def append(_session, _redis, event, deps_=None, *, dispatch_event=True):
        state.dispatch_flags.append((event.type, dispatch_event))
        state.events.append(event)
        return SimpleNamespace(id=len(state.events))

    async def append_message(_s, sid, chat_id, role, text, markup, event_id):
        state.messages.append((chat_id, role, text, event_id))
        return uuid4()

    async def run_chat(_kind, _ctx, _message, _deps):
        for event in state.script:
            if isinstance(event, asyncio.Event):
                await event.wait()
                continue
            yield event

    async def enqueue(arq, queue, fn_name, **kwargs):
        state.enqueued.append((fn_name, kwargs))
        return kwargs.get("_job_id")

    async def count(_session, _chat_id, _types):
        return state.count

    monkeypatch.setattr(chat.store, "append", append)
    monkeypatch.setattr(chat.store, "count_unprocessed", count)
    monkeypatch.setattr(chat.messages, "append_message", append_message)
    monkeypatch.setattr(chat, "current_session_id", AsyncMock(return_value=uuid4()))
    monkeypatch.setattr(chat, "enqueue", enqueue)
    monkeypatch.setattr(
        chat,
        "_agent_router",
        lambda: SimpleNamespace(AgentDeps=SimpleNamespace, run_chat=run_chat),
    )
    app = create_app()
    app.dependency_overrides[deps.get_redis] = lambda: redis
    state.app = app
    state.token = issue_token(student_id, "s@quack.kz")

    def client():
        c = TestClient(app)
        c.cookies.set("quack_token", state.token)
        return c

    def setup(c):
        app.state.llm = object()
        app.state.sessionmaker = FakeSession
        app.state.redis = redis
        app.state.arq = object()

    state.client = client
    state.setup = setup
    return state


def test_sse_tool_call_and_result_frames(world):
    world.script = [
        ToolCall(tool="run_matching", args={"limit": 5}, call_id="c1"),
        ToolResult(tool="run_matching", call_id="c1", data={"count": 3}),
        TextDelta(text="Вот"),
        Done(event_id=0, mode="matching"),
    ]
    with world.client() as c:
        world.setup(c)
        response = c.post("/chat/selection/messages", json={"text": "покажи"})

    frames = _frames(response)
    assert [f["type"] for f in frames] == [
        "tool_call",
        "tool_result",
        "text_delta",
        "done",
    ]
    assert frames[-1]["event_id"] == 2
    assert frames[1]["data"] == {"count": 3}
    assert [m[1] for m in world.messages] == ["user", "assistant"]
    assert world.messages[1][2] == "Вот"


def test_postcheck_failed_not_persisted(world):
    world.script = [
        TextDelta(text="Стоит 1500"),
        StreamError(code="postcheck_failed", message="x"),
    ]
    with world.client() as c:
        world.setup(c)
        response = c.post("/chat/selection/messages", json={"text": "сколько"})

    frames = _frames(response)
    assert frames[-1] == {"type": "error", "code": "postcheck_failed", "message": "x"}
    assert [m[1] for m in world.messages] == ["user"]
    assert [e.type for e in world.events] == [EventType.message_user]


def test_message_events_not_dispatched(world):
    world.script = [TextDelta(text="ок"), Done(event_id=0)]
    with world.client() as c:
        world.setup(c)
        c.post("/chat/selection/messages", json={"text": "hi"})
    assert world.dispatch_flags == [
        (EventType.message_user, False),
        (EventType.message_assistant, False),
    ]


def test_chat_lock_conflict(world):
    chat_id = uuid5(world.student_id, "selection")
    lock = keys.lock(f"chat:{chat_id}")
    world.script = [Done(event_id=0)]
    with world.client() as c:
        world.setup(c)
        world.sync_redis.set(lock, "other")
        busy = c.post("/chat/selection/messages", json={"text": "hi"})
        assert busy.status_code == 409
        assert busy.json()["error"]["code"] == "conflict"
        assert world.events == []

        world.sync_redis.delete(lock)
        ok = c.post("/chat/selection/messages", json={"text": "hi"})
    assert ok.status_code == 200
    assert world.sync_redis.get(lock) is None


def test_observer_trigger_every_n(world):
    set_id = uuid4()
    body = {"text": "решил", "set_id": str(set_id), "topic_skill_id": "algebra"}
    world.script = [Done(event_id=0, mode="review")]
    with world.client() as c:
        world.setup(c)
        world.count = 5
        c.post("/chat/prep/messages", json=body)
        assert world.enqueued == []
        world.count = 6
        c.post("/chat/prep/messages", json=body)

    chat_id = uuid5(world.student_id, f"prep:{set_id}:algebra")
    [(fn, kwargs)] = world.enqueued
    assert fn == "observe_chat"
    assert kwargs["_job_id"] == f"observe:{chat_id}"
    assert kwargs["trigger"] == "every_n"


def test_selection_chat_never_triggers_observer(world):
    world.script = [Done(event_id=0)]
    world.count = 100
    with world.client() as c:
        world.setup(c)
        c.post("/chat/selection/messages", json={"text": "hi"})
    assert world.enqueued == []


def test_set_chat_id_without_topic(world):
    set_id = uuid4()
    world.script = [Done(event_id=0)]
    with world.client() as c:
        world.setup(c)
        response = c.post(
            "/chat/prep/messages", json={"text": "hi", "set_id": str(set_id)}
        )
    assert response.status_code == 200
    assert all(
        e.chat_id == uuid5(world.student_id, f"prep:{set_id}") for e in world.events
    )


def _diff_deps(world, monkeypatch, *, owned=True):
    rule_deps = RuleDeps(
        graph=None, redis=world.redis, params=KnowledgeParams(), now=lambda: NOW
    )

    async def session():
        yield FakeSession()

    world.app.dependency_overrides[deps.get_session] = session
    world.app.dependency_overrides[deps.get_rule_deps] = lambda: rule_deps
    world.app.dependency_overrides[deps.get_arq] = lambda: object()
    monkeypatch.setattr(
        chat.sets_repo,
        "get_set",
        AsyncMock(
            side_effect=lambda _s, _sid, set_id: set_out(set_id) if owned else None
        ),
    )


def test_observe_endpoint_202_and_rate_limit(world, monkeypatch):
    _diff_deps(world, monkeypatch)
    set_id = uuid4()
    with world.client() as c:
        world.setup(c)
        first = c.post(
            "/chat/prep/observe",
            json={"set_id": str(set_id), "topic_skill_id": "algebra"},
        )
        second = c.post(
            "/chat/prep/observe",
            json={"set_id": str(set_id), "topic_skill_id": "algebra"},
        )

    assert first.status_code == 202
    assert first.json()["since_event_id"] == 1
    assert world.events[0].type == EventType.observer_requested
    assert world.events[0].payload == {"reason": "button"}
    [(fn, kwargs)] = world.enqueued
    assert fn == "observe_chat" and kwargs["trigger"] == "requested"
    assert second.status_code == 429


def _extracted(event_id, chat_id, observations):
    return Event(
        id=event_id,
        type=EventType.observation_extracted,
        student_id=uuid4(),
        chat_id=chat_id,
        occurred_at=NOW,
        ingested_at=NOW,
        payload={
            "observations": observations,
            "window_from_event_id": 1,
            "window_to_event_id": 2,
            "topic_skill_id": "algebra",
            "set_id": str(uuid4()),
            "exam_id": "SAT_MATH",
            "model": "m",
            "raw_count": len(observations),
        },
    )


def test_observations_diff_pending_done_failed(world, monkeypatch):
    _diff_deps(world, monkeypatch)
    set_id = uuid4()
    chat_id = uuid5(world.student_id, f"prep:{set_id}:algebra")
    listing: dict = {
        EventType.observation_extracted: [],
        EventType.job_failed: [],
        EventType.task_answered: [],
    }

    async def list_by_type(_s, _sid, types, _since, _limit, **kw):
        return listing[types[0]]

    message_id = uuid4()
    monkeypatch.setattr(chat.store, "list_by_type", list_by_type)
    monkeypatch.setattr(
        chat.messages, "list_by_event_ids", AsyncMock(return_value={11: message_id})
    )
    view = SkillStateView(
        skill_id="algebra",
        name="Алгебра",
        area_id="alg",
        exam_id="SAT_MATH",
        weight=1,
        p_target=0.9,
        level="shaky",
        p_recall=0.5,
        confidence=0.5,
        trend="flat",
        due_at=None,
        is_root=False,
        n_evidence=1,
    )
    monkeypatch.setattr(
        chat.apply_knowledge, "states_view", AsyncMock(return_value=[view])
    )
    monkeypatch.setattr(
        chat.apply_knowledge, "misconceptions_view", AsyncMock(return_value=[])
    )
    url = (
        f"/chat/prep/observations?set_id={set_id}"
        "&topic_skill_id=algebra&since_event_id=10"
    )

    with world.client() as c:
        world.setup(c)
        pending = c.get(url).json()
        listing[EventType.job_failed] = [
            Event(
                id=12,
                type=EventType.job_failed,
                student_id=uuid4(),
                chat_id=chat_id,
                occurred_at=NOW,
                ingested_at=NOW,
                payload={
                    "job": "observe_chat",
                    "job_id": "j",
                    "reason": "llm_down",
                    "args": {},
                },
            )
        ]
        failed = c.get(url).json()
        listing[EventType.observation_extracted] = [
            _extracted(
                13,
                chat_id,
                [
                    {
                        "kind": "question",
                        "skill_id": "algebra",
                        "event_ids": [11],
                        "confidence": 0.9,
                    }
                ],
            )
        ]
        done_response = c.get(url)

    assert pending["status"] == "pending"
    assert failed["status"] == "failed" and failed["failed_reason"] == "llm_down"
    done = done_response.json()
    assert done["status"] == "done"
    assert done["observations"][0]["message_ids"] == [str(message_id)]
    assert done["observations"][0]["skill_name"] == "Алгебра"
    assert done["observations"][0]["applied"] is False  # graph down: nothing confirmed
    assert [s["skill_id"] for s in done["skills"]] == ["algebra"]
    assert "x-knowledge-version" in done_response.headers


def test_observations_diff_empty_done(world, monkeypatch):
    _diff_deps(world, monkeypatch)
    set_id = uuid4()
    chat_id = uuid5(world.student_id, f"prep:{set_id}:algebra")

    async def list_by_type(_s, _sid, types, _since, _limit, **kw):
        return (
            [_extracted(13, chat_id, [])]
            if types[0] == EventType.observation_extracted
            else []
        )

    monkeypatch.setattr(chat.store, "list_by_type", list_by_type)
    monkeypatch.setattr(chat.messages, "list_by_event_ids", AsyncMock(return_value={}))
    monkeypatch.setattr(chat.apply_knowledge, "states_view", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        chat.apply_knowledge, "misconceptions_view", AsyncMock(return_value=[])
    )
    with world.client() as c:
        world.setup(c)
        body = c.get(
            f"/chat/prep/observations?set_id={set_id}&topic_skill_id=algebra"
        ).json()
    assert body["status"] == "done" and body["observations"] == []


def test_observations_diff_foreign_set_404(world, monkeypatch):
    _diff_deps(world, monkeypatch, owned=False)
    with world.client() as c:
        world.setup(c)
        response = c.get(f"/chat/prep/observations?set_id={uuid4()}")
    assert response.status_code == 404


async def test_parallel_turns_same_chat_second_409(world):
    gate = asyncio.Event()
    world.script = [TextDelta(text="…"), gate, Done(event_id=0)]
    world.app.state.llm = object()
    world.app.state.sessionmaker = FakeSession
    world.app.state.redis = world.redis
    world.app.state.arq = None
    world.app.state.neo4j = None
    transport = httpx.ASGITransport(app=world.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"quack_token": world.token},
    ) as client:

        async def first():
            return await client.post("/chat/selection/messages", json={"text": "a"})

        async def second():
            await asyncio.sleep(0.2)
            response = await client.post("/chat/selection/messages", json={"text": "b"})
            gate.set()
            return response

        one, two = await asyncio.gather(first(), second())

    assert one.status_code == 200
    assert two.status_code == 409
    assert [
        e.payload["text"] for e in world.events if e.type == EventType.message_user
    ] == ["a"]
