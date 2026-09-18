"""Event-store ordering, validation, and SQL contracts without live services."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.events import dispatch as dispatcher
from app.events import store
from app.schemas.events import EventIn, EventType

pytestmark = pytest.mark.phase1


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(dispatcher, "_handlers", {})


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> bytes | None:
        value = self.values.get(key)
        return value.encode() if value is not None else None

    async def set(self, key: str, value: str, ex: int) -> None:
        self.values[key] = value


class FakeSession:
    def __init__(self, rows=None) -> None:
        self.statements = []
        self.rows = rows or []
        self.commit = AsyncMock()

    async def execute(self, statement):
        self.statements.append(statement)
        if statement.is_insert:
            return SimpleNamespace(one=lambda: (42, datetime.now(UTC)))
        return SimpleNamespace()

    async def scalars(self, statement):
        self.statements.append(statement)
        return self.rows


def _event_in(**overrides) -> EventIn:
    fields = {
        "student_id": uuid4(),
        "type": EventType.profile_updated,
        "payload": {"field": "level.grade", "value": 11, "by": "user"},
    }
    fields.update(overrides)
    return EventIn(**fields)


async def test_append_fills_session_and_utc_time_then_dispatches_once():
    session = FakeSession()
    redis = FakeRedis()
    handled = AsyncMock()
    dispatcher.on(EventType.profile_updated)(handled)
    before = datetime.now(UTC)

    event = await store.append(session, redis, _event_in())

    assert event.id == 42
    assert event.session_id is not None
    assert before <= event.occurred_at <= datetime.now(UTC)
    assert event.ingested_at.tzinfo is not None
    assert handled.await_count == 1
    assert handled.await_args.args[:2] == (session, event)
    assert isinstance(handled.await_args.args[2], dispatcher.RuleDeps)
    values = session.statements[0].compile().params
    assert values["session_id"] == event.session_id
    assert values["occurred_at"] == event.occurred_at
    assert values["payload"] == event.payload
    session.commit.assert_not_awaited()


async def test_append_respects_explicit_session_and_time():
    session = FakeSession()
    redis = FakeRedis()
    session_id = uuid4()
    occurred_at = datetime(2026, 1, 2, tzinfo=UTC)

    event = await store.append(
        session,
        redis,
        _event_in(session_id=session_id, occurred_at=occurred_at),
    )

    assert event.session_id == session_id
    assert event.occurred_at == occurred_at
    assert redis.values == {}


async def test_invalid_known_payload_is_rejected_before_insert():
    session = FakeSession()
    with pytest.raises(ValidationError):
        await store.append(
            session,
            FakeRedis(),
            _event_in(payload={"field": "level.grade", "value": 11, "by": "other"}),
        )
    assert session.statements == []


async def test_payload_schema_requires_assistant_references_and_serializes_uuid():
    session = FakeSession()
    redis = FakeRedis()
    with pytest.raises(ValidationError):
        await store.append(
            session,
            redis,
            _event_in(type=EventType.message_assistant, payload={"text": "hello"}),
        )
    assert session.statements == []

    instance_id = uuid4()
    event = await store.append(
        session,
        redis,
        _event_in(
            type=EventType.task_issued,
            payload={
                "instance_id": instance_id,
                "template_id": "t1",
                "skill_id": "skill1",
                "mode": "topic",
                "via": "topic",
            },
        ),
    )
    assert event.payload["instance_id"] == str(instance_id)
    assert session.statements[0].compile().params["payload"] == event.payload


async def test_handler_failure_propagates_without_store_commit():
    session = FakeSession()

    @dispatcher.on(EventType.profile_updated)
    async def fail(db, event, deps):
        raise RuntimeError("handler failed")

    with pytest.raises(RuntimeError, match="handler failed"):
        await store.append(session, FakeRedis(), _event_in())
    assert len(session.statements) == 1
    session.commit.assert_not_awaited()


def _row(event_id: int, student_id, chat_id):
    return SimpleNamespace(
        id=event_id,
        student_id=student_id,
        session_id=uuid4(),
        exam_id=None,
        set_id=None,
        topic_skill_id=None,
        chat_id=chat_id,
        type=EventType.message_user.value,
        payload={"text": "hello"},
        occurred_at=datetime.now(UTC),
        ingested_at=datetime.now(UTC),
        processed_at=None,
        extractor_version=None,
        source_event_ids=None,
    )


async def test_list_unprocessed_and_mark_processed_queries():
    student_id = uuid4()
    chat_id = uuid4()
    session = FakeSession([_row(7, student_id, chat_id)])

    events = await store.list_unprocessed(session, chat_id, limit=10)
    assert [event.id for event in events] == [7]
    query = str(session.statements[0])
    assert "events.chat_id =" in query
    assert "events.processed_at IS NULL" in query
    assert "ORDER BY events.id" in query
    assert "LIMIT" in query

    await store.mark_processed(session, [7])
    statement = session.statements[1]
    assert statement.is_update
    assert "events.id IN" in str(statement)
    assert statement.compile().params["processed_at"].tzinfo is not None
    session.commit.assert_not_awaited()

    await store.mark_processed(session, [])
    assert len(session.statements) == 2


async def test_list_events_is_scoped_to_student_type_and_time():
    student_id = uuid4()
    since = datetime.now(UTC) - timedelta(days=1)
    session = FakeSession([_row(8, student_id, uuid4())])

    events = await store.list_events(
        session, student_id, types=[EventType.message_user], since=since, limit=5
    )

    assert [event.id for event in events] == [8]
    query = str(session.statements[0])
    params = session.statements[0].compile().params
    assert "events.student_id =" in query
    assert "events.type IN" in query
    assert "events.occurred_at >=" in query
    assert student_id in params.values()
    assert since in params.values()
