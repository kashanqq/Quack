"""Sets router hooks of phase 3: the observer after a topic/set is completed
and the context cache invalidation (docs/tz/phase3-agents.md §3.12, §6.11)."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid5

import pytest

from app import keys
from app.api import deps
from app.api import sets as sets_api
from tests.api.test_sets_knowledge_phase2 import _client, _set, transport  # noqa: F401

pytestmark = pytest.mark.phase3


@pytest.fixture
def hooks(transport, monkeypatch):  # noqa: F811
    enqueued: list[dict] = []

    async def enqueue(arq, queue, fn_name, **kwargs):
        enqueued.append({"queue": queue, "fn": fn_name, **kwargs})
        return kwargs["_job_id"]

    monkeypatch.setattr(sets_api, "enqueue", enqueue)
    transport.app.dependency_overrides[deps.get_arq] = lambda: object()
    transport.deps.redis.delete = AsyncMock()
    return enqueued


def test_topic_completed_enqueues_and_invalidates(transport, hooks, monkeypatch):  # noqa: F811
    monkeypatch.setattr(sets_api.store, "count_unprocessed", AsyncMock(return_value=0))
    item = _set(transport.student_id, status="current", skills=("a", "b"))
    transport.rows[(transport.student_id, item.id)] = item

    with _client(transport) as client:
        response = client.post(f"/sets/{item.id}/topics/a/complete")

    assert response.status_code == 200
    [job] = hooks
    assert job["fn"] == "observe_chat" and job["trigger"] == "topic_completed"
    chat_id = uuid5(transport.student_id, f"prep:{item.id}:a")
    assert job["_job_id"] == f"observe:{chat_id}"
    deleted = transport.deps.redis.delete.call_args.args
    assert keys.ctx_topic(str(transport.student_id), "a") in deleted
    assert keys.ctx_topic(str(transport.student_id), f"set:{item.id}") in deleted


def test_set_completed_enqueues_each_topic_chat(transport, hooks, monkeypatch):  # noqa: F811
    item = _set(transport.student_id, status="current", skills=("a", "b", "c"))
    transport.rows[(transport.student_id, item.id)] = item
    with_messages = {
        uuid5(transport.student_id, f"prep:{item.id}:b"),
        uuid5(transport.student_id, f"prep:{item.id}"),
    }

    async def count(_session, chat_id, _types):
        return 3 if chat_id in with_messages else 0

    monkeypatch.setattr(sets_api.store, "count_unprocessed", count)

    with _client(transport) as client:
        client.post(f"/sets/{item.id}/topics/a/complete")
        client.post(f"/sets/{item.id}/topics/b/complete")
        hooks.clear()
        client.post(f"/sets/{item.id}/topics/c/complete")

    triggers = {(job["chat_id"], job["trigger"]) for job in hooks}
    assert triggers == {
        (uuid5(transport.student_id, f"prep:{item.id}:c"), "topic_completed"),
        (uuid5(transport.student_id, f"prep:{item.id}:b"), "set_completed"),
        (uuid5(transport.student_id, f"prep:{item.id}"), "set_completed"),
    }
