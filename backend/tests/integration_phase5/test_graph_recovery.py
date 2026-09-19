"""T10–T13, AC04 against live Postgres and Neo4j.

The claim under test: a Neo4j outage must not cost the student their answer,
and the catch-up afterwards must not count it twice. Everything runs through
the ordinary `store.append` → `dispatch` → `app.apply` path — the recovery job
adds order and a watermark, never a second set of rules.
"""

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.config import KnowledgeParams, Settings
from app.db.engine import close_engine, create_engine, create_sessionmaker
from app.db.models import Event as EventRow
from app.db.models import TaskInstance as InstanceRow
from app.db.repo import tasks as tasks_repo
from app.events import handlers as _handlers  # noqa: F401 — the rule table
from app.events import recovery, store
from app.events.dispatch import RuleDeps
from app.graph.queries import applied as applied_q
from app.graph.queries import personal as personal_q
from app.schemas.events import EventIn, EventType, TaskAnsweredPayload
from app.workers import jobs_infra

pytestmark = [pytest.mark.integration, pytest.mark.phase5]

SKILL = "test.phase2.skill.absolute"


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


@pytest.fixture
async def student(sessionmaker, seeded_graph, templates_db_committed):
    student_id = uuid4()
    await personal_q.ensure_student(seeded_graph, student_id)
    yield student_id
    async with sessionmaker() as session:
        await session.execute(delete(EventRow).where(EventRow.student_id == student_id))
        await session.execute(
            delete(InstanceRow).where(InstanceRow.student_id == student_id)
        )
        await session.commit()
    async with seeded_graph.session() as graph_session:
        await graph_session.run(
            "MATCH (n) WHERE n.student_id = $sid DETACH DELETE n",
            sid=str(student_id),
        )


@pytest.fixture
async def templates_db_committed(sessionmaker):
    """The phase-2 fixture lives in a rolled-back transaction; the recovery
    job opens its own session, so the templates have to be really committed."""
    import json

    from app.db.repo.tasks import upsert_template
    from app.schemas.tasks import TaskTemplateSpec
    from tests.conftest import FIXTURE_DATA

    async with sessionmaker() as session:
        for path in sorted((FIXTURE_DATA / "templates").glob("*.json")):
            await upsert_template(
                session,
                TaskTemplateSpec.model_validate(
                    json.loads(path.read_text(encoding="utf-8"))
                ),
            )
        await session.commit()


def _deps(graph, redis):
    return RuleDeps(
        graph=graph,
        redis=redis,
        params=KnowledgeParams(),
        now=lambda: datetime.now(UTC),
    )


_seed = 0


async def _issue_instance(session, student_id):
    """One answerable instance, committed, without going through the API."""
    global _seed
    _seed += 1
    from app.tasks.generate import generate_instance

    templates = await tasks_repo.list_templates(session, SKILL)
    assert templates, "fixture templates for the skill are required"
    instance = generate_instance(templates[0], seed=_seed, student_id=student_id)
    await tasks_repo.insert_instance(session, student_id, instance, mode="topic")
    await session.commit()
    return instance


async def _answer(session, deps, student_id, instance, answer: str):
    return await store.append(
        session,
        deps.redis,
        EventIn(
            type=EventType.task_answered,
            payload=TaskAnsweredPayload(
                instance_id=instance.id,
                answer=answer,
                time_spent_sec=30,
                mode="topic",
                session_minute=1,
                after_guideline=False,
                hint_level_before=0,
            ).model_dump(mode="json"),
            student_id=student_id,
            exam_id="SAT_MATH",
            topic_skill_id=SKILL,
        ),
        deps,
    )


async def test_t10_an_answer_given_while_the_graph_is_down_is_kept_and_owed(
    sessionmaker, seeded_graph, redis, student
):
    down = _deps(None, redis)
    async with sessionmaker() as session:
        instance = await _issue_instance(session, student)
        event = await _answer(session, down, student, instance, "A")
        await session.commit()

    # Событие есть, проекции нет — и это видно как долг, а не как «готово».
    assert event.processed_at is None
    async with sessionmaker() as session:
        assert await recovery.oldest_pending_id(session, student) == event.id
        assert await recovery.pending_count(session) >= 1
    # Знание не выдумано: состояния в графе нет.
    assert await personal_q.get_state(seeded_graph, student, SKILL, "SAT_MATH") is None


