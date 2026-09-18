"""E2E — сквозной сценарий шагов 4-8 product-logic через роутеры.

Unit-транспорт: все apply.* и repo замоканы. Проверяем, что роуты
связаны в правильную цепочку и отдают осмысленные ответы.

Source: 10-B3-phase2.md §8 (test_e2e_rules).
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api import profile as profile_api
from app.api import sets as sets_api
from app.api.auth import issue_token
from app.config import KnowledgeParams
from app.events import store
from app.events.dispatch import RuleDeps
from app.keys import knowledge_version
from app.main import create_app
from app.schemas.events import Event
from app.schemas.knowledge import SkillStateView
from app.schemas.profile import Profile
from app.schemas.sets import SetsByExam
from app.schemas.tasks import (
    AnswerResult,
    Grade,
    OptionOut,
    TaskInstanceOut,
)

pytestmark = pytest.mark.phase2


class FakeRedis:
    def __init__(self, student_id):
        self.values = {knowledge_version(str(student_id)): "5"}

    async def get(self, key):
        return self.values.get(key)

    async def incr(self, key):
        v = int(self.values.get(key, "0")) + 1
        self.values[key] = str(v)
        return v

    async def set(self, key, value, *, ex=None, nx=False):
        self.values[key] = str(value)
        return True

    async def delete(self, key):
        self.values.pop(key, None)


def _task_out(skill_id: str = "sat.alg.slope_lines") -> TaskInstanceOut:
    return TaskInstanceOut(
        id=uuid4(),
        template_id="tpl.test",
        exam_id="SAT_MATH",
        type="mcq4",
        skill_id=skill_id,
        stem_rendered="2 + 2?",
        options=[OptionOut(key="A", text="4"), OptionOut(key="B", text="5")],
        figure_url=None,
        time_reference_sec=60,
        difficulty=3,
        tags=[],
        mode="topic",
        provenance="template",
    )


def _skill_view(sid: str, *, n_evidence: int = 0) -> SkillStateView:
    return SkillStateView(
        skill_id=sid,
        name=sid,
        area_id="area.sat.algebra",
        exam_id="SAT_MATH",
        weight=3.0,
        p_target=0.9,
        level="shaky",
        p_recall=0.5,
        confidence=0.7,
        trend="flat",
        due_at=None,
        is_root=False,
        n_evidence=n_evidence,
    )


@pytest.fixture
def transport(monkeypatch, fake_apply):
    student_id = uuid4()
    session = object()
    redis = FakeRedis(student_id)
    deps_value = RuleDeps(
        graph=None,
        redis=redis,
        params=KnowledgeParams(),
        now=lambda: datetime(2026, 9, 18, 12, tzinfo=UTC),
    )
    app = create_app()
    events: list[Event] = []
    skills_state = {"n": 0}

    async def session_override():
        yield session

    async def append(received_session, received_redis, event_in, **kwargs):
        event = Event(
            **event_in.model_dump(exclude={"occurred_at"}),
            occurred_at=deps_value.now(),
            ingested_at=deps_value.now(),
            id=len(events) + 1,
        )
        events.append(event)
        return event

    app.dependency_overrides[deps.get_session] = session_override
    app.dependency_overrides[deps.get_rule_deps] = lambda: deps_value
    monkeypatch.setattr(store, "append", append)

    # profile repo — не лезем в реальный Postgres
    async def fake_apply_profile_update(received_session, owner, body):
        return Profile(student_id=owner)

    monkeypatch.setattr(
        profile_api.profile_repo, "apply_profile_update", fake_apply_profile_update
    )

    # set repo — возвращаем пусто
    async def fake_list_sets(received_session, owner, exam_id):
        return []

    monkeypatch.setattr(sets_api.set_repo, "list_sets", fake_list_sets)

    async def fake_forecast_get(received_session, owner, exam_id):
        return None

    monkeypatch.setattr(sets_api.forecast_repo, "get", fake_forecast_get)

    # apply.tasks.issue → фейковая задача
    issue = fake_apply("app.apply.tasks.issue", _task_out())

    # apply.task_answered → фейковый AnswerResult
    apply_answer = fake_apply(
        "app.apply.task_answered.apply_task_answered",
        AnswerResult(
            grade=Grade(correct=True),
            solution=["шаг"],
            state_after=None,
            misconception_change=None,
            state_words="уверенно",
            knowledge_version=6,
        ),
    )

    # apply.sets.rebuild_sets → пустой SetsByExam
    rebuild = fake_apply("app.apply.sets.rebuild_sets", None)
    rebuild.return_value = SetsByExam(
        exam_id="SAT_MATH", forecast=None, current=None, upcoming=[], done=[]
    )

    # apply.knowledge.* → минимальные ответы
    async def states_view(session_, deps_, student_, exam_id):
        return [_skill_view("sat.alg.slope_lines", n_evidence=skills_state["n"])]

    async def misconceptions_view(deps_, student_, exam_id):
        return []

    async def explain(deps_, student_, node_id):
        return []

    monkeypatch.setattr("app.apply.knowledge.states_view", states_view)
    monkeypatch.setattr("app.apply.knowledge.misconceptions_view", misconceptions_view)
    monkeypatch.setattr("app.apply.knowledge.explain", explain)

    return SimpleNamespace(
        app=app,
        student_id=student_id,
        session=session,
        deps=deps_value,
        events=events,
        issue=issue,
        apply_answer=apply_answer,
        rebuild=rebuild,
        skills_state=skills_state,
    )


def _client(transport):
    client = TestClient(transport.app)
    client.cookies.set(
        "quack_token", issue_token(transport.student_id, "student@quack.kz")
    )
    return client


# --- step 4: PATCH /profile записывает событие profile.updated ---


def test_step4_patch_profile_records_event(transport):
    with _client(transport) as client:
        r = client.patch(
            "/profile",
            json={
                "path": "preferences.budget_per_year",
                "value": 30000,
                "by": "user",
            },
        )
    assert r.status_code == 200
    types = [e.type.value for e in transport.events]
    assert "profile.updated" in types


# --- step 7: POST /tasks → GET /knowledge видит n_evidence ---


def test_step7_answer_task_bumps_knowledge(transport):
    with _client(transport) as client:
        issue_r = client.post(
            "/tasks",
            json={
                "skill_id": "sat.alg.slope_lines",
                "set_id": None,
                "mode": "topic",
                "with_trap": None,
                "exclude_seen": True,
            },
        )
    assert issue_r.status_code == 201
    assert transport.issue.await_count == 1

    transport.skills_state["n"] = 1

    with _client(transport) as client:
        k_r = client.get("/knowledge?exam_id=SAT_MATH")
    assert k_r.status_code == 200
    skills = k_r.json()["skills"]
    assert any(s["n_evidence"] == 1 for s in skills)


# --- step 8: GET /sets → rebuild_sets вызван, есть версия ---


def test_step8_sets_rebuilds_once(transport):
    with _client(transport) as client:
        r = client.get("/sets?exam_id=SAT_MATH")
    assert r.status_code == 200
    assert r.headers["X-Knowledge-Version"] == "5"
