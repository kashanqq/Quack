"""Chat transport tests with a fake implementation of the agreed B2 interface."""

import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4, uuid5

from fastapi.testclient import TestClient

from app.api import chat, sse
from app.api.auth import issue_token
from app.errors import LLMUnavailable
from app.main import create_app
from app.schemas.chat import Done, MessageOut, TextDelta


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def commit(self):
        pass


def _events(response):
    return [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


def _setup(monkeypatch, script):
    student_id = uuid4()
    saved_events = []
    saved_messages = []

    async def append(_session, _redis, event, deps=None, *, dispatch_event=True):
        # Реплики чата — окно наблюдателя: транспорт обязан просить
        # «не диспетчеризовать» явно, а не полагаться на deps=None.
        assert dispatch_event is False
        saved_events.append(event)
        return SimpleNamespace(id=len(saved_events))

    async def append_message(
        _session, student_id, chat_id, role, text, markup, event_id
    ):
        saved_messages.append((student_id, chat_id, role, text, markup, event_id))
        return uuid4()

    async def list_messages(_session, student_id, chat_id, limit):
        return [
            MessageOut(
                id=uuid4(),
                role=role,
                text=text,
                markup=markup,
                event_id=event_id,
                created_at=datetime.now(UTC),
            )
            for sid, cid, role, text, markup, event_id in saved_messages
            if sid == student_id and cid == chat_id
        ][:limit]

    async def session_id(_redis, _student_id):
        return uuid4()

    async def run_chat(_kind, _ctx, _message, _deps):
        for event in script:
            if isinstance(event, Exception):
                raise event
            yield event

    monkeypatch.setattr(chat.store, "append", append)
    monkeypatch.setattr(chat.messages, "append_message", append_message)
    monkeypatch.setattr(chat.messages, "list_messages", list_messages)
    monkeypatch.setattr(chat, "current_session_id", session_id)
    monkeypatch.setattr(
        chat,
        "_agent_router",
        lambda: SimpleNamespace(AgentDeps=SimpleNamespace, run_chat=run_chat),
    )
    app = create_app()
    token = issue_token(student_id, "student@quack.kz")
    return app, token, student_id, saved_events, saved_messages


def test_three_deltas_done_two_events_history_and_stable_chat_id(monkeypatch):
    script = [
        TextDelta(text="one"),
        TextDelta(text=" two"),
        TextDelta(text=" three"),
        Done(event_id=0, mode="explain"),
    ]
    app, token, student_id, saved_events, saved_messages = _setup(monkeypatch, script)
    with TestClient(app) as client:
        app.state.llm = object()
        app.state.sessionmaker = FakeSession
        client.cookies.set("quack_token", token)
        response = client.post("/chat/selection/messages", json={"text": "hello"})
        history = client.get("/chat/selection/messages")
        second = client.post("/chat/selection/messages", json={"text": "again"})

    stream = _events(response)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    assert [event["type"] for event in stream] == [
        "text_delta",
        "text_delta",
        "text_delta",
        "done",
    ]
    assert stream[-1]["event_id"] == 2
    assert [event.type for event in saved_events[:2]] == [
        "message.user",
        "message.assistant",
    ]
    expected_chat_id = uuid5(student_id, "selection")
    assert all(event.chat_id == expected_chat_id for event in saved_events)
    assert [message[2] for message in saved_messages[:2]] == ["user", "assistant"]
    assert saved_messages[1][3] == "one two three"
    assert [message["role"] for message in history.json()] == ["user", "assistant"]
    assert _events(second)[-1]["event_id"] == 4


def test_agent_error_is_last_without_assistant_write(monkeypatch):
    app, token, _, saved_events, saved_messages = _setup(
        monkeypatch, [TextDelta(text="partial"), RuntimeError("private detail")]
    )
    with TestClient(app) as client:
        app.state.llm = object()
        app.state.sessionmaker = FakeSession
        client.cookies.set("quack_token", token)
        response = client.post("/chat/selection/messages", json={"text": "hello"})
    stream = _events(response)
    assert [event["type"] for event in stream] == ["text_delta", "error"]
    assert "private detail" not in response.text
    assert [event.type for event in saved_events] == ["message.user"]
    assert [message[2] for message in saved_messages] == ["user"]


def test_oversized_text_rejected_before_stream(monkeypatch):
    app, token, _, saved_events, _ = _setup(monkeypatch, [])
    with TestClient(app) as client:
        app.state.llm = object()
        client.cookies.set("quack_token", token)
        response = client.post("/chat/selection/messages", json={"text": "x" * 4001})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_failed"
    assert saved_events == []


def test_missing_b2_returns_503_before_write(monkeypatch):
    agent_router = chat._agent_router
    app, token, _, saved_events, _ = _setup(monkeypatch, [])
    monkeypatch.setattr(chat, "_agent_router", agent_router)

    def missing(_name):
        exc = ModuleNotFoundError("No module named 'app.agents'")
        exc.name = "app.agents"
        raise exc

    monkeypatch.setattr(chat, "import_module", missing)
    with TestClient(app) as client:
        client.cookies.set("quack_token", token)
        response = client.post("/chat/selection/messages", json={"text": "hello"})
    assert response.status_code == 503
    assert saved_events == []


def test_llm_unavailable_before_first_event_is_http_503(monkeypatch):
    app, token, _, saved_events, _ = _setup(
        monkeypatch, [LLMUnavailable("provider down")]
    )
    with TestClient(app) as client:
        app.state.llm = object()
        app.state.sessionmaker = FakeSession
        client.cookies.set("quack_token", token)
        response = client.post("/chat/selection/messages", json={"text": "hello"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_unavailable"
    assert [event.type for event in saved_events] == ["message.user"]


def test_prep_chat_id_uses_set_and_skill(monkeypatch):
    app, token, student_id, saved_events, _ = _setup(monkeypatch, [Done(event_id=0)])
    set_id = uuid4()
    with TestClient(app) as client:
        app.state.llm = object()
        app.state.sessionmaker = FakeSession
        client.cookies.set("quack_token", token)
        response = client.post(
            "/chat/prep/messages",
            json={"text": "hello", "set_id": str(set_id), "topic_skill_id": "algebra"},
        )
    assert response.status_code == 200
    expected = uuid5(student_id, f"prep:{set_id}:algebra")
    assert all(event.chat_id == expected for event in saved_events)


async def test_sse_keepalive_does_not_cancel_pending_event(monkeypatch):
    real_wait = asyncio.wait
    calls = 0

    async def wait_once(tasks, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            return set(), tasks
        return await real_wait(tasks, timeout=timeout)

    async def source():
        yield TextDelta(text="after wait")
        yield Done(event_id=3)

    monkeypatch.setattr(sse.asyncio, "wait", wait_once)
    frames = [frame async for frame in sse._frames(source())]
    assert frames[0] == ": keepalive\n\n"
    assert json.loads(frames[1][6:])["text"] == "after wait"
    assert json.loads(frames[2][6:])["type"] == "done"
