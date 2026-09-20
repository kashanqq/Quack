"""Phase 4 end to end on live Postgres + Neo4j + Redis — §13.4.

The chain under test is the real one: an event is appended, `dispatch` runs
the phase-4 handlers, the outbox is flushed by hand (there is no HTTP layer
here), the job runs against the databases with a scripted `FakeLLMClient`,
and the read model is checked afterwards. Everything is keyed by fresh ids,
so runs do not interfere with each other or with the phase-3 flow.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.agents import jobs_phase4 as jobs
from app.config import KnowledgeParams, Settings
from app.db.engine import close_engine, create_engine, create_sessionmaker
from app.db.models import GeneratedText as GeneratedTextRow
from app.db.models import Set as SetRow
from app.db.models import SetTopic
from app.db.repo import profiles as profiles_repo
from app.db.repo import recommendations as recs_repo
from app.db.repo import soft_matches as soft_repo
from app.db.repo import summaries as summaries_repo
from app.db.repo import texts as texts_repo
from app.errors import LLMUnavailable
from app.events import handlers as _handlers  # noqa: F401  (таблица правил)
from app.events import store
from app.events.dispatch import RuleDeps, dispatch
from app.events.outbox import JobOutbox
from app.graph.queries import personal
from app.llm.fake import FakeLLMClient
from app.schemas.events import EventIn, EventType
from app.schemas.profile import ProfileUpdateIn
from app.schemas.texts import ExplanationOut, GuidelineOut, SetSummaryTextOut

pytestmark = [pytest.mark.integration, pytest.mark.phase4]

TOPIC = "test.phase2.skill.absolute"


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
async def saved_programs(sessionmaker, seeded_graph):
    """Ученик с двумя сохранёнными программами, закоммиченными по-настоящему.

    Общая фикстура `student_with_saved` живёт внутри откатываемой
    транзакции `db_session`, а задачи открывают свои сессии и такой записи
    не увидят.
    """
    from pathlib import Path

    from app.db.repo.programs import save_program
    from app.seed.programs import seed_programs_floor, validate_programs_floor

    path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "programs_floor"
        / "programs.json"
    )
    student_id = uuid4()
    await personal.ensure_student(seeded_graph, student_id)
    async with sessionmaker() as session:
        await seed_programs_floor(session, path)
        programs = validate_programs_floor(path)[:2]
        for program in programs:
            await save_program(session, student_id, program.id)
        await session.commit()
    return student_id, programs


def _deps(graph, redis, jobs_outbox: JobOutbox | None = None) -> RuleDeps:
    return RuleDeps(
        graph=graph,
        redis=redis,
        params=KnowledgeParams(),
        now=lambda: datetime.now(UTC),
        jobs=jobs_outbox if jobs_outbox is not None else JobOutbox(),
    )


async def _student_with_set(sessionmaker, graph, *, status="current"):
    student_id, set_id = uuid4(), uuid4()
    await personal.ensure_student(graph, student_id)
    async with sessionmaker() as session:
        session.add(
            SetRow(
                id=set_id,
                student_id=student_id,
                exam_id="SAT_MATH",
                status=status,
                position=0,
                deadline=date.today() + timedelta(days=10),
                reason="test",
                kind="regular",
                opened_at=datetime.now(UTC) - timedelta(days=3),
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


def _ctx(sessionmaker, graph, redis, llm):
    return {
        "sessionmaker": sessionmaker,
        "neo4j": graph,
        "redis": redis,
        "llm": llm,
        "job_id": "job-1",
        "job_try": 1,
    }


def _guideline() -> GuidelineOut:
    return GuidelineOut(
        how_to_prepare="Начни с определения модуля и разбора двух случаев.",
        must_know=["раскрывать модуль", "проверять оба случая", "сверять корни"],
        traps=[],
        what_to_solve=["простые уравнения с модулем", "неравенства"],
        summary="Коротко: два случая, обе проверки.",
    )


def _explanation() -> ExplanationOut:
    return ExplanationOut(
        text="Модуль — это расстояние до нуля.",
        key_points=["два случая", "проверка корней"],
    )


# --- 1. set.opened → pregenerate_set → GET-able texts (§13.4 п.1–2) ---


async def test_opening_a_set_pre_generates_its_texts(sessionmaker, seeded_graph, redis):
    student_id, set_id = await _student_with_set(sessionmaker, seeded_graph)
    outbox = JobOutbox()
    deps = _deps(seeded_graph, redis, outbox)

    async with sessionmaker() as session:
        event = await store.append(
            session,
            redis,
            EventIn(
                type=EventType.set_opened,
                payload={"set_id": str(set_id), "skill_ids": [TOPIC]},
                student_id=student_id,
                exam_id="SAT_MATH",
                set_id=set_id,
            ),
            dispatch_event=False,
        )
        await dispatch(session, event, deps)
        await session.commit()

    # Обработчик только записал намерение — задача ставится после коммита.
    [entry] = [item for item in outbox.entries if item.fn_name == "pregenerate_set"]
    assert entry.job_id.startswith(f"pregen:{set_id}:")
    assert entry.queue == "bulk"

    llm = FakeLLMClient([_guideline(), _explanation()])
    await jobs.pregenerate_set(
        _ctx(sessionmaker, seeded_graph, redis, llm), "req", set_id, student_id
    )

    async with sessionmaker() as session:
        [guideline] = (
            await session.scalars(
                select(GeneratedTextRow).where(
                    GeneratedTextRow.set_id == set_id,
                    GeneratedTextRow.kind == "guideline",
                )
            )
        ).all()
        # Объяснение навыка общее и не принадлежит ни ученику, ни сету —
        # оно переиспользуется между учениками (§3.1), поэтому ищется по
        # предмету с пустым владельцем.
        explanation = await texts_repo.last_ready(session, None, "explanation", TOPIC)
    assert guideline.status == "ready" and guideline.text
    assert guideline.prompt_version == "guideline_v1"
    assert guideline.student_id == student_id
    assert explanation is not None and explanation.text

    # Повторный прогон с тем же входом не тратит ни одного вызова модели.
    empty = FakeLLMClient([])
    await jobs.pregenerate_set(
        _ctx(sessionmaker, seeded_graph, redis, empty), "req", set_id, student_id
    )
    assert empty.calls == []


async def test_an_unavailable_model_leaves_the_rows_generating(
    sessionmaker, seeded_graph, redis
):
    student_id, set_id = await _student_with_set(sessionmaker, seeded_graph)
    from arq import Retry

    llm = FakeLLMClient([LLMUnavailable("llm unavailable")])
    with pytest.raises(Retry):
        await jobs.pregenerate_set(
            _ctx(sessionmaker, seeded_graph, redis, llm), "req", set_id, student_id
        )
    async with sessionmaker() as session:
        rows = (
            await session.scalars(
                select(GeneratedTextRow).where(GeneratedTextRow.set_id == set_id)
            )
        ).all()
    assert [row.status for row in rows if row.kind == "guideline"] == ["generating"]

    # Модель вернулась — следующий прогон доводит текст до ready.
    good = FakeLLMClient([_guideline(), _explanation()])
    await jobs.pregenerate_set(
        _ctx(sessionmaker, seeded_graph, redis, good), "req", set_id, student_id
    )
    async with sessionmaker() as session:
        rows = (
            await session.scalars(
                select(GeneratedTextRow).where(GeneratedTextRow.set_id == set_id)
            )
        ).all()
    assert {row.status for row in rows} == {"ready"}
    assert {row.kind for row in rows} >= {"guideline"}


# --- 2. set.completed → stats now, text later (§13.4 п.4) ---


async def test_completing_a_set_freezes_the_statistics_then_writes_the_text(
    sessionmaker, seeded_graph, redis
):
    student_id, set_id = await _student_with_set(sessionmaker, seeded_graph)
    outbox = JobOutbox()
    deps = _deps(seeded_graph, redis, outbox)

    async with sessionmaker() as session:
        event = await store.append(
            session,
            redis,
            EventIn(
                type=EventType.set_completed,
                payload={"set_id": str(set_id)},
                student_id=student_id,
                exam_id="SAT_MATH",
                set_id=set_id,
            ),
            dispatch_event=False,
        )
        await dispatch(session, event, deps)
        await session.commit()

    async with sessionmaker() as session:
        summary = await summaries_repo.get(session, set_id)
    # Статистика есть сразу — Обзор не ждёт модель (§4.1).
    assert summary is not None
    assert summary.status == "generating" and summary.text is None
    assert summary.stats.set_id == set_id

    assert [item.fn_name for item in outbox.entries if item.queue == "interactive"] == [
        "set_summary"
    ]

    llm = FakeLLMClient([SetSummaryTextOut(text="Сет закрыт, идём дальше.")])
    await jobs.set_summary(
        _ctx(sessionmaker, seeded_graph, redis, llm), "req", set_id, student_id
    )
    async with sessionmaker() as session:
        summary = await summaries_repo.get(session, set_id)
    assert summary.status == "ready"
    assert summary.text == "Сет закрыт, идём дальше."

    # Модель, назвавшая число не из статистики, оставляет отчёт без текста.
    other_student, other_set = await _student_with_set(sessionmaker, seeded_graph)
    async with sessionmaker() as session:
        event = await store.append(
            session,
            redis,
            EventIn(
                type=EventType.set_completed,
                payload={"set_id": str(other_set)},
                student_id=other_student,
                exam_id="SAT_MATH",
                set_id=other_set,
            ),
            dispatch_event=False,
        )
        await dispatch(session, event, _deps(seeded_graph, redis))
        await session.commit()
    liar = SetSummaryTextOut(text="Ты решил 137 задач!")
    await jobs.set_summary(
        _ctx(sessionmaker, seeded_graph, redis, FakeLLMClient([liar, liar])),
        "req",
        other_set,
        other_student,
    )
    async with sessionmaker() as session:
        summary = await summaries_repo.get(session, other_set)
    assert summary.status == "failed" and summary.text is None
    assert summary.stats is not None


# --- 3. profile.updated → soft_match (§13.4 п.5) ---


async def test_a_trait_summary_triggers_and_fills_the_soft_match(
    sessionmaker, seeded_graph, redis, saved_programs
):
    from app.agents.texts import _SoftMatchModelOut
    from app.apply.soft import summary_hash

    student_id, programs = saved_programs
    outbox = JobOutbox()
    deps = _deps(seeded_graph, redis, outbox)
    summary = "тёплый климат, небольшой город"

    async with sessionmaker() as session:
        await profiles_repo.apply_profile_update(
            session,
            student_id,
            ProfileUpdateIn(path="traits.summary", value=summary, by="user"),
        )
        event = await store.append(
            session,
            redis,
            EventIn(
                type=EventType.profile_updated,
                payload={"field": "traits.summary", "value": summary, "by": "user"},
                student_id=student_id,
            ),
            dispatch_event=False,
        )
        await dispatch(session, event, deps)
        await session.commit()

    digest = summary_hash(summary)
    [entry] = [item for item in outbox.entries if item.fn_name == "soft_match"]
    assert entry.job_id == f"softmatch:{student_id}:{digest[:12]}"
    # Быстрые правки резюме схлопываются в одну задачу (§1.3).
    assert entry.defer_by == KnowledgeParams().soft_match_debounce_s

    answer = _SoftMatchModelOut(
        score=0.8, fit_text="подходит: спокойный компактный город", confidence="high"
    )
    llm = FakeLLMClient([answer for _ in programs])
    await jobs.soft_match(
        _ctx(sessionmaker, seeded_graph, redis, llm),
        "req",
        student_id,
        [program.id for program in programs],
    )

    async with sessionmaker() as session:
        rows = await soft_repo.get_many(
            session,
            digest,
            [program.id for program in programs],
            "soft_match_v1",
        )
    assert rows
    for row in rows.values():
        assert 0.0 <= row.score <= 1.0
        assert row.stale is False
        if row.fit_text:
            assert not any(character.isdigit() for character in row.fit_text)


# --- 4. the Quack batch writes a feed the route can read (§13.4 п.7, п.11) ---


async def test_the_batch_writes_a_readable_feed(
    sessionmaker, seeded_graph, redis, saved_programs
):
    from app.apply import quack as apply_quack

    student_id, _programs = saved_programs
    deps = _deps(seeded_graph, redis)
    async with sessionmaker() as session:
        result = await apply_quack.run_batch(session, deps, student_id, urgent=False)
        await session.commit()

    async with sessionmaker() as session:
        items = await recs_repo.list_open(session, student_id)
    assert result.created == len(items)
    for item in items:
        # Каждая строка ленты объясняет себя и предлагает действие (§8.5).
        assert item.reason and item.action_text and item.title
        assert item.position == items.index(item)
        assert item.reason_hash
    # Повторный прогон ничего не создаёт заново — причины те же.
    async with sessionmaker() as session:
        again = await apply_quack.run_batch(session, deps, student_id, urgent=False)
        await session.commit()
    assert again.created == 0


async def test_accepting_a_recommendation_changes_the_profile(
    sessionmaker, seeded_graph, redis, saved_programs
):
    from app.schemas.events import RecommendationAcceptedPayload
    from app.schemas.quack import RecDraft, RecommendationAction

    student_id, _programs = saved_programs
    deps = _deps(seeded_graph, redis)
    draft = RecDraft(
        kind="pace_variant",
        urgency="urgent",
        title="SAT: добавить часы",
        reason="готовность позже теста",
        action_text="7 ч/нед",
        action=RecommendationAction(
            kind="profile_update", profile_path="pace.hours_per_week", profile_value=7
        ),
        reason_hash=f"cause-{uuid4().hex[:8]}",
        exam_id="SAT_MATH",
    )
    async with sessionmaker() as session:
        await recs_repo.reconcile(
            session, student_id, [draft], urgent_only=False, now=datetime.now(UTC)
        )
        await session.commit()
    async with sessionmaker() as session:
        [row] = [
            item
            for item in await recs_repo.list_open(session, student_id)
            if item.reason_hash == draft.reason_hash
        ]

    async with sessionmaker() as session:
        event = await store.append(
            session,
            redis,
            EventIn(
                type=EventType.recommendation_accepted,
                payload=RecommendationAcceptedPayload(
                    recommendation_id=row.id,
                    reason_hash=row.reason_hash,
                    kind=row.kind,
                    action=row.action,
                ).model_dump(mode="json"),
                student_id=student_id,
                exam_id="SAT_MATH",
            ),
            dispatch_event=False,
        )
        await dispatch(session, event, deps)
        await session.commit()

    async with sessionmaker() as session:
        profile = await profiles_repo.get_profile(session, student_id)
        updated = await recs_repo.get(session, student_id, row.id)
        nested = await store.list_by_type(
            session, student_id, [EventType.profile_updated], None, 50
        )
    # Приём сработал как обычная правка ученика (product-logic §6.1).
    assert profile.questionnaire.pace.hours_per_week.value == 7
    assert profile.questionnaire.pace.hours_per_week.mark == "stated"
    assert updated.status == "accepted"
    assert updated.decided_at is not None
    assert nested and nested[-1].payload["field"] == "pace.hours_per_week"
    assert nested[-1].payload["by"] == "user"


# --- 5. aggregates from the real event log (§13.4 п.10) ---


async def test_aggregates_are_computed_from_the_event_log(
    sessionmaker, seeded_graph, redis
):
    from app.apply import aggregates as apply_aggregates
    from app.db.repo import aggregates as aggregates_repo

    student_id = uuid4()
    await personal.ensure_student(seeded_graph, student_id)
    session_id = uuid4()
    base = datetime.now(UTC).replace(hour=6, minute=0, second=0, microsecond=0)
    async with sessionmaker() as session:
        for offset in (0, 10, 20):
            await store.append(
                session,
                redis,
                EventIn(
                    type=EventType.message_user,
                    payload={"text": "вопрос"},
                    student_id=student_id,
                    session_id=session_id,
                    chat_id=uuid4(),
                    occurred_at=base + timedelta(minutes=offset),
                ),
                dispatch_event=False,
            )
        await session.commit()

    deps = _deps(seeded_graph, redis)
    async with sessionmaker() as session:
        summary = await apply_aggregates.run(session, deps, student_id)
        await session.commit()
    assert summary is not None
    assert summary.active_days == 1

    async with sessionmaker() as session:
        activity = await aggregates_repo.activity(
            session,
            student_id,
            today=base.date(),
            days=14,
            tz=KnowledgeParams().activity_tz,
            hours_declared=None,
        )
    assert activity.window_days == 14
    assert activity.tz == "Asia/Almaty"
    assert sum(day.chat_messages for day in activity.days) == 3
    assert activity.active_days == 1

    # Повторный расчёт без новых событий — тот же результат, без работы.
    async with sessionmaker() as session:
        again = await apply_aggregates.run(session, deps, student_id)
    assert again.as_of_event_id == summary.as_of_event_id
    assert again.active_days_by_day == summary.active_days_by_day
