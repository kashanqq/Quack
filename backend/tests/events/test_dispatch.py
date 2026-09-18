"""Handler registration order and failure propagation."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.events import dispatch as dispatcher
from app.schemas.events import Event, EventType

pytestmark = pytest.mark.phase1


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(dispatcher, "_handlers", {})


def _event() -> Event:
    return Event(
        id=1,
        type=EventType.profile_updated,
        payload={"field": "level.grade", "value": 11, "by": "user"},
        student_id=uuid4(),
        session_id=uuid4(),
        occurred_at=datetime.now(UTC),
        ingested_at=datetime.now(UTC),
    )


async def test_handlers_run_once_in_registration_order():
    calls: list[str] = []
    session = object()
    event = _event()

    @dispatcher.on(EventType.profile_updated)
    async def first(received_session, received_event):
        assert received_session is session
        assert received_event is event
        calls.append("first")

    @dispatcher.on(EventType.profile_updated)
    async def second(received_session, received_event):
        calls.append("second")

    await dispatcher.dispatch(session, event)
    assert calls == ["first", "second"]


async def test_handler_failure_stops_later_handlers():
    later = AsyncMock()

    @dispatcher.on(EventType.profile_updated)
    async def failed(session, event):
        raise RuntimeError("handler failed")

    dispatcher.on(EventType.profile_updated)(later)
    with pytest.raises(RuntimeError, match="handler failed"):
        await dispatcher.dispatch(object(), _event())
    later.assert_not_awaited()
