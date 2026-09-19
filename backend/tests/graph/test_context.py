"""graph.context.build_topic_context and apply.context.get_topic_context
(docs/tz/phase3-agents.md §3.7, §6.6). Unit: the four queries are faked."""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app import keys
from app.apply import context as apply_context
from app.config import KnowledgeParams
from app.events import version
from app.events.dispatch import RuleDeps
from app.graph import context as ctx_mod
from app.graph.context import ContextExtras, build_topic_context
from app.graph.queries.context import SkillSliceRow
from app.schemas.knowledge import (
    KnowledgeStateOut,
    MisconceptionStateOut,
    Prerequisite,
    TestDate,
)
from app.schemas.profile import Profile
from app.schemas.sets import SetOut, SetProgress, TopicOut

pytestmark = pytest.mark.phase3

NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)
TOPIC = "topic"


def st(skill, p, conf, h=100.0) -> KnowledgeStateOut:
    """A state whose recall at NOW is `p` (recall decays from the last
    observation: 2 ** (-dt / h), so dt = h * log2(1 / p))."""
    observed = NOW - timedelta(hours=h * math.log2(1 / p))
    return KnowledgeStateOut(
        skill_id=skill,
        exam_id="SAT_MATH",
        p_recall=p,
        p_at_obs=p,
        half_life_h=h,
        confidence=conf,
        evidence_mass=1,
        n_correct=1,
        n_incorrect=0,
        n_partial=0,
        has_strong=True,
        last_observed_at=observed,
        created_at=observed,
    )


def ms(mid, status, occ=3, days=1, triggers=None) -> MisconceptionStateOut:
    return MisconceptionStateOut(
        misconception_id=mid,
        name=f"{mid}-name",
        status=status,
        occurrence_count=occ,
        strong_count=1,
        consecutive_avoided=0,
        triggers=triggers or {},
        first_seen_at=NOW,
        updated_at=NOW - timedelta(days=days),
        skill_ids=[TOPIC],
    )


def _set(set_id, topics=(TOPIC, "next")) -> SetOut:
    return SetOut(
        id=set_id,
        exam_id="SAT_MATH",
        area_ids=["alg"],
        status="current",
        kind="regular",
        position=2,
        deadline=date(2026, 10, 5),
        reason="",
        topics=[
            TopicOut(
                skill_id=s,
                name=f"{s}-name",
                kind="topic",
                position=i,
                status="open",
                level="shaky",
                is_root=False,
                misconception_labels=[],
                subtitle=None,
            )
            for i, s in enumerate(topics)
        ],
        progress=SetProgress(
            topics_closed=0, topics_total=len(topics), tasks_answered=0, tasks_correct=0
        ),
    )


def _rows(p=None) -> list[SkillSliceRow]:
    p = p or {}
    specs = {
        TOPIC: (0.55, 0.8),
        "A": (0.88, 0.9),
        "B": (0.82, 0.7),
        "C": (0.93, 0.6),
        "D": (0.42, 0.6),
        "E": (0.5, 0.1),
        **p,
    }
    return [
        SkillSliceRow(
            skill_id=s, name=f"{s}-name", state=st(s, *v), history=[st(s, *v)]
        )
        for s, v in specs.items()
    ]


@pytest.fixture
def queries(monkeypatch):
    fakes = {
        "q_skill_slice": AsyncMock(return_value=_rows()),
        "q_root_causes": AsyncMock(return_value={"D": (2, 1.2)}),
        "q_misconceptions": AsyncMock(return_value=[]),
        "q_test_dates": AsyncMock(
            return_value=[
                TestDate(
                    exam_id="SAT_MATH",
                    date=date(2026, 11, 7),
                    registration_deadline=date(2026, 10, 20),
                    source="cb",
                    checked_at=date(2026, 9, 1),
                    is_demo=True,
                )
            ]
        ),
    }
    for name, fake in fakes.items():
        monkeypatch.setattr(ctx_mod.context_q, name, fake)
    monkeypatch.setattr(
        ctx_mod.canonical_q,
        "get_prerequisites",
        AsyncMock(
            return_value=[
                Prerequisite(skill_id=s, strength=1, depth=1) for s in "ABCDE"
            ]
        ),
    )
    return fakes


def _extras(set_out=None, profile=None, summary=None) -> ContextExtras:
    return ContextExtras(
        set=set_out,
        profile=profile or Profile(student_id=uuid4()),
        previous_summary=summary,
        p_target=0.95,
    )


async def _build(
    redis, student_id=None, set_id=None, topic=TOPIC, params=None, extras=None
):
    set_id = set_id or uuid4()
    return await build_topic_context(
        object(),
        redis,
        student_id or uuid4(),
        topic,
        set_id,
        exam_id="SAT_MATH",
        extras=extras or _extras(_set(set_id)),
        params=params or KnowledgeParams(),
        now=NOW,
    )


async def test_four_queries_run_in_parallel_once(redis, queries):
    started: list[str] = []
    gate = asyncio.Event()

    def blocking(name, value):
        async def run(*_a, **_k):
            started.append(name)
            if len(started) == 4:
                gate.set()
            await asyncio.wait_for(gate.wait(), 1)
            return value

        return run

    for name, fake in queries.items():
        fake.side_effect = blocking(name, fake.return_value)

    await _build(redis)

    assert sorted(started) == sorted(queries)
    for fake in queries.values():
        assert fake.await_count == 1


