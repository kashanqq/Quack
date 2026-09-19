"""Phase 3 end to end on live Postgres + Neo4j (docs/tz/phase3-agents.md
§6.8 integration_end_to_end, §6.9 merge_evidence_ordinal_key_integration,
§6.6 integration_context_from_seeded_graph, §6.10 canonization).

The chat transport is covered by unit tests; here the window is written the
way the transport writes it (`message.*` with `dispatch_event=False`) and the
real `observe_chat` / `canonize_misconception` jobs run against the databases.
Everything is keyed by fresh ids, so runs do not interfere.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4, uuid5

import pytest
from fastapi import Response
from sqlalchemy import select

from app.agents import jobs
from app.api import chat as chat_api
from app.apply import context as apply_context
from app.config import KnowledgeParams, Settings
from app.db.engine import close_engine, create_engine, create_sessionmaker
from app.db.models import Event as EventRow
from app.db.models import Set as SetRow
from app.db.models import SetTopic
from app.db.repo import messages as messages_repo
from app.events import dispatch, store, version
from app.events.dispatch import RuleDeps
from app.graph.queries import personal
from app.llm.fake import FakeLLMClient
from app.schemas.auth import StudentCtx
from app.schemas.events import EventIn, EventType
from app.schemas.knowledge import EvidenceContext, EvidenceIn
from app.schemas.observer import Observation, ObservationOut

pytestmark = [pytest.mark.integration, pytest.mark.phase3]

TOPIC = "test.phase2.skill.absolute"
PRE = "test.phase2.skill.linear"
MISC = "test.phase2.misc.single_branch"


class Embedder:
    def embed(self, texts):
        return [[1.0] + [0.0] * 383 for _ in texts]


@pytest.fixture
async def sessionmaker():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required")
    engine = create_engine(Settings(ENV="local", DATABASE_URL=url))
    try:
        yield create_sessionmaker(engine)
    finally:
        await close_engine(engine)


def _deps(graph, redis) -> RuleDeps:
    return RuleDeps(
        graph=graph,
        redis=redis,
        params=KnowledgeParams(),
        now=lambda: datetime.now(UTC),
    )


async def _student_with_set(sessionmaker, graph):
    student_id, set_id = uuid4(), uuid4()
    await personal.ensure_student(graph, student_id)
    async with sessionmaker() as session:
        session.add(
            SetRow(
                id=set_id,
                student_id=student_id,
                exam_id="SAT_MATH",
                status="current",
                position=0,
                deadline=date.today() + timedelta(days=10),
                reason="test",
                kind="regular",
            )
        )
        await session.flush()
        session.add(
            SetTopic(
                set_id=set_id, skill_id=TOPIC, position=0, kind="topic", status="open"
            )
        )
        await session.commit()
    return student_id, set_id


async def _message(sessionmaker, redis, student_id, chat_id, set_id, role, text):
    async with sessionmaker() as session:
        event = await store.append(
            session,
            redis,
            EventIn(
                type=EventType.message_user
                if role == "user"
                else EventType.message_assistant,
                payload={"text": text}
                if role == "user"
                else {
                    "text": text,
                    "mode": "review",
                    "hint_level": 2,
                    "referenced_skill_ids": [],
                },
                student_id=student_id,
                chat_id=chat_id,
                set_id=set_id,
                topic_skill_id=TOPIC,
            ),
            dispatch_event=False,
        )
        await messages_repo.append_message(
            session, student_id, chat_id, role, text, None, event.id
        )
        await session.commit()
    return event


async def test_merge_evidence_ordinal_key_integration(seeded_graph):
    student_id = uuid4()
    await personal.ensure_student(seeded_graph, student_id)
    message_id = uuid4()

    def ev(ordinal):
        return EvidenceIn(
            event_id=424242,
            ordinal=ordinal,
            skill_id=TOPIC,
            exam_id="SAT_MATH",
            kind="confusion",
            tier=3,
            source="chat",
            weight=0.6,
            direction=-1,
            context=EvidenceContext(mode="chat", message_id=message_id),
            observed_at=datetime.now(UTC),
        )

    await personal.merge_evidence(seeded_graph, student_id, ev(0))
    await personal.merge_evidence(seeded_graph, student_id, ev(0))
    assert await personal.list_evidence_keys_for_event(
        seeded_graph, student_id, 424242
    ) == {(TOPIC, 0)}
    await personal.merge_evidence(seeded_graph, student_id, ev(1))
    assert await personal.list_evidence_keys_for_event(
        seeded_graph, student_id, 424242
    ) == {
        (TOPIC, 0),
        (TOPIC, 1),
    }
    items = await personal.list_evidence(seeded_graph, student_id, TOPIC)
    assert {item.message_id for item in items} == {message_id}


async def test_integration_end_to_end(seeded_graph, sessionmaker, redis, fake_enqueue):
    student_id, set_id = await _student_with_set(sessionmaker, seeded_graph)
    chat_id = uuid5(student_id, f"prep:{set_id}:{TOPIC}")
    user = await _message(
        sessionmaker, redis, student_id, chat_id, set_id, "user", "|x-3|=2, x=5"
    )
    await _message(
        sessionmaker, redis, student_id, chat_id, set_id, "assistant", "А вторая ветвь?"
    )
    version_before = await version.get(redis, student_id)

    llm = FakeLLMClient(
        [
            ObservationOut(
                observations=[
                    Observation(
                        kind="solution_step",
                        outcome="incorrect",
                        skill_id=TOPIC,
                        misconception_id=MISC,
                        event_ids=[user.id],
                        confidence=0.9,
                        summary="одна ветвь",
                    ),
                    Observation(
                        kind="proposed_misconception",
                        name="Single branch again",
                        description="drops a branch",
                        error_class="conceptual",
                        skill_id=TOPIC,
                        event_ids=[user.id],
                        confidence=0.8,
                    ),
                ]
            )
        ]
    )
    ctx = {
        "sessionmaker": sessionmaker,
        "redis": redis,
        "neo4j": seeded_graph,
        "llm": llm,
        "job_try": 1,
        "job_id": "it",
        "embedder": Embedder(),
    }
    await jobs.observe_chat(ctx, "req", chat_id, student_id, "requested")

    # the event, the window and the graph
    async with sessionmaker() as session:
        [extracted] = await store.list_by_type(
            session,
            student_id,
            [EventType.observation_extracted],
            None,
            10,
            chat_id=chat_id,
        )
        window = (
            await session.scalars(
                select(EventRow).where(
                    EventRow.chat_id == chat_id, EventRow.processed_at.is_(None)
                )
            )
        ).all()
    assert extracted.extractor_version == "observer_v1"
    assert window == []  # the window is closed
    assert await personal.list_evidence_keys_for_event(
        seeded_graph, student_id, extracted.id
    ) == {(TOPIC, 0)}
    state = await personal.get_state(seeded_graph, student_id, TOPIC, "SAT_MATH")
    assert state is not None and state.n_incorrect == 1
    [misc_state] = await personal.get_misc_states(seeded_graph, student_id, [TOPIC])
    assert (misc_state.misconception_id, misc_state.status) == (MISC, "suspected")
    evidence = await personal.list_evidence(seeded_graph, student_id, TOPIC)
    assert evidence[0].message_id is not None
    version_after = await version.get(redis, student_id)
    assert version_after > version_before
    [(_, fn, kwargs)] = [c for c in fake_enqueue if c[1] == "canonize_misconception"]
    assert kwargs["_job_id"] == f"canon:{extracted.id}:1"

    # replay of the same event changes nothing
    async with sessionmaker() as session:
        again = await dispatch.dispatch(session, extracted, _deps(seeded_graph, redis))
        await session.commit()
    result = again["apply_observation_extracted"]
    assert result.applied == 0
    assert await version.get(redis, student_id) == version_after
    assert (
        await personal.get_state(seeded_graph, student_id, TOPIC, "SAT_MATH")
    ).n_incorrect == 1

    # canonization: the fixture embedder makes every library node identical
    await jobs.canonize_misconception(ctx, "req", student_id, extracted.id, 1)
    async with sessionmaker() as session:
        [canonized] = await store.list_by_type(
            session, student_id, [EventType.misconception_canonized], None, 10
        )
    assert canonized.payload["decided_by"] == "threshold"
    # the fixture embedder makes both library entries equally close
    canonical_id = canonized.payload["canonical_id"]
    assert canonical_id in {MISC, "test.phase2.misc.sign_drop"}
    states = {
        m.misconception_id: m
        for m in await personal.get_misc_states(seeded_graph, student_id, [TOPIC])
    }
    assert states[canonical_id].occurrence_count == (2 if canonical_id == MISC else 1)
    assert (canonized.id, TOPIC, 0) and await personal.list_evidence_keys_for_event(
        seeded_graph, student_id, canonized.id
    ) == {(TOPIC, 0)}

    # the button's diff
    async with sessionmaker() as session:
        diff = await chat_api.observations_diff(
            set_id,
            Response(),
            StudentCtx(student_id=student_id, email="s@x"),
            session,
            _deps(seeded_graph, redis),
            since_event_id=user.id,
            topic_skill_id=TOPIC,
        )
    assert diff.status == "done"
    assert diff.observations[0].applied is True
    assert diff.observations[0].message_ids

    # the tutor context now sees the state
    async with sessionmaker() as session:
        context = await apply_context.get_topic_context(
            session, _deps(seeded_graph, redis), student_id, set_id, TOPIC
        )
    assert context is not None
    assert context.skill_ids[0] == TOPIC and PRE in context.skill_ids
    assert context.topic and "Absolute" in context.topic[0]
    assert context.cache == "miss"


async def test_personal_misconception_created_in_index(
    seeded_graph, sessionmaker, redis
):
    from app.graph.queries import canonical

    student_id, _set_id = await _student_with_set(sessionmaker, seeded_graph)
    ref = await canonical.create_personal_misconception(
        seeded_graph,
        student_id,
        f"pers.{student_id.hex[:8]}.x",
        "x",
        "y",
        "conceptual",
        TOPIC,
        [1.0] + [0.0] * 383,
        1,
        0,
    )
    again = await canonical.create_personal_misconception(
        seeded_graph,
        student_id,
        ref.id,
        "x",
        "y",
        "conceptual",
        TOPIC,
        [1.0] + [0.0] * 383,
        1,
        0,
    )
    assert again.id == ref.id and again.skill_ids == [TOPIC]
    found = await canonical.search_misconceptions(
        seeded_graph, [1.0] + [0.0] * 383, TOPIC, student_id
    )
    ids = {r.id for r, _ in found}
    assert ref.id in ids and MISC in ids
    assert all(score == pytest.approx(1.0, abs=1e-6) for _, score in found)
