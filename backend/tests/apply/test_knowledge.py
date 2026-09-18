"""apply.knowledge read-models — 20-B1-phase2.md §7."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.apply.knowledge import (
    explain,
    misconceptions_view,
    states_view,
)
from app.events.dispatch import RuleDeps
from app.schemas.knowledge import (
    KnowledgeStateOut,
    MisconceptionStateOut,
    SkillRef,
    SkillWeight,
)

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
        name=f"name-{skill_id}",
        description="...",
        exam_ids=["SAT_MATH"],  # type: ignore[list-item]
        effort_h=4.0,
        base_half_life_h=None,
    )


def _weight(skill_id: str, weight: float = 3.0) -> SkillWeight:
    return SkillWeight(
        skill=_skill(skill_id),
        area_id="area.sat.algebra",
        weight=weight,
    )


def _state(
    skill_id: str, *, p_recall: float = 0.5, confidence: float = 0.8
) -> KnowledgeStateOut:
    return KnowledgeStateOut(
        skill_id=skill_id,
        exam_id="SAT_MATH",
        p_recall=p_recall,
        p_at_obs=p_recall,
        half_life_h=24.0,
        confidence=confidence,
        evidence_mass=1.0,
        n_correct=1,
        n_incorrect=0,
        n_partial=0,
        has_strong=True,
        last_observed_at=NOW - timedelta(days=1),
        created_at=NOW - timedelta(days=2),
    )


# --- states_view ---


async def test_states_view_graph_none_returns_empty():
    out = await states_view(None, _deps(graph=None), uuid4(), "SAT_MATH")
    assert out == []


async def test_states_view_with_skill_and_state(monkeypatch):
    sid = uuid4()

    async def fake_list(driver, exam_id):
        return [_weight("skill.a"), _weight("skill.b")]

    async def fake_states(driver, student_id, exam_id):
        return [_state("skill.a", p_recall=0.9, confidence=0.8)]

    async def fake_roots(driver, student_id, window_days):
        return []

    async def fake_history(driver, student_id, skill_id, exam_id, n=3):
        return []

    monkeypatch.setattr("app.apply.knowledge.canonical_q.list_exam_skills", fake_list)
    monkeypatch.setattr("app.apply.knowledge.personal_q.get_states", fake_states)
    monkeypatch.setattr("app.apply.knowledge.personal_q.list_root_causes", fake_roots)
    monkeypatch.setattr(
        "app.apply.knowledge.personal_q.get_state_history", fake_history
    )

    out = await states_view(None, _deps(graph=object()), sid, "SAT_MATH")
    assert len(out) == 2
    a = next(v for v in out if v.skill_id == "skill.a")
    b = next(v for v in out if v.skill_id == "skill.b")
    assert a.level == "shaky"  # p 0.9 < p_target_max 0.95
    assert b.confidence == 0.0
    assert b.n_evidence == 0


async def test_states_view_low_data_when_no_state(monkeypatch):
    sid = uuid4()

    async def fake_list(driver, exam_id):
        return [_weight("skill.a")]

    async def fake_states(driver, student_id, exam_id):
        return []

    async def fake_roots(driver, student_id, window_days):
        return []

    async def fake_history(driver, student_id, skill_id, exam_id, n=3):
        return []

    monkeypatch.setattr("app.apply.knowledge.canonical_q.list_exam_skills", fake_list)
    monkeypatch.setattr("app.apply.knowledge.personal_q.get_states", fake_states)
    monkeypatch.setattr("app.apply.knowledge.personal_q.list_root_causes", fake_roots)
    monkeypatch.setattr(
        "app.apply.knowledge.personal_q.get_state_history", fake_history
    )

    out = await states_view(None, _deps(graph=object()), sid, "SAT_MATH")
    assert out[0].level == "low_data"


# --- misconceptions_view ---


async def test_misconceptions_view_graph_none_returns_empty():
    out = await misconceptions_view(_deps(graph=None), uuid4(), "SAT_MATH")
    assert out == []


async def test_misconceptions_view_filters_visible(monkeypatch):
    sid = uuid4()

    async def fake_list(driver, exam_id):
        return [_weight("skill.a")]

    async def fake_misc(driver, student_id, skill_ids):
        return [
            MisconceptionStateOut(
                misconception_id="lib.suspected_one",
                name="...",
                status="suspected",
                occurrence_count=1,
                strong_count=0,
                consecutive_avoided=0,
                triggers={},
                first_seen_at=NOW - timedelta(days=1),
                updated_at=NOW,
                skill_ids=["skill.a"],
            ),
            MisconceptionStateOut(
                misconception_id="lib.disputed_one",
                name="...",
                status="disputed",
                occurrence_count=2,
                strong_count=0,
                consecutive_avoided=0,
                triggers={},
                first_seen_at=NOW - timedelta(days=1),
                updated_at=NOW,
                skill_ids=["skill.a"],
            ),
        ]

    monkeypatch.setattr("app.apply.knowledge.canonical_q.list_exam_skills", fake_list)
    monkeypatch.setattr("app.apply.knowledge.personal_q.get_misc_states", fake_misc)

    out = await misconceptions_view(_deps(graph=object()), sid, "SAT_MATH")
    # disputed → не видно
    assert all(m.status != "disputed" for m in out)


# --- explain ---


async def test_explain_graph_none_returns_empty():
    out = await explain(_deps(graph=None), uuid4(), "skill.a")
    assert out == []


async def test_explain_for_skill(monkeypatch):
    sid = uuid4()
    calls = []

    async def fake_list_evidence(driver, student_id, skill_id, limit=50):
        calls.append((skill_id, limit))
        return []

    monkeypatch.setattr(
        "app.apply.knowledge.personal_q.list_evidence", fake_list_evidence
    )

    await explain(_deps(graph=object()), sid, "skill.a")
    assert calls == [("skill.a", 50)]
