"""PostgreSQL and Redis transaction checks; opt in with test service URLs."""

import os
from uuid import uuid4

import pytest
from redis.asyncio import Redis
from sqlalchemy.engine import make_url

from app.config import Settings
from app.db.engine import close_engine, create_engine, create_sessionmaker
from app.db.models import Event as EventRow
from app.events import dispatch as dispatcher
from app.events import store
from app.keys import session as session_key
from app.schemas.events import EventIn, EventType

pytestmark = [pytest.mark.phase1, pytest.mark.integration]


async def test_event_lifecycle_and_handler_rollback(monkeypatch):
    database_url = os.environ.get("TEST_DATABASE_URL")
    redis_url = os.environ.get("TEST_REDIS_URL")
    if not database_url or not redis_url:
        pytest.skip(
            "Set TEST_DATABASE_URL and TEST_REDIS_URL to migrated test services"
        )
    if make_url(database_url).database != "quack_test":
        pytest.fail("Event integration test requires the quack_test database")

    monkeypatch.setattr(dispatcher, "_handlers", {})
    engine = create_engine(Settings(ENV="local", DATABASE_URL=database_url))
    redis = Redis.from_url(redis_url)
    student_id = uuid4()
    chat_id = uuid4()
    key = session_key(str(student_id))
    try:
        await redis.delete(key)
        factory = create_sessionmaker(engine)
        async with factory() as db:
            first = await store.append(
                db,
                redis,
                EventIn(
                    type=EventType.message_user,
                    payload={"text": "hello"},
                    student_id=student_id,
                    chat_id=chat_id,
                ),
            )
            again = await store.append(
                db,
                redis,
                EventIn(
                    type=EventType.message_user,
                    payload={"text": "again"},
                    student_id=student_id,
                    chat_id=chat_id,
                ),
            )
            assert first.session_id == again.session_id
            assert [ev.id for ev in await store.list_unprocessed(db, chat_id)] == [
                first.id,
                again.id,
            ]
            await store.mark_processed(db, [first.id, again.id])
            assert await store.list_unprocessed(db, chat_id) == []
            assert len(await store.list_events(db, student_id)) == 2
            await db.rollback()

            await redis.delete(key)
            fresh = await store.append(
                db,
                redis,
                EventIn(
                    type=EventType.message_user,
                    payload={"text": "fresh"},
                    student_id=student_id,
                    chat_id=chat_id,
                ),
            )
            assert fresh.session_id != first.session_id
            await db.rollback()

            failed_id = None

            @dispatcher.on(EventType.profile_updated)
            async def fail(session, event):
                nonlocal failed_id
                failed_id = event.id
                raise RuntimeError("handler failed")

            with pytest.raises(RuntimeError, match="handler failed"):
                await store.append(
                    db,
                    redis,
                    EventIn(
                        type=EventType.profile_updated,
                        payload={"field": "level.grade", "value": 11, "by": "user"},
                        student_id=student_id,
                    ),
                )
            await db.rollback()
            assert failed_id is not None
            assert await db.get(EventRow, failed_id) is None
    finally:
        await redis.delete(key)
        await redis.aclose()
        await close_engine(engine)
