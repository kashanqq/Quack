"""Phase 2 dispatch, registry, version and event query contracts."""

import importlib
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from neo4j.exceptions import ServiceUnavailable, SessionExpired

from app.config import KnowledgeParams
from app.events import dispatch as dispatcher
from app.events import store, version
from app.schemas.events import Event, EventType


def _event(event_type: EventType = EventType.task_answered) -> Event:
    now = datetime.now(UTC)
    return Event(
        id=7,
        type=event_type,
        payload={},
        student_id=uuid4(),
        occurred_at=now,
        ingested_at=now,
    )


_GRAPH = object()


def _deps(graph=_GRAPH) -> dispatcher.RuleDeps:
    return dispatcher.RuleDeps(
        graph, object(), KnowledgeParams(), lambda: datetime.now(UTC)
    )


@pytest.fixture
def empty_registry(monkeypatch):
    monkeypatch.setattr(dispatcher, "_handlers", {})


async def test_dispatch_returns_results_in_registration_order_and_marks_processed(
    empty_registry, monkeypatch
):
    calls = []
    marked = AsyncMock()
    monkeypatch.setattr(store, "mark_processed", marked)

    @dispatcher.on(EventType.task_answered)
    async def first(session, event, deps):
        calls.append("first")
        return "one"

    @dispatcher.on(EventType.task_answered)
    async def second(session, event, deps):
        calls.append("second")
        return "two"

    session = object()
    event = _event()
    assert await dispatcher.dispatch(session, event, _deps()) == {
        "first": "one",
        "second": "two",
    }
    assert calls == ["first", "second"]
    marked.assert_awaited_once_with(session, [event.id])
    assert event.processed_at is not None


async def test_dispatch_rethrows_ordinary_error_without_marking(
    empty_registry, monkeypatch
):
    marked = AsyncMock()
    later = AsyncMock()
    monkeypatch.setattr(store, "mark_processed", marked)

    @dispatcher.on(EventType.task_answered)
    async def failing(session, event, deps):
        raise RuntimeError("unexpected failure")

    dispatcher.on(EventType.task_answered)(later)
    with pytest.raises(RuntimeError, match="unexpected failure"):
        await dispatcher.dispatch(object(), _event(), _deps())
    later.assert_not_awaited()
    marked.assert_not_awaited()


@pytest.mark.parametrize(
    "result",
    [
        dispatcher.GraphUnavailable,
        ServiceUnavailable("down"),
        SessionExpired("expired"),
    ],
)
async def test_graph_unavailable_does_not_mark_processed(
    empty_registry, monkeypatch, result
):
    marked = AsyncMock()
    monkeypatch.setattr(store, "mark_processed", marked)

    @dispatcher.on(EventType.task_answered)
    async def graph_handler(session, event, deps):
        if isinstance(result, Exception):
            raise result
        return result

    event = _event()
    await dispatcher.dispatch(object(), event, _deps())
    marked.assert_not_awaited()
    assert event.processed_at is None


async def test_missing_graph_does_not_mark_processed(empty_registry, monkeypatch):
    marked = AsyncMock()
    monkeypatch.setattr(store, "mark_processed", marked)

    @dispatcher.on(EventType.task_answered)
    async def fallback(session, event, deps):
        return "grade without state"

    assert (await dispatcher.dispatch(object(), _event(), _deps(None)))["fallback"] == (
        "grade without state"
    )
    marked.assert_not_awaited()


def test_handlers_exact_mapping(empty_registry):
    from app.events import handlers

    dispatcher._handlers.clear()
    importlib.reload(handlers)
    expected = {
        EventType.task_answered: "apply_task_answered",
        EventType.task_skipped: "apply_task_skipped",
        EventType.task_timed_out: "apply_task_skipped",
        EventType.profile_updated: "apply_profile_updated",
        EventType.program_saved: "on_program_change",
        EventType.program_removed: "on_program_change",
        EventType.set_switched_by_user: "on_set_change",
        EventType.set_deadline_changed: "on_set_change",
        EventType.misconception_disputed: "apply_dispute",
        EventType.misconception_undisputed: "apply_dispute",
        EventType.diagnostic_completed: "on_run_completed",
        EventType.mock_completed: "on_run_completed",
    }
    assert {
        event_type: [handler.__name__ for handler in functions]
        for event_type, functions in dispatcher._handlers.items()
    } == {event_type: [name] for event_type, name in expected.items()}
    assert dispatcher._handlers.get(EventType.topic_opened, []) == []
    assert dispatcher._handlers.get(EventType.set_opened, []) == []


class FakeRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def incr(self, key):
        value = int(self.values.get(key, 0)) + 1
        self.values[key] = str(value).encode()
        return value


async def test_knowledge_version_starts_at_zero_and_increments():
    redis = FakeRedis()
    student_id = uuid4()
    assert await version.get(redis, student_id) == 0
    assert await version.bump(redis, student_id) == 1
    assert await version.bump(redis, student_id) == 2
    assert await version.get(redis, student_id) == 2
    assert list(redis.values) == [f"quack:knowledge:version:{student_id}"]


class QuerySession:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None

    async def scalars(self, statement):
        self.statement = statement
        return self.rows


async def test_list_by_type_filters_student_types_since_and_limit():
    student_id = uuid4()
    since = datetime(2026, 9, 1, tzinfo=UTC)
    event = _event()
    row = SimpleNamespace(**event.model_dump())
    session = QuerySession([row])
    assert [
        item.id
        for item in await store.list_by_type(
            session, student_id, [EventType.task_answered], since, 3
        )
    ] == [7]
    sql = str(session.statement)
    params = session.statement.compile().params
    assert "events.student_id =" in sql
    assert "events.type IN" in sql
    assert "events.occurred_at >=" in sql
    assert "ORDER BY events.id" in sql
    assert student_id in params.values()
    assert since in params.values()
    assert 3 in params.values()