async def test_slots_limits_and_thresholds(redis, queries):
    context = await _build(redis)

    assert context.strengths == ["A-name: p=0.88 conf=0.90", "B-name: p=0.82 conf=0.70"]
    assert context.prerequisite_gaps == [
        "D-name: p=0.42 conf=0.60 (корень 2 ошибок за 30 дней)"
    ]
    assert context.low_data == ["E-name: мало данных"]
    assert "p=0.55 conf=0.80 trend=" in context.topic[0]
    assert "в сете 1 из 2, дальше — next-name" in context.topic[0]
    assert context.deadline == ["сет до 5 окт", "SAT 7 ноя"]
    assert context.skill_ids == [TOPIC, "A", "B", "C", "D", "E"]
    assert context.set_label == "сет 2 до 5 окт"


async def test_misconceptions_visibility(redis, queries):
    queries["q_misconceptions"].return_value = [
        ms("m.confirmed", "confirmed", occ=3),
        ms("m.suspected", "suspected"),
        ms("m.resolved.fresh", "resolved", days=3),
        ms("m.resolved.old", "resolved", days=20),
        ms("m.disputed", "disputed"),
    ]
    context = await _build(redis)

    assert context.active_misconceptions == ["m.confirmed-name (подтверждено, 3 набл.)"]
    assert context.under_watch == ["m.resolved.fresh-name (исправлено, следим)"]


async def test_trigger_words_in_active(redis, queries):
    queries["q_misconceptions"].return_value = [
        ms("m", "confirmed", triggers={"n": 4, "hurried": [3, 4]})
    ]
    context = await _build(redis)
    assert "обычно — когда торопится" in context.active_misconceptions[0]


async def test_set_multiplier(redis, queries):
    rows = _rows(
        {
            "F": (0.9, 0.9),
            "G": (0.85, 0.9),
            "H": (0.3, 0.9),
            "I": (0.2, 0.9),
            "J": (0.1, 0.9),
            "K": (0.35, 0.9),
        }
    )
    queries["q_skill_slice"].return_value = rows
    set_id = uuid4()

    context = await _build(
        redis, set_id=set_id, topic=None, extras=_extras(_set(set_id))
    )

    assert len(context.strengths) == 3
    assert len(context.prerequisite_gaps) == 5
    assert context.topic == ["сет: topic-name, next-name"]


async def test_cache_hit_on_same_version(redis, queries):
    student_id, set_id = uuid4(), uuid4()
    await _build(redis, student_id, set_id)
    first = await _build(redis, student_id, set_id)

    assert first.cache == "hit"
    assert queries["q_skill_slice"].await_count == 1

    await version.bump(redis, student_id)
    second = await _build(redis, student_id, set_id)
    assert second.cache == "miss"
    assert queries["q_skill_slice"].await_count == 2
    assert await redis.get(keys.ctx_topic(str(student_id), TOPIC)) is not None


async def test_cache_corrupted_is_miss(redis, queries):
    student_id = uuid4()
    await redis.set(keys.ctx_topic(str(student_id), TOPIC), "{not json")

    context = await _build(redis, student_id)

    assert context.cache == "miss"
    assert queries["q_skill_slice"].await_count == 1


async def test_no_redis_is_none(queries):
    context = await _build(None)
    assert context.cache == "none"


async def test_budget_truncation(redis, queries):
    params = KnowledgeParams(context_budget_tokens=50)
    set_id = uuid4()
    extras = _extras(_set(set_id), summary="в прошлом сете закрыли линейные уравнения")

    context = await _build(redis, set_id=set_id, params=params, extras=extras)

    total = sum(
        len(line) for name in ctx_mod.SLOT_ORDER for line in getattr(context, name)
    )
    assert total <= 150
    assert context.previous_set == []


async def test_apply_get_topic_context_foreign_set_is_none(monkeypatch, redis):
    deps = RuleDeps(
        graph=object(), redis=redis, params=KnowledgeParams(), now=lambda: NOW
    )
    monkeypatch.setattr(
        apply_context.sets_repo, "get_set", AsyncMock(return_value=None)
    )
    assert (
        await apply_context.get_topic_context(object(), deps, uuid4(), uuid4(), TOPIC)
        is None
    )

    set_id = uuid4()
    monkeypatch.setattr(
        apply_context.sets_repo, "get_set", AsyncMock(return_value=_set(set_id))
    )
    monkeypatch.setattr(
        apply_context.profiles_repo,
        "get_profile",
        AsyncMock(return_value=Profile(student_id=uuid4())),
    )
    monkeypatch.setattr(
        apply_context.summaries_repo, "get_latest_text", AsyncMock(return_value=None)
    )
    assert (
        await apply_context.get_topic_context(
            object(), deps, uuid4(), set_id, "not-in-set"
        )
        is None
    )
    deps.graph = None
    assert (
        await apply_context.get_topic_context(object(), deps, uuid4(), set_id, TOPIC)
        is None
    )


async def test_context_cache_double_build_consistent(redis, queries):
    student_id, set_id = uuid4(), uuid4()
    a, b = await asyncio.gather(
        _build(redis, student_id, set_id), _build(redis, student_id, set_id)
    )
    assert a.strengths == b.strengths
    assert await redis.get(keys.ctx_topic(str(student_id), TOPIC)) is not None
