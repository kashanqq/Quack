"""events.store phase-3 additions (docs/tz/phase3-agents.md §3.12, §6.11)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.events import store
from app.schemas.events import EventIn, EventType

pytestmark = pytest.mark.phase3


def _ev(type_, payload):
    return EventIn(type=type_, payload=payload, student_id=uuid4())


def test_payload_models_registered():
    observation = {
        "observations": [
            {"kind": "question", "skill_id": "s", "event_ids": [1], "confidence": 0.9}
        ],
        "window_from_event_id": 1,
        "window_to_event_id": 1,
        "topic_skill_id": "s",
        "set_id": str(uuid4()),
        "exam_id": "SAT_MATH",
        "model": "m",
        "raw_count": 1,
    }
    assert store._validated_payload(_ev(EventType.observation_extracted, observation))
    with pytest.raises(ValidationError):
        store._validated_payload(
            _ev(EventType.observation_extracted, {**observation, "extra": 1})
        )
    with pytest.raises(ValidationError):
        store._validated_payload(
            _ev(
                EventType.job_failed,
                {"job": "x", "job_id": None, "reason": "r", "args": {}, "x": 1},
            )
        )
    canonized = {
        "source_event_id": 1,
        "ordinal": 0,
        "skill_id": "s",
        "canonical_id": "lib.x",
        "similarity": 0.9,
        "decided_by": "threshold",
        "name": "n",
        "description": "d",
        "error_class": "conceptual",
    }
    assert store._validated_payload(_ev(EventType.misconception_canonized, canonized))
    with pytest.raises(ValidationError):
        store._validated_payload(
            _ev(EventType.misconception_canonized, {**canonized, "decided_by": "guess"})
        )
    assert store._validated_payload(
        _ev(EventType.observer_requested, {"reason": "button"})
    )


@pytest.mark.integration
async def test_store_list_unprocessed_types_and_count(db_session, redis):
    student_id, chat_id = uuid4(), uuid4()

    async def add(type_, payload):
        return await store.append(
            db_session,
            redis,
            EventIn(
                type=type_, payload=payload, student_id=student_id, chat_id=chat_id
            ),
            dispatch_event=False,
        )

    user = await add(EventType.message_user, {"text": "a"})
    await add(
        EventType.message_assistant,
        {"text": "b", "referenced_skill_ids": []},
    )
    await add(EventType.observer_requested, {"reason": "button"})

    only_user = await store.list_unprocessed(
        db_session, chat_id, types=[EventType.message_user]
    )
    assert [e.id for e in only_user] == [user.id]
    assert (
        await store.count_unprocessed(
            db_session, chat_id, [EventType.message_user, EventType.message_assistant]
        )
        == 2
    )
    await store.mark_processed(db_session, [user.id])
    assert (
        await store.count_unprocessed(db_session, chat_id, [EventType.message_user])
        == 0
    )

    assert (await store.get_event(db_session, student_id, user.id)).id == user.id
    assert await store.get_event(db_session, uuid4(), user.id) is None