async def test_recovery_applies_the_backlog_and_marks_it_processed(
    sessionmaker, seeded_graph, redis, student
):
    down = _deps(None, redis)
    async with sessionmaker() as session:
        instance = await _issue_instance(session, student)
        event = await _answer(session, down, student, instance, "A")
        await session.commit()

    ctx = {"sessionmaker": sessionmaker, "redis": redis, "neo4j": seeded_graph}
    await jobs_infra.recover_graph_events(
        ctx, request_id="test", student_id=str(student), through_event_id=event.id
    )

    async with sessionmaker() as session:
        row = await session.get(EventRow, event.id)
        assert row is not None and row.processed_at is not None
        assert await recovery.oldest_pending_id(session, student) is None
    assert (
        await personal_q.get_state(seeded_graph, student, SKILL, "SAT_MATH") is not None
    )
    assert await applied_q.is_applied(
        seeded_graph, student, event.id, "apply_task_answered"
    )


async def test_t11_running_recovery_twice_does_not_double_the_knowledge(
    sessionmaker, seeded_graph, redis, student
):
    """Маркер и идемпотентные ключи: второй проход ничего не добавляет."""
    down = _deps(None, redis)
    async with sessionmaker() as session:
        instance = await _issue_instance(session, student)
        event = await _answer(session, down, student, instance, "A")
        await session.commit()

    ctx = {"sessionmaker": sessionmaker, "redis": redis, "neo4j": seeded_graph}
    await jobs_infra.recover_graph_events(
        ctx, request_id="one", student_id=str(student), through_event_id=event.id
    )
    first = await personal_q.get_state(seeded_graph, student, SKILL, "SAT_MATH")
    counts_before = await _counts(seeded_graph, student)

    # «Падение после коммита графа»: событие снова выглядит неприменённым.
    async with sessionmaker() as session:
        row = await session.get(EventRow, event.id)
        row.processed_at = None
        await session.commit()

    await jobs_infra.recover_graph_events(
        ctx, request_id="two", student_id=str(student), through_event_id=event.id
    )
    second = await personal_q.get_state(seeded_graph, student, SKILL, "SAT_MATH")
    assert await _counts(seeded_graph, student) == counts_before
    assert first is not None and second is not None
    assert (second.n_correct, second.n_incorrect) == (
        first.n_correct,
        first.n_incorrect,
    )
    async with sessionmaker() as session:
        row = await session.get(EventRow, event.id)
        assert row.processed_at is not None


async def test_recovery_without_the_graph_waits_instead_of_failing(
    sessionmaker, redis, student
):
    from arq import Retry

    ctx = {"sessionmaker": sessionmaker, "redis": redis, "neo4j": None}
    with pytest.raises(Retry):
        await jobs_infra.recover_graph_events(
            ctx, request_id="test", student_id=str(student), through_event_id=1
        )


async def test_the_watermark_bounds_the_job(sessionmaker, seeded_graph, redis, student):
    """Ответ, пришедший после снимка, остаётся следующему прогону (§13.3)."""
    down = _deps(None, redis)
    async with sessionmaker() as session:
        first_instance = await _issue_instance(session, student)
        first = await _answer(session, down, student, first_instance, "A")
        await session.commit()
    async with sessionmaker() as session:
        second_instance = await _issue_instance(session, student)
        second = await _answer(session, down, student, second_instance, "A")
        await session.commit()

    ctx = {"sessionmaker": sessionmaker, "redis": redis, "neo4j": seeded_graph}
    await jobs_infra.recover_graph_events(
        ctx, request_id="test", student_id=str(student), through_event_id=first.id
    )

    async with sessionmaker() as session:
        assert (await session.get(EventRow, first.id)).processed_at is not None
        assert (await session.get(EventRow, second.id)).processed_at is None
        assert await recovery.oldest_pending_id(session, student) == second.id


async def _counts(driver, student_id) -> tuple[int, int]:
    """(Evidence, KnowledgeState) of one student — the doubling detector."""
    async with driver.session() as session:
        result = await session.run(
            "MATCH (e:Evidence {student_id: $sid}) WITH count(e) AS ev "
            "MATCH (k:KnowledgeState {student_id: $sid}) "
            "RETURN ev AS evidence, count(k) AS states",
            sid=str(student_id),
        )
        record = await result.single()
    return (int(record["evidence"]), int(record["states"]))
