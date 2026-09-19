"""apply_task_answered — memory-architecture §8.2.

Unit tests using monkeypatched repositories and a None graph.
Integration cases live behind @pytest.mark.integration and skip without
a live Postgres + Neo4j.

Source: 20-B1-phase2.md §8.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.apply.task_answered import apply_task_answered, apply_task_skipped
from app.events.dispatch import RuleDeps
from app.schemas.events import Event, EventType, TaskAnsweredPayload
from app.schemas.tasks import Option, TaskInstance

pytestmark = pytest.mark.phase1

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def _instance(
    *,
    correct_key: str = "A",
    wrong_key: str = "B",
    misc_id: str | None = "lib.abs_single_branch",
) -> TaskInstance:
    return TaskInstance(
        id=uuid4(),
        template_id="tpl.sat.alg.abs_eq_sum_roots",
        seed=1,
        exam_id="SAT_MATH",
        type="mcq4",
        skill_id="math.alg.abs_value_eq",
        stem_rendered="...",
        options=[
            Option(
                key=correct_key, text="correct", correct=True, misconception_id=None
            ),
            Option(
                key=wrong_key, text="wrong", correct=False, misconception_id=misc_id
            ),
            Option(key="C", text="d2", correct=False, misconception_id=None),
            Option(key="D", text="d3", correct=False, misconception_id=None),
        ],
        answer=correct_key,
        trap_answers=[],
        solution_rendered=["шаг 1", "шаг 2"],
        figure_url=None,
        time_reference_sec=60,
        difficulty=3,
        tags=[],
    )


def _event(
    *,
    student_id,
    instance_id,
    answer: str = "A",
    type_: EventType = EventType.task_answered,
) -> Event:
    payload = TaskAnsweredPayload(
        instance_id=instance_id,
        answer=answer,
        time_spent_sec=30,
        mode="topic",
        session_minute=5,
        after_guideline=False,
        hint_level_before=0,
    ).model_dump(mode="json")
    return Event(
        id=1,
        type=type_,
        payload=payload,
        student_id=student_id,
        session_id=None,
        exam_id="SAT_MATH",
        set_id=None,
        topic_skill_id=None,
        chat_id=None,
        occurred_at=NOW,
        extractor_version=None,
        source_event_ids=None,
        ingested_at=NOW,
        processed_at=None,
    )


# --- unit: graph unavailable ---


async def test_apply_with_graph_none_returns_result_without_state(monkeypatch):
    sid = uuid4()
    inst = _instance()
    event = _event(student_id=sid, instance_id=inst.id, answer="A")

    called = {}

    async def fake_get_instance(session, student_id, instance_id):
        called["get_instance"] = (student_id, instance_id)
        return inst

    async def fake_mark_answered(session, instance_id, answered_at, correct):
        called["mark_answered"] = (instance_id, correct)

    async def fake_bump_seen(session, student_id, template_id):
        called["bump_seen"] = (student_id, template_id)

    async def fake_answered_at(session, instance_id):
        return None

    monkeypatch.setattr(
        "app.apply.task_answered.tasks_repo.get_instance", fake_get_instance
    )
    monkeypatch.setattr(
        "app.apply.task_answered.tasks_repo.get_answered_at", fake_answered_at
    )
    monkeypatch.setattr(
        "app.apply.task_answered.tasks_repo.mark_answered", fake_mark_answered
    )
    monkeypatch.setattr("app.apply.task_answered.tasks_repo.bump_seen", fake_bump_seen)

    class _Redis:
        async def incr(self, key):
            return 7

    monkeypatch.setattr("app.apply.task_answered.bump", lambda redis, sid_: _async(7))

    deps = RuleDeps(graph=None, redis=_Redis(), params=_params(), now=lambda: NOW)
    result = await apply_task_answered(None, event, deps)

    assert result.grade.correct is True
    assert result.state_after is None
    assert result.solution == ["шаг 1", "шаг 2"]
    assert called["get_instance"] == (sid, inst.id)
    # при graph=None мы не помечаем ответ и не бампаем seen
    assert "mark_answered" not in called
    assert "bump_seen" not in called


async def test_apply_missing_instance_returns_empty_result(monkeypatch):
    sid = uuid4()
    event = _event(student_id=sid, instance_id=uuid4())

    async def fake_get_instance(session, student_id, instance_id):
        return None

    async def fake_answered_at(session, instance_id):
        return None

    monkeypatch.setattr(
        "app.apply.task_answered.tasks_repo.get_instance", fake_get_instance
    )
    monkeypatch.setattr(
        "app.apply.task_answered.tasks_repo.get_answered_at", fake_answered_at
    )

    class _Redis:
        async def incr(self, key):
            return 0

    deps = RuleDeps(graph=None, redis=_Redis(), params=_params(), now=lambda: NOW)
    result = await apply_task_answered(None, event, deps)
    assert result.grade.correct is False
    assert result.state_after is None
    assert result.knowledge_version == 0


async def test_apply_is_idempotent_on_a_repeated_dispatch(monkeypatch):
    """Повторный dispatch того же task.answered не двигает счётчики.

    `bump_seen` и `mark_answered` не идемпотентны сами по себе, поэтому
    обработчик выходит раньше, если экземпляр уже отвечен (§8.2).
    """
    sid = uuid4()
    inst = _instance()
    event = _event(student_id=sid, instance_id=inst.id, answer="A")
    calls: list[str] = []

    async def fake_get_instance(session, student_id, instance_id):
        return inst

    async def fake_answered_at(session, instance_id):
        return NOW  # уже отвечено

    async def fake_mark_answered(session, instance_id, answered_at, correct):
        calls.append("mark_answered")

    async def fake_bump_seen(session, student_id, template_id):
        calls.append("bump_seen")

    monkeypatch.setattr(
        "app.apply.task_answered.tasks_repo.get_instance", fake_get_instance
    )
    monkeypatch.setattr(
        "app.apply.task_answered.tasks_repo.get_answered_at", fake_answered_at
    )
    monkeypatch.setattr(
        "app.apply.task_answered.tasks_repo.mark_answered", fake_mark_answered
    )
    monkeypatch.setattr("app.apply.task_answered.tasks_repo.bump_seen", fake_bump_seen)

    class _Redis:
        async def incr(self, key):
            return 7

        async def get(self, key):
            return b"7"

    deps = RuleDeps(graph=object(), redis=_Redis(), params=_params(), now=lambda: NOW)
    result = await apply_task_answered(None, event, deps)

    assert result.grade.correct is True
    # Версия модели знаний — текущая, а не ноль: ничего не изменилось,
    # но и «версии нет» это не значит.
    assert result.knowledge_version == 7
    assert result.solution == ["шаг 1", "шаг 2"]
    assert calls == []


# --- task.skipped ---


async def test_apply_task_skipped_does_nothing():
    sid = uuid4()
    event = _event(student_id=sid, instance_id=uuid4(), type_=EventType.task_skipped)

    class _Redis:
        async def incr(self, key):
            return 0

    deps = RuleDeps(graph=None, redis=_Redis(), params=_params(), now=lambda: NOW)
    # не падает
    await apply_task_skipped(None, event, deps)


# --- helpers ---


def _params():
    from app.config import KnowledgeParams

    return KnowledgeParams()


def _async(value):
    async def _coro():
        return value

    return _coro()
