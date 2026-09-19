"""Rules for canonization results (docs/tz/phase3-agents.md §3.11, §6.10)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.apply import observation as rule
from app.config import KnowledgeParams
from app.events.dispatch import GraphUnavailable, RuleDeps
from app.schemas.events import Event, EventType
from tests.apply._fake_graph import NOW, FakeGraph, mock

pytestmark = pytest.mark.phase3

SKILL = "math.alg.abs_value_eq"


@pytest.fixture
def world(monkeypatch, redis):
    graph = FakeGraph()
    graph.install(monkeypatch, rule)
    monkeypatch.setattr(rule.store, "get_event", mock(None))
    monkeypatch.setattr(rule.messages_repo, "list_by_event_ids", mock({}))
    deps = RuleDeps(
        graph=object(), redis=redis, params=KnowledgeParams(), now=lambda: NOW
    )
    return graph, deps


def _event(type_, payload, event_id=900) -> Event:
    return Event(
        id=event_id,
        type=type_,
        payload=payload,
        student_id=uuid4(),
        occurred_at=NOW,
        ingested_at=NOW,
        exam_id="SAT_MATH",
    )


def _canonized(mid="lib.x"):
    return _event(
        EventType.misconception_canonized,
        {
            "source_event_id": 500,
            "ordinal": 1,
            "skill_id": SKILL,
            "canonical_id": mid,
            "similarity": 0.95,
            "decided_by": "threshold",
            "name": "n",
            "description": "теряет ветвь",
            "error_class": "conceptual",
        },
    )


async def test_apply_canonized_creates_evidence_and_state(world):
    graph, deps = world
    event = _canonized()

    result = await rule.apply_misconception_canonized(object(), event, deps)

    evidence = graph.evidence[(900, SKILL, 0)]
    assert (evidence.kind, evidence.tier, evidence.direction) == (
        "misconception_hit",
        2,
        -1,
    )
    assert graph.misc["lib.x"].status == "suspected"
    assert result.applied == 1 and result.knowledge_version == 1

    again = await rule.apply_misconception_canonized(object(), event, deps)
    assert again.applied == 0
    assert len(graph.evidence) == 1
    assert again.knowledge_version == 1


async def test_apply_personal_created_merges_node(world):
    graph, deps = world
    event = _event(
        EventType.misconception_personal_created,
        {
            "misconception_id": "pers.abc.putaet-znak",
            "source_event_id": 500,
            "ordinal": 1,
            "skill_id": SKILL,
            "name": "n",
            "description": "d",
            "error_class": "procedural",
            "embedding": [0.1] * 384,
            "best_similarity": None,
        },
    )

    await rule.apply_misconception_personal_created(object(), event, deps)
    await rule.apply_misconception_personal_created(object(), event, deps)

    assert list(graph.personal_nodes) == ["pers.abc.putaet-znak"]
    assert graph.misc["pers.abc.putaet-znak"].status == "suspected"
    assert len(graph.evidence) == 1


async def test_graph_down(world):
    _graph, deps = world
    deps.graph = None
    assert (
        await rule.apply_misconception_canonized(object(), _canonized(), deps)
        is GraphUnavailable
    )
