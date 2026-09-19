"""jobs.observe_chat — window, event, retries, requeue
(docs/tz/phase3-agents.md §3.9, §6.8)."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import openai
import pytest
from arq import Retry

from app import keys
from app.agents import jobs
from app.errors import LLMUnavailable
from app.llm.fake import FakeLLMClient
from app.schemas.events import EventType
from app.schemas.observer import (
    Observation,
    ObservationApplyResult,
    ObservationOut,
    ObserverContext,
)
from tests.agents._jobs_fakes import (
    MemoryStore,
    arq_ctx,
    no_messages_repo,
    patch_store,
    set_out,
)

pytestmark = pytest.mark.phase3

SKILL = "math.alg.abs_value_eq"


@pytest.fixture
def world(monkeypatch, redis, fake_enqueue):
    memory = MemoryStore()
    patch_store(monkeypatch, jobs, memory)
    no_messages_repo(monkeypatch, jobs)
    student_id, chat_id, set_id = uuid4(), uuid4(), uuid4()
    monkeypatch.setattr(
        jobs.sets_repo, "get_set", AsyncMock(return_value=set_out(set_id))
    )
    monkeypatch.setattr(
        jobs.tasks_repo, "list_open_chat_instances", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(jobs.tasks_repo, "list_instances", AsyncMock(return_value=[]))
    monkeypatch.setattr(jobs.tasks_repo, "issued_event_ids", AsyncMock(return_value={}))
    monkeypatch.setattr(
        jobs,
        "_observer_context",
        AsyncMock(return_value=ObserverContext(skills=[], misconceptions=[])),
    )
    dispatched = AsyncMock(
        return_value={"apply_observation_extracted": ObservationApplyResult(event_id=0)}
    )
    monkeypatch.setattr(jobs.dispatch, "dispatch", dispatched)

    def message(role="user", processed=False, text="x"):
        return memory.add(
            EventType.message_user if role == "user" else EventType.message_assistant,
            chat_id=chat_id,
            student_id=student_id,
            set_id=set_id,
            topic_skill_id=SKILL,
            payload={"text": text}
            if role == "user"
            else {"text": text, "referenced_skill_ids": []},
            processed=processed,
        )

    return type(
        "World",
        (),
        {
            "memory": memory,
            "student_id": student_id,
            "chat_id": chat_id,
            "set_id": set_id,
            "message": staticmethod(message),
            "dispatch": dispatched,
            "enqueued": fake_enqueue,
            "redis": redis,
        },
    )


def _out(*event_ids, confidence=0.9) -> ObservationOut:
    return ObservationOut(
        observations=[
            Observation(
                kind="solution_step",
                outcome="incorrect",
                skill_id=SKILL,
                event_ids=list(event_ids),
                confidence=confidence,
            )
        ]
    )


async def _run(world, llm, trigger="every_n", **ctx_kw):
    ctx = arq_ctx(llm, world.redis, **ctx_kw)
    await jobs.observe_chat(ctx, "req", world.chat_id, world.student_id, trigger)
    return ctx


async def test_window_selects_unprocessed_messages_only(world):
    world.message(processed=True)
    world.message("assistant", processed=True)
    fresh = [world.message(), world.message("assistant")]
    task = world.memory.add(
        EventType.task_issued,
        chat_id=world.chat_id,
        student_id=world.student_id,
        payload={"instance_id": str(uuid4())},
    )
    fresh += [world.message(), world.message("assistant")]
    requested = world.memory.add(
        EventType.observer_requested, chat_id=world.chat_id, student_id=world.student_id
    )
    llm = FakeLLMClient([_out(fresh[0].id)])

    await _run(world, llm)

    [event] = world.memory.of(EventType.observation_extracted)
    assert event.source_event_ids == sorted([e.id for e in fresh] + [task.id])
    assert set(world.memory.processed) == {*event.source_event_ids, requested.id}


async def test_window_max_and_requeue(world, monkeypatch):
    monkeypatch.setattr(jobs.settings.KNOWLEDGE, "observer_window_max", 30)
    monkeypatch.setattr(jobs.settings.KNOWLEDGE, "observer_every_n", 6)
    for i in range(40):
        world.message("user" if i % 2 == 0 else "assistant")
    llm = FakeLLMClient([ObservationOut(observations=[])])

    await _run(world, llm)

    [event] = world.memory.of(EventType.observation_extracted)
    assert len(event.source_event_ids) == 30
    [(queue, fn, kwargs)] = [c for c in world.enqueued if c[1] == "observe_chat"]
    assert queue == "interactive"
    assert kwargs["_job_id"].startswith(f"observe:{world.chat_id}")
    assert kwargs["trigger"] == "every_n"


async def test_empty_window_no_event(world):
    llm = FakeLLMClient()

    await _run(world, llm)

    assert world.memory.appended == []
    assert llm.calls == []


async def test_empty_window_requested_writes_empty_event(world):
    world.memory.add(
        EventType.observer_requested,
        chat_id=world.chat_id,
        student_id=world.student_id,
        set_id=world.set_id,
        topic_skill_id=SKILL,
    )
    llm = FakeLLMClient()

    await _run(world, llm, trigger="requested")

    [event] = world.memory.of(EventType.observation_extracted)
    assert event.payload["observations"] == []
    assert event.source_event_ids == []
    assert llm.calls == []


async def test_event_written_with_extractor_version_and_sources(world):
    first = world.message()
    second = world.message("assistant")
    out = ObservationOut(
        observations=[
            *_out(first.id).observations,
            *_out(second.id, confidence=0.3).observations,
        ]
    )

    await _run(world, FakeLLMClient([out]))

    [event] = world.memory.of(EventType.observation_extracted)
    assert event.extractor_version == "observer_v1"
    assert event.chat_id == world.chat_id
    assert [o["confidence"] for o in event.payload["observations"]] == [0.9, 0.3]
    assert set(world.memory.processed) >= {first.id, second.id}
    world.dispatch.assert_awaited_once()


async def test_dispatch_result_used_for_canonization_enqueue(world):
    world.message()
    world.dispatch.return_value = {
        "apply_observation_extracted": ObservationApplyResult(
            event_id=1, pending_canonizations=[2]
        )
    }

    await _run(world, FakeLLMClient([ObservationOut(observations=[])]))

    [event] = [
        e for e in world.memory.events if e.type == EventType.observation_extracted
    ]
    canon = [c for c in world.enqueued if c[1] == "canonize_misconception"]
    assert canon[0][2]["_job_id"] == f"canon:{event.id}:2"
    assert canon[0][2]["ordinal"] == 2


async def test_lock_skips_second_run(world):
    world.message()
    await world.redis.set(keys.lock(f"observe:{world.chat_id}"), "other")
    llm = FakeLLMClient()

    await _run(world, llm)

    assert llm.calls == []
    assert world.memory.appended == []


async def test_lock_released_after_run(world):
    world.message()
    await _run(world, FakeLLMClient([ObservationOut(observations=[])]))
    assert await world.redis.get(keys.lock(f"observe:{world.chat_id}")) is None


def _timeout_error():
    import httpx

    return openai.APITimeoutError(request=httpx.Request("POST", "https://x"))


async def test_transient_error_retries(world):
    world.message()
    with pytest.raises(Retry):
        await _run(world, FakeLLMClient([_timeout_error()]), job_try=1)
    assert world.memory.of(EventType.job_failed) == []

    await _run(world, FakeLLMClient([_timeout_error()]), job_try=3)
    [failed] = world.memory.of(EventType.job_failed)
    assert failed.payload["job"] == "observe_chat"
    assert failed.payload["reason"] == "llm_unavailable"
    assert world.memory.processed == []


async def test_invalid_structured_no_retry(world):
    world.message()

    await _run(world, FakeLLMClient(["bad", "bad"]), job_try=1)

    [failed] = world.memory.of(EventType.job_failed)
    assert failed.payload["reason"] == "invalid_structured_output"
    assert world.memory.processed == []


async def test_forced_down_fails_without_retry(world):
    world.message()
    llm = FakeLLMClient([LLMUnavailable("llm unavailable (forced down)")])
    llm.forced_status = "down"

    await _run(world, llm, job_try=1)

    [failed] = world.memory.of(EventType.job_failed)
    assert failed.payload["reason"] == "llm_down"


async def test_graph_none_retries_then_fails(world):
    world.message()
    with pytest.raises(Retry):
        await _run(world, FakeLLMClient(), graph=None, job_try=1)

    await _run(world, FakeLLMClient(), graph=None, job_try=3)
    [failed] = world.memory.of(EventType.job_failed)
    assert failed.payload["reason"] == "graph_unavailable"


async def test_selection_chat_is_skipped(world):
    world.memory.add(
        EventType.message_user, chat_id=world.chat_id, student_id=world.student_id
    )
    llm = FakeLLMClient()

    await _run(world, llm)

    assert llm.calls == []
    assert world.memory.appended == []
