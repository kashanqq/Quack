"""apply.tasks.issue — 20-B1-phase2.md §7."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.apply.tasks import issue
from app.errors import NotFound, ValidationFailed
from app.events.dispatch import RuleDeps
from app.schemas.sets import SetOut, SetProgress, TopicOut
from app.schemas.tasks import (
    DistractorSpec,
    ParamSpec,
    TaskRequestIn,
    TaskTemplateSpec,
)

pytestmark = pytest.mark.phase1

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(self, key: str, value: str, *, ex=None, nx=False):
        self.store[key] = value
        return True

    async def get(self, key: str):
        return self.store.get(key)

    async def incr(self, key: str) -> int:
        v = int(self.store.get(key, "0")) + 1
        self.store[key] = str(v)
        return v

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)


def _deps(graph=None) -> RuleDeps:
    return RuleDeps(
        graph=graph,
        redis=_FakeRedis(),
        params=_params(),
        now=lambda: NOW,
    )


def _params():
    from app.config import KnowledgeParams

    return KnowledgeParams()


def _template(skill_id: str = "math.alg.linear_eq") -> TaskTemplateSpec:
    # Шаблон из memory-architecture §3.1 — дистракторы гарантированно
    # не коллапсируют при constraints b > c и b, c > 0.
    return TaskTemplateSpec(
        id="tpl.test.abs_eq_sum_roots",
        exam_id="SAT_MATH",
        type="mcq4",
        difficulty=3,
        skill_id=skill_id,
        tags=["negative_branch", "sum_of_roots"],
        time_reference_sec=75,
        kind="template",
        params={
            "a": ParamSpec(range=(2, 5)),
            "b": ParamSpec(range=(2, 12)),
            "c": ParamSpec(range=(1, 9)),
        },
        constraints=["(b + c) % a == 0", "(b - c) % a == 0", "b > c"],
        stem="|{a}x − {b}| = {c}. Чему равна сумма корней?",
        correct="2*b/a",
        distractors=[
            DistractorSpec(expr="(b + c)/a", misconception_id=None),
            DistractorSpec(expr="(b - c)/a", misconception_id=None),
            DistractorSpec(expr="-2*b/a", misconception_id=None),
            DistractorSpec(expr="2*c/a", misconception_id=None),
        ],
        solution=["Раскрыть модуль", "x1, x2", "Сумма = {answer}"],
    )


def _req(
    *,
    skill_id: str | None = None,
    set_id=None,
    with_trap: str | None = None,
    mode: str = "topic",
) -> TaskRequestIn:
    """TaskRequestIn with all required fields explicitly filled in."""
    return TaskRequestIn(
        skill_id=skill_id,
        set_id=set_id,
        mode=mode,  # type: ignore[arg-type]
        with_trap=with_trap,
        exclude_seen=True,
    )


# --- tests ---


async def test_issue_requires_skill_or_set():
    sid = uuid4()
    req = _req()
    with pytest.raises(ValidationFailed):
        await issue(None, _deps(), sid, req)


async def test_issue_no_templates(monkeypatch):
    async def fake_templates(session, skill_ids):
        return {}

    async def fake_seen(session, student_id, skill_ids):
        return {}

    monkeypatch.setattr(
        "app.apply.tasks.tasks_repo.list_templates_for_skills", fake_templates
    )
    monkeypatch.setattr("app.apply.tasks.tasks_repo.get_seen_many", fake_seen)

    sid = uuid4()
    req = _req(skill_id="math.alg.linear_eq")
    with pytest.raises(NotFound):
        await issue(None, _deps(), sid, req)


async def test_issue_returns_instance_out(monkeypatch):
    sid = uuid4()
    spec = _template()

    async def fake_templates(session, skill_ids):
        return {spec.skill_id: [spec]}

    async def fake_seen(session, student_id, skill_ids):
        return {}

    inserted: list = []

    async def fake_insert(
        session, student_id, inst, *, mode=None, issued_event_id=None
    ):
        inserted.append((inst, mode, issued_event_id))
        return None

    appended: list = []

    async def fake_append(session, redis, ev, *, dispatch_event=True):
        appended.append(ev)
        return SimpleNamespace(id=len(appended))

    async def fake_grades(session, student_id, skill_id, limit=2):
        return []

    monkeypatch.setattr(
        "app.apply.tasks.tasks_repo.list_templates_for_skills", fake_templates
    )
    monkeypatch.setattr("app.apply.tasks.tasks_repo.get_seen_many", fake_seen)
    monkeypatch.setattr("app.apply.tasks.tasks_repo.insert_instance", fake_insert)
    monkeypatch.setattr("app.apply.tasks.tasks_repo.last_grades_for_skill", fake_grades)
    monkeypatch.setattr("app.apply.tasks.events_store.append", fake_append)

    chat_id = uuid4()
    req = _req(skill_id="math.alg.linear_eq", mode="chat")
    out = await issue(None, _deps(), sid, req, chat_id=chat_id)

    assert out.skill_id == spec.skill_id
    assert out.template_id == spec.id
    assert out.options  # непраздно
    assert not hasattr(out, "answer")
    assert len(appended) == 1
    # Задача репетитора видна окну наблюдателя: событие привязано к чату,
    # у экземпляра есть issued_event_id и режим.
    assert appended[0].chat_id == chat_id
    assert appended[0].payload["via"] == "chat"
    instance, mode, issued_event_id = inserted[0]
    assert mode == "chat"
    assert issued_event_id == 1
    assert str(instance.id) == str(appended[0].payload["instance_id"])


async def test_issue_from_set_picks_first_open_topic(monkeypatch):
    sid = uuid4()
    set_id = uuid4()
    spec = _template()

    async def fake_get_set(session, student_id, sid_):
        return SetOut(
            id=set_id,
            exam_id="SAT_MATH",
            area_ids=[],
            status="current",
            kind="regular",
            position=0,
            deadline=date(2026, 10, 1),
            reason="...",
            topics=[
                TopicOut(
                    skill_id="a",
                    name="a",
                    kind="topic",
                    position=0,
                    status="closed",
                    level="solid",
                    is_root=False,
                    misconception_labels=[],
                    subtitle=None,
                ),
                TopicOut(
                    skill_id=spec.skill_id,
                    name=spec.skill_id,
                    kind="topic",
                    position=1,
                    status="open",
                    level="weak",
                    is_root=False,
                    misconception_labels=[],
                    subtitle=None,
                ),
            ],
            progress=SetProgress(
                topics_closed=1, topics_total=2, tasks_answered=0, tasks_correct=0
            ),
        )

    async def fake_templates(session, skill_ids):
        return {spec.skill_id: [spec]}

    async def fake_seen(session, student_id, skill_ids):
        return {}

    async def fake_insert(
        session, student_id, inst, *, mode=None, issued_event_id=None
    ):
        return None

    async def fake_append(session, redis, ev, *, dispatch_event=True):
        return SimpleNamespace(id=1)

    async def fake_grades(session, student_id, skill_id, limit=2):
        return []

    monkeypatch.setattr("app.apply.tasks.sets_repo.get_set", fake_get_set)
    monkeypatch.setattr(
        "app.apply.tasks.tasks_repo.list_templates_for_skills", fake_templates
    )
    monkeypatch.setattr("app.apply.tasks.tasks_repo.get_seen_many", fake_seen)
    monkeypatch.setattr("app.apply.tasks.tasks_repo.insert_instance", fake_insert)
    monkeypatch.setattr("app.apply.tasks.tasks_repo.last_grades_for_skill", fake_grades)
    monkeypatch.setattr("app.apply.tasks.events_store.append", fake_append)

    req = _req(set_id=set_id)
    out = await issue(None, _deps(), sid, req)
    assert out.skill_id == spec.skill_id
