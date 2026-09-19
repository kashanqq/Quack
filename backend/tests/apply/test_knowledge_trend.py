"""states_view trend direction (found while building the phase-3 context:
the history comes newest first, `words.trend` wants oldest first)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.apply import knowledge
from app.config import KnowledgeParams
from app.events.dispatch import RuleDeps
from app.schemas.knowledge import KnowledgeStateOut, SkillRef, SkillWeight

pytestmark = pytest.mark.phase3

NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def _state(p, hours_ago):
    at = NOW - timedelta(hours=hours_ago)
    return KnowledgeStateOut(
        skill_id="s", exam_id="SAT_MATH", p_recall=p, p_at_obs=p, half_life_h=48,
        confidence=0.6, evidence_mass=1, n_correct=1, n_incorrect=0, n_partial=0,
        has_strong=True, last_observed_at=at, created_at=at,
    )  # fmt: skip


async def test_rising_history_reads_as_up(monkeypatch, redis):
    newest_first = [_state(0.8, 1), _state(0.6, 10), _state(0.4, 20)]
    skill = SkillRef(
        id="s", name="S", description="", exam_ids=["SAT_MATH"], effort_h=1
    )
    monkeypatch.setattr(
        knowledge.canonical_q,
        "list_exam_skills",
        AsyncMock(return_value=[SkillWeight(skill=skill, area_id="a", weight=1)]),
    )
    monkeypatch.setattr(
        knowledge.personal_q, "get_states", AsyncMock(return_value=[newest_first[0]])
    )
    monkeypatch.setattr(
        knowledge.personal_q, "list_root_causes", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        knowledge.personal_q, "get_state_history", AsyncMock(return_value=newest_first)
    )
    monkeypatch.setattr(knowledge, "p_target_for", AsyncMock(return_value=0.9))
    deps = RuleDeps(
        graph=object(), redis=redis, params=KnowledgeParams(), now=lambda: NOW
    )

    [view] = await knowledge.states_view(object(), deps, uuid4(), "SAT_MATH")

    assert view.trend == "up"
