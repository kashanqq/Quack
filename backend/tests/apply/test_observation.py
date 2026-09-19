"""apply.observation — the observer's rule (docs/tz/phase3-agents.md §3.10,
§6.9). Unit tests on an in-memory graph; Postgres repositories are faked."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app import keys
from app.apply import observation as rule
from app.apply._lock import lock_key
from app.config import KnowledgeParams
from app.events.dispatch import GraphUnavailable, RuleDeps
from app.knowledge.reconcile import reconcile_task_answer
from app.schemas.events import Event, EventType, TaskAnsweredPayload
from app.schemas.observer import Observation, ObservationApplyResult
from app.schemas.tasks import Grade, Option, TaskInstance
from tests.apply._fake_graph import NOW, FakeGraph, misc, state

pytestmark = pytest.mark.phase3

TOPIC = "math.alg.abs_value_eq"
PRE = "math.alg.linear_eq"
MISC = "lib.abs_single_branch"


class World:
    def __init__(self, monkeypatch, redis):
        self.graph = FakeGraph()
        self.graph.prereqs[TOPIC] = [PRE]
        self.graph.library[TOPIC] = [MISC]
        self.graph.install(monkeypatch, rule)
        self.student_id = uuid4()
        self.chat_id = uuid4()
        self.set_id = uuid4()
        self.redis = redis
        self.deps = RuleDeps(
            graph=object(), redis=redis, params=KnowledgeParams(), now=lambda: NOW
        )
        self.window: dict[int, Event] = {}
        self.appended: list = []
        self.pace: set = set()
        self.instances: dict = {}
        self.answered: set = set()
        self.rebuild = AsyncMock()
        self.next_id = 100
        monkeypatch.setattr("app.apply.sets.rebuild_sets", self.rebuild)
        monkeypatch.setattr(rule.store, "get_events", self._get_events)
        monkeypatch.setattr(rule.store, "latest_before", AsyncMock(return_value=None))
        monkeypatch.setattr(rule.store, "get_event", self._get_event)
        monkeypatch.setattr(rule.store, "append", self._append)
        monkeypatch.setattr(
            rule.messages_repo, "list_by_event_ids", AsyncMock(return_value={})
        )
        monkeypatch.setattr(rule, "session_minute", AsyncMock(return_value=5))
        monkeypatch.setattr(rule.aggregates_repo, "add_pace_signal", self._pace)
        monkeypatch.setattr(rule.tasks_repo, "get_instance", self._instance)
        monkeypatch.setattr(rule.tasks_repo, "issued_event_ids", self._issued)
        monkeypatch.setattr(rule.tasks_repo, "get_answered_at", self._answered_at)

    def message(self, role="user", hint=None) -> Event:
        self.next_id += 1
        event = Event(
            id=self.next_id,
            type=EventType.message_user
            if role == "user"
            else EventType.message_assistant,
            payload={"text": "x", "hint_level": hint},
            student_id=self.student_id,
            chat_id=self.chat_id,
            session_id=uuid4(),
            occurred_at=NOW,
            ingested_at=NOW,
        )
        self.window[event.id] = event
        return event

    def task(self) -> TaskInstance:
        self.next_id += 1
        issued = Event(
            id=self.next_id,
            type=EventType.task_issued,
            payload={},
            student_id=self.student_id,
            chat_id=self.chat_id,
            occurred_at=NOW - timedelta(seconds=90),
            ingested_at=NOW,
        )
        self.window[issued.id] = issued
        instance = TaskInstance(
            id=uuid4(),
            template_id="t",
            seed=1,
            exam_id="SAT_MATH",
            type="mcq4",
            skill_id=TOPIC,
            stem_rendered="?",
            options=[Option(key=k, text=k, correct=k == "A") for k in "ABCD"],
            answer="A",
            trap_answers=[],
            solution_rendered=[],
            time_reference_sec=60,
            difficulty=3,
            tags=[],
        )
        self.instances[instance.id] = (instance, issued.id)
        return instance

    def event(self, *observations: Observation, event_id=500) -> Event:
        return Event(
            id=event_id,
            type=EventType.observation_extracted,
            payload={
                "observations": [o.model_dump(mode="json") for o in observations],
                "window_from_event_id": None,
                "window_to_event_id": None,
                "topic_skill_id": TOPIC,
                "set_id": str(self.set_id),
                "exam_id": "SAT_MATH",
                "model": "m",
                "raw_count": len(observations),
            },
            student_id=self.student_id,
            chat_id=self.chat_id,
            set_id=self.set_id,
            topic_skill_id=TOPIC,
            extractor_version="observer_v1",
            source_event_ids=sorted(self.window),
            occurred_at=NOW,
            ingested_at=NOW,
        )

    async def apply(self, event) -> ObservationApplyResult:
        return await rule.apply_observation_extracted(object(), event, self.deps)

    # fakes
    async def _get_events(self, _s, _sid, ids):
        return [self.window[i] for i in ids if i in self.window]

    async def _get_event(self, _s, _sid, event_id):
        return self.window.get(event_id)

    async def _append(self, _s, _r, ev, deps=None, *, dispatch_event=True):
        self.appended.append((ev, dispatch_event))
        self.answered.add(ev.payload["instance_id"])
        self.next_id += 1
        return Event(
            **ev.model_dump(exclude={"occurred_at"}),
            id=self.next_id,
            occurred_at=NOW,
            ingested_at=NOW,
        )

    async def _pace(self, _s, _sid, day, signal, event_id, ordinal):
        self.pace.add((event_id, ordinal, signal))

    async def _instance(self, _s, _sid, instance_id):
        found = self.instances.get(instance_id)
        return found[0] if found else None

    async def _issued(self, _s, _sid, ids):
        return {i: self.instances[i][1] for i in ids if i in self.instances}

    async def _answered_at(self, _s, instance_id):
        return NOW if str(instance_id) in self.answered else None


@pytest.fixture
def world(monkeypatch, redis):
    return World(monkeypatch, redis)


def obs(kind="solution_step", *, event_ids, confidence=0.9, **kw) -> Observation:
    if kind == "solution_step":
        kw.setdefault("outcome", "incorrect")
    if kind not in ("task_in_chat", "proposed_misconception", "pace_signal"):
        kw.setdefault("skill_id", TOPIC)
    return Observation(kind=kind, event_ids=event_ids, confidence=confidence, **kw)


async def test_confidence_filter(world):
    m = world.message()
    result = await world.apply(
        world.event(
            obs(event_ids=[m.id], confidence=0.69),
            obs(event_ids=[m.id], confidence=0.7),
        )
    )
    assert (0, "low_confidence") in result.skipped
    assert result.applied == 1


async def test_referential_filters(world):
    m = world.message()
    result = await world.apply(
        world.event(
            obs(event_ids=[m.id], skill_id="math.geo.circle"),
            obs(event_ids=[m.id], misconception_id="lib.unknown"),
            obs(event_ids=[9999]),
            obs("root_hint", event_ids=[m.id], root_skill_id="math.geo.circle"),
        )
    )
    assert dict(result.skipped) == {
        0: "unknown_skill",
        1: "unknown_misconception",
        2: "event_ids_outside_window",
        3: "unknown_root",
    }
    assert result.applied == 0


async def test_solution_step_incorrect_with_misconception(world):
    world.graph.states[(TOPIC, "SAT_MATH")] = state(TOPIC, p=0.6, h=48)
    m = world.message()

    result = await world.apply(
        world.event(obs(event_ids=[m.id], misconception_id=MISC))
    )

    [evidence] = world.graph.evidence.values()
    assert (evidence.tier, evidence.weight, evidence.direction) == (2, 0.7, -1)
    assert evidence.source == "chat" and evidence.extractor_version == "observer_v1"
    assert evidence.context.mode == "chat" and evidence.context.session_minute == 5
    assert world.graph.states[(TOPIC, "SAT_MATH")].half_life_h == pytest.approx(
        48 * 0.65
    )
    created = world.graph.misc[MISC]
    assert (created.status, created.occurrence_count, created.strong_count) == (
        "suspected",
        1,
        1,
    )
    assert result.misconceptions_changed[0].to_status == "suspected"


async def test_second_hit_confirms_only_with_strong(world):
    world.graph.misc[MISC] = misc(MISC, "suspected", occ=1, strong=0, skill=TOPIC)
    m = world.message()

    await world.apply(
        world.event(obs(event_ids=[m.id], misconception_id=MISC), event_id=501)
    )
    assert world.graph.misc[MISC].status == "confirmed"

    world.graph.misc[MISC] = misc(MISC, "suspected", occ=1, strong=0, skill=TOPIC)
    await world.apply(world.event(obs("confusion", event_ids=[m.id]), event_id=502))
    assert world.graph.misc[MISC].status == "suspected"


async def test_tier3_capped_by_p_chat_cap(world):
    world.graph.states[(TOPIC, "SAT_MATH")] = state(
        TOPIC, p=0.78, h=48, last_observed_at=NOW - timedelta(hours=48)
    )
    m = world.message()

    await world.apply(world.event(obs("applied", event_ids=[m.id])))

    after = world.graph.states[(TOPIC, "SAT_MATH")]
    assert after.p_at_obs <= KnowledgeParams().p_chat_cap
    assert after.has_strong is False


async def test_avoided_trap_increments_consecutive(world):
    world.graph.misc[MISC] = misc(
        MISC, "confirmed", occ=3, strong=2, avoided=2, skill=TOPIC
    )
    m = world.message()

    await world.apply(
        world.event(obs("avoided_trap", event_ids=[m.id], misconception_id=MISC))
    )

    assert world.graph.misc[MISC].consecutive_avoided == 3
    assert world.graph.misc[MISC].status == "resolved"


async def test_avoided_trap_without_state_skipped(world):
    m = world.message()
    result = await world.apply(
        world.event(obs("avoided_trap", event_ids=[m.id], misconception_id=MISC))
    )
    assert result.skipped == [(0, "no_misconception_state")]


async def test_root_hint_links_latest_incorrect(world):
    m = world.message()
    result = await world.apply(
        world.event(
            obs(event_ids=[m.id]),
            obs("root_hint", event_ids=[m.id], root_skill_id=PRE),
        )
    )
    assert (f"500:{TOPIC}:0", PRE) in world.graph.roots
    assert result.applied == 2

    other = await world.apply(
        world.event(
            obs("root_hint", event_ids=[m.id], root_skill_id=PRE, confidence=0.8),
            event_id=600,
        )
    )
    assert other.skipped == [
        (0, "already_applied")
    ]  # the same latest evidence and root


async def test_root_hint_without_incorrect_evidence(world):
    m = world.message()
    result = await world.apply(
        world.event(obs("root_hint", event_ids=[m.id], root_skill_id=PRE))
    )
    assert result.skipped == [(0, "no_incorrect_evidence")]


async def test_task_in_chat_appends_task_answered_once(world):
    instance = world.task()
    world.message("assistant", hint=2)
    m = world.message()
    event = world.event(
        obs(
            "task_in_chat",
            event_ids=[m.id],
            instance_id=str(instance.id),
            answer="ответ a",
        )
    )

    result = await world.apply(event)

    [(answered, dispatched)] = world.appended
    assert dispatched is True
    assert answered.type == EventType.task_answered
    payload = TaskAnsweredPayload.model_validate(answered.payload)
    assert payload.mode == "chat" and payload.answer == "A"
    assert payload.hint_level_before == 2
    assert payload.time_spent_sec == 90
    assert answered.source_event_ids == [event.id]
    assert len(result.task_answered_event_ids) == 1

    again = await world.apply(event)
    assert again.skipped == [(0, "already_answered")]
    assert len(world.appended) == 1


async def test_task_in_chat_unparsable(world):
    instance = world.task()
    m = world.message()
    result = await world.apply(
        world.event(
            obs(
                "task_in_chat",
                event_ids=[m.id],
                instance_id=str(instance.id),
                answer="не знаю",
            )
        )
    )
    assert result.skipped == [(0, "unparsable_answer")]


def test_task_in_chat_weight_is_chat_tier2():
    instance = TaskInstance(
        id=uuid4(),
        template_id="t",
        seed=1,
        exam_id="SAT_MATH",
        type="mcq4",
        skill_id=TOPIC,
        stem_rendered="?",
        options=[Option(key="A", text="1", correct=True)],
        answer="A",
        trap_answers=[],
        solution_rendered=[],
        time_reference_sec=60,
        difficulty=3,
        tags=[],
    )
    payload = TaskAnsweredPayload(
        instance_id=instance.id,
        answer="A",
        time_spent_sec=30,
        mode="chat",
        session_minute=1,
        after_guideline=False,
        hint_level_before=0,
    )
    result = reconcile_task_answer(
        instance,
        Grade(correct=True),
        payload,
        None,
        [],
        [],
        0,
        ["SAT_MATH"],
        KnowledgeParams(),
        NOW,
        event_id=7,
    )
    evidence = result.evidence[0]
    assert (evidence.source, evidence.kind, evidence.tier, evidence.weight) == (
        "chat",
        "task_in_chat",
        2,
        0.8,
    )
    assert evidence.context.instance_id == instance.id


async def test_two_observations_same_skill_get_ordinals(world):
    m = world.message()
    await world.apply(
        world.event(obs(event_ids=[m.id]), obs(event_ids=[m.id], outcome="correct"))
    )
    assert set(world.graph.evidence) == {(500, TOPIC, 0), (500, TOPIC, 1)}
    assert len([s for s in world.graph.history if s.skill_id == TOPIC]) == 2


async def test_idempotent_redelivery(world):
    m = world.message()
    event = world.event(obs(event_ids=[m.id]), obs("question", event_ids=[m.id]))
    first = await world.apply(event)
    states_before = len(world.graph.history)

    second = await world.apply(event)

    assert first.applied == 2
    assert second.applied == 0
    assert {reason for _, reason in second.skipped} == {"already_applied"}
    assert len(world.graph.history) == states_before
    assert second.knowledge_version == first.knowledge_version


async def test_partial_failure_resumes(world):
    m = world.message()
    event = world.event(obs(event_ids=[m.id]), obs("question", event_ids=[m.id]))
    world.graph.fail_after = 1

    assert await world.apply(event) is GraphUnavailable
    world.graph.fail_after = None
    result = await world.apply(event)

    assert result.skipped == [(0, "already_applied")]
    assert result.applied == 1


async def test_graph_none_is_graph_unavailable(world):
    m = world.message()
    world.deps.graph = None
    assert await world.apply(world.event(obs(event_ids=[m.id]))) is GraphUnavailable


async def test_proposed_misconception_pending(world):
    m = world.message()
    result = await world.apply(
        world.event(
            obs(
                "proposed_misconception",
                event_ids=[m.id],
                name="n",
                description="d",
                error_class="procedural",
                skill_id=TOPIC,
            )
        )
    )
    assert result.pending_canonizations == [0]
    assert world.graph.evidence == {}


async def test_pace_signal_to_aggregates(world):
    m = world.message()
    event = world.event(
        Observation(kind="pace_signal", signal="просит медленнее", event_ids=[m.id])
    )
    await world.apply(event)
    await world.apply(event)
    assert world.pace == {(500, 0, "просит медленнее")}


async def test_version_bump_and_cache_invalidation(world):
    m = world.message()
    topic_key = keys.ctx_topic(str(world.student_id), TOPIC)
    set_key = keys.ctx_topic(str(world.student_id), f"set:{world.set_id}")
    await world.redis.set(topic_key, "x")
    await world.redis.set(set_key, "x")

    result = await world.apply(world.event(obs(event_ids=[m.id])))

    assert result.knowledge_version == 1
    assert await world.redis.get(topic_key) is None
    assert await world.redis.get(set_key) is None
    world.rebuild.assert_awaited_once()

    await world.redis.set(topic_key, "x")
    empty = await world.apply(world.event(event_id=777))
    assert empty.applied == 0 and empty.knowledge_version == 1
    assert await world.redis.get(topic_key) == b"x"


async def test_student_lock_taken_and_released(world, monkeypatch):
    seen = []
    original = world.graph.apply_chat_observation_tx

    async def spy(*args, **kwargs):
        seen.append(await world.redis.get(lock_key(world.student_id)))
        return await original(*args, **kwargs)

    monkeypatch.setattr(rule.personal_q, "apply_chat_observation_tx", spy)
    m = world.message()

    await world.apply(world.event(obs(event_ids=[m.id])))

    assert seen and seen[0] is not None
    assert await world.redis.get(lock_key(world.student_id)) is None


def test_normalize_chat_answer_forms():
    base = dict(
        id=uuid4(),
        template_id="t",
        seed=1,
        exam_id="SAT_MATH",
        skill_id=TOPIC,
        stem_rendered="?",
        answer="A",
        trap_answers=[],
        solution_rendered=[],
        time_reference_sec=60,
        difficulty=3,
        tags=[],
    )
    options = [Option(key=k, text=k, correct=False) for k in "ABCD"]
    mcq = TaskInstance(type="mcq4", options=options, **base)
    multi = TaskInstance(type="multi_select", options=options, **base)
    numeric = TaskInstance(type="numeric", options=[], **base)
    assert rule.normalize_chat_answer(mcq, "думаю, ответ b") == "B"
    assert rule.normalize_chat_answer(mcq, "С") == "C"  # Cyrillic С
    assert rule.normalize_chat_answer(multi, "A, C") == ["A", "C"]
    assert rule.normalize_chat_answer(numeric, "x = −2,5") == "-2.5"
    assert rule.normalize_chat_answer(numeric, "не знаю") is None
