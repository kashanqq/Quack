"""apply.diagnostic — 20-B1-phase2.md §7."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.apply.diagnostic import finish, start
from app.errors import NotFound, ValidationFailed
from app.events.dispatch import RuleDeps
from app.schemas.knowledge import SkillRef, SkillWeight

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


def _skill(skill_id: str) -> SkillRef:
    return SkillRef(
        id=skill_id,
        name=skill_id,
        description="...",
        exam_ids=["SAT_MATH"],  # type: ignore[list-item]
        effort_h=4.0,
        base_half_life_h=None,
    )


def _weight(skill_id: str) -> SkillWeight:
    return SkillWeight(
        skill=_skill(skill_id),
        area_id="area.sat.algebra",
        weight=3.0,
    )


# --- start ---


async def test_start_graph_none_raises():
    with pytest.raises(ValidationFailed):
        await start(None, _deps(graph=None), uuid4(), "SAT_MATH", None)


async def test_start_no_skills(monkeypatch):
    async def fake_skills(driver, exam_id):
        return []

    async def fake_areas(driver, exam_id):
        return []

    monkeypatch.setattr(
        "app.apply.diagnostic.canonical_q.list_exam_skills", fake_skills
    )
    monkeypatch.setattr("app.apply.diagnostic.canonical_q.list_areas", fake_areas)

    with pytest.raises(NotFound):
        await start(None, _deps(graph=object()), uuid4(), "SAT_MATH", None)


# --- finish ---


async def test_finish_run_not_found(monkeypatch):
    async def fake_get(session, student_id, run_id):
        raise NotFound("diagnostic run not found")

    monkeypatch.setattr("app.apply.diagnostic._get_run", fake_get)

    with pytest.raises(NotFound):
        await finish(None, _deps(graph=object()), uuid4(), uuid4())
