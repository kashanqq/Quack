"""jobs.canonize_misconception — thresholds, adjudication, idempotency
(docs/tz/phase3-agents.md §3.11, §6.10)."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agents import jobs
from app.llm.fake import FakeLLMClient
from app.schemas.events import EventType, ObservationExtractedPayload
from app.schemas.knowledge import MisconceptionRef
from app.schemas.observer import CanonDecision, Observation
from tests.agents._jobs_fakes import MemoryStore, arq_ctx, patch_store

pytestmark = pytest.mark.phase3

SKILL = "math.alg.abs_value_eq"


class Embedder:
    def __init__(self, dim=384):
        self.dim = dim

    def embed(self, texts):
        return [[0.1] * self.dim for _ in texts]


def _ref(mid="lib.x") -> MisconceptionRef:
    return MisconceptionRef(
        id=mid,
        name="одна ветвь",
        description="теряет ветвь",
        error_class="conceptual",
        skill_ids=[SKILL],
    )


@pytest.fixture
def world(monkeypatch, redis):
    memory = MemoryStore()
    patch_store(monkeypatch, jobs, memory)
    dispatched = AsyncMock(return_value={})
    monkeypatch.setattr(jobs.dispatch, "dispatch", dispatched)
    monkeypatch.setattr(
        jobs.canonical_q, "get_misconception", AsyncMock(return_value=None)
    )
    student_id = uuid4()
    payload = ObservationExtractedPayload(
        observations=[
            Observation(kind="question", skill_id=SKILL, event_ids=[1], confidence=0.9),
            Observation(
                kind="proposed_misconception",
                name="Путает знак",
                description="меняет знак при переносе",
                error_class="procedural",
                skill_id=SKILL,
                event_ids=[1],
                confidence=0.9,
            ),
        ],
        window_from_event_id=1,
        window_to_event_id=1,
        topic_skill_id=SKILL,
        set_id=uuid4(),
        exam_id="SAT_MATH",
        model="m",
        raw_count=2,
    )
    source = memory.add(
        EventType.observation_extracted,
        chat_id=uuid4(),
        student_id=student_id,
        payload=payload.model_dump(mode="json"),
    )

    def search(results):
        monkeypatch.setattr(
            jobs.canonical_q, "search_misconceptions", AsyncMock(return_value=results)
        )

    return type(
        "W",
        (),
        {
            "memory": memory,
            "student_id": student_id,
            "source": source,
            "search": staticmethod(search),
            "dispatch": dispatched,
            "redis": redis,
        },
    )


async def _run(world, llm=None, ordinal=1, **kw):
    kw.setdefault("embedder", Embedder())
    ctx = arq_ctx(llm or FakeLLMClient(), world.redis, **kw)
    await jobs.canonize_misconception(
        ctx, "req", world.student_id, world.source.id, ordinal
    )


async def test_merge_above_threshold(world):
    world.search([(_ref("lib.x"), 0.95)])
    llm = FakeLLMClient()

    await _run(world, llm)

    [event] = world.memory.of(EventType.misconception_canonized)
    assert event.payload["canonical_id"] == "lib.x"
    assert event.payload["decided_by"] == "threshold"
    assert llm.calls == []
    world.dispatch.assert_awaited_once()


async def test_adjudicate_in_grey_zone_yes(world):
    world.search([(_ref("lib.x"), 0.85)])
    llm = FakeLLMClient([CanonDecision(same=True, reason="одно")])

    await _run(world, llm)

    [event] = world.memory.of(EventType.misconception_canonized)
    assert event.payload["decided_by"] == "model"
    assert llm.calls[0].method == "structured"


async def test_adjudicate_no_creates_personal(world):
    world.search([(_ref("lib.x"), 0.85)])

    await _run(world, FakeLLMClient([CanonDecision(same=False, reason="разное")]))

    [event] = world.memory.of(EventType.misconception_personal_created)
    assert event.payload["misconception_id"].startswith(
        f"pers.{world.student_id.hex[:8]}."
    )
    assert len(event.payload["embedding"]) == 384
    assert event.payload["best_similarity"] == 0.85


@pytest.mark.parametrize("results", [[(_ref(), 0.5)], []])
async def test_below_threshold_creates(world, results):
    world.search(results)

    await _run(world)

    assert len(world.memory.of(EventType.misconception_personal_created)) == 1


async def test_adjudication_failed_no_node(world):
    world.search([(_ref(), 0.85)])

    await _run(world, FakeLLMClient(["bad", "bad"]))

    [failed] = world.memory.of(EventType.job_failed)
    assert failed.payload["reason"] == "adjudication_failed"
    assert world.memory.of(EventType.misconception_personal_created) == []
    assert world.memory.of(EventType.misconception_canonized) == []


async def test_embedder_missing(world):
    world.search([])

    await _run(world, embedder=None, job_try=1)

    [failed] = world.memory.of(EventType.job_failed)
    assert failed.payload["reason"] == "embedder_unavailable"


async def test_idempotent_by_prior_result(world):
    world.search([(_ref(), 0.95)])
    world.memory.add(
        EventType.misconception_canonized,
        student_id=world.student_id,
        payload={"source_event_id": world.source.id, "ordinal": 1},
    )
    appended_before = len(world.memory.appended)

    await _run(world)

    assert len(world.memory.appended) == appended_before


async def test_not_proposed_is_ignored(world):
    world.search([])
    await _run(world, ordinal=0)
    assert world.memory.appended == []


async def test_personal_id_collision_gets_suffix(world, monkeypatch):
    world.search([])
    taken = {f"pers.{world.student_id.hex[:8]}.{jobs.slug('Путает знак')}"}
    monkeypatch.setattr(
        jobs.canonical_q,
        "get_misconception",
        AsyncMock(side_effect=lambda _g, mid: _ref(mid) if mid in taken else None),
    )

    await _run(world)

    [event] = world.memory.of(EventType.misconception_personal_created)
    assert event.payload["misconception_id"].endswith("-2")


def test_slug_transliterates():
    assert jobs.slug("Путает знак!") == "putaet-znak"
