"""apply.mocks — 20-B1-phase2.md §7."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.apply.mocks import finish, start
from app.errors import NotFound, ValidationFailed
from app.events.dispatch import RuleDeps
from app.schemas.knowledge import ExamFormat, Section
from app.schemas.mocks import MockStartIn

pytestmark = pytest.mark.phase1

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(self, key, value, *, ex=None, nx=False):
        self.store[key] = value
        return True

    async def get(self, key):
        return self.store.get(key)

    async def incr(self, key):
        v = int(self.store.get(key, "0")) + 1
        self.store[key] = str(v)
        return v

    async def delete(self, key):
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


def _format() -> ExamFormat:
    return ExamFormat(
        exam_id="SAT_MATH",
        name="SAT Math",
        max_raw_score=44,
        sections=[
            Section(
                name="M1",
                n_items=22,
                minutes=35,
                item_types={"mcq4": 22},
                scoring_rule="mcq4: 1 per correct",
                calculator=True,
                adaptive=False,
                area_shares={"area.sat.algebra": 1.0},
                difficulty_shares={"2": 0.5, "3": 0.5},
                answer_forms=["integer"],
            )
        ],
        scale_table=None,
        scale_note=None,
        source="https://...",
        checked_at=NOW.date(),
        is_demo=True,
    )


def _start_body(kind: str = "mock_topic") -> MockStartIn:
    return MockStartIn(
        kind=kind,  # type: ignore[arg-type]
        exam_id="SAT_MATH",
        set_id=None,
        skill_id="math.alg.linear_eq",
        misconception_id=None,
    )


# --- start ---


async def test_start_graph_none_raises():
    with pytest.raises(ValidationFailed):
        await start(None, _deps(graph=None), uuid4(), _start_body())


async def test_start_no_format(monkeypatch):
    async def fake_format(driver, exam_id):
        return None

    monkeypatch.setattr("app.apply.mocks.canonical_q.get_exam_format", fake_format)

    with pytest.raises(NotFound):
        await start(None, _deps(graph=object()), uuid4(), _start_body())


async def test_start_no_templates(monkeypatch):
    async def fake_format(driver, exam_id):
        return _format()

    async def fake_templates(session, skill_ids):
        return {}

    monkeypatch.setattr("app.apply.mocks.canonical_q.get_exam_format", fake_format)
    monkeypatch.setattr(
        "app.apply.mocks.tasks_repo.list_templates_for_skills", fake_templates
    )

    with pytest.raises(NotFound):
        await start(None, _deps(graph=object()), uuid4(), _start_body())


async def test_start_no_skills(monkeypatch):
    # mock_topic без skill_id
    async def fake_format(driver, exam_id):
        return _format()

    monkeypatch.setattr("app.apply.mocks.canonical_q.get_exam_format", fake_format)

    body = MockStartIn(
        kind="mock_topic",
        exam_id="SAT_MATH",
        set_id=None,
        skill_id=None,
        misconception_id=None,
    )
    with pytest.raises(NotFound):
        await start(None, _deps(graph=object()), uuid4(), body)


# --- finish ---


async def test_finish_graph_none_raises(monkeypatch):
    async def fake_get_run(session, *args, **kwargs):
        return None

    monkeypatch.setattr("app.apply.mocks.mocks_repo.get_run", fake_get_run)

    with pytest.raises(NotFound):
        await finish(None, _deps(graph=None), uuid4(), uuid4())


async def test_finish_no_run(monkeypatch):
    async def fake_get_run(session, student_id, run_id):
        return None

    monkeypatch.setattr("app.apply.mocks.mocks_repo.get_run", fake_get_run)

    with pytest.raises(NotFound):
        await finish(None, _deps(graph=object()), uuid4(), uuid4())
