"""An in-memory personal graph for rule tests (phase3 §6.9–§6.10).

Replaces the `personal_q` / `canonical_q` functions `app.apply.observation`
calls, keeping just enough state (states, misconception states, evidence
keys, roots) to check what the rule writes and that a replay writes nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

from neo4j.exceptions import ServiceUnavailable

from app.graph.queries.personal import evidence_id
from app.schemas.knowledge import (
    EvidenceIn,
    EvidenceOut,
    KnowledgeStateOut,
    MisconceptionChange,
    MisconceptionRef,
    MisconceptionStateOut,
    Prerequisite,
)

NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


def state(skill_id: str, p: float = 0.6, h: float = 48, **kw: Any) -> KnowledgeStateOut:
    values = dict(
        skill_id=skill_id,
        exam_id="SAT_MATH",
        p_recall=p,
        p_at_obs=p,
        half_life_h=h,
        confidence=0.6,
        evidence_mass=1.0,
        n_correct=1,
        n_incorrect=0,
        n_partial=0,
        has_strong=False,
        last_observed_at=NOW,
        created_at=NOW,
    )
    values.update(kw)
    return KnowledgeStateOut(**values)


def misc(
    mid: str, status="suspected", occ=1, strong=0, avoided=0, skill="s"
) -> MisconceptionStateOut:
    return MisconceptionStateOut(
        misconception_id=mid,
        name=mid,
        status=status,
        occurrence_count=occ,
        strong_count=strong,
        consecutive_avoided=avoided,
        triggers={},
        first_seen_at=NOW,
        updated_at=NOW,
        skill_ids=[skill],
    )


class FakeGraph:
    def __init__(self) -> None:
        self.states: dict[tuple[str, str], KnowledgeStateOut] = {}
        self.history: list[KnowledgeStateOut] = []
        self.misc: dict[str, MisconceptionStateOut] = {}
        self.evidence: dict[tuple[int, str, int], EvidenceIn] = {}
        self.roots: set[tuple[str, str]] = set()
        self.prereqs: dict[str, list[str]] = {}
        self.library: dict[str, list[str]] = {}
        self.personal_nodes: dict[str, dict] = {}
        self.fail_after: int | None = None
        self.tx_calls = 0
        self.order: list[str] = []

    # canonical
    async def get_prerequisites(self, _driver, skill_id, depth=2):
        return [
            Prerequisite(skill_id=s, strength=1.0, depth=1)
            for s in self.prereqs.get(skill_id, [])
        ]

    async def list_misconceptions_for_skill(self, _driver, skill_id):
        return [
            MisconceptionRef(
                id=m,
                name=m,
                description=m,
                error_class="conceptual",
                skill_ids=[skill_id],
            )
            for m in self.library.get(skill_id, [])
        ]

    async def create_personal_misconception(
        self,
        _driver,
        student_id,
        mid,
        name,
        description,
        error_class,
        skill_id,
        embedding,
        source_event_id,
        ordinal,
    ):
        self.personal_nodes.setdefault(
            mid, {"skill_id": skill_id, "embedding": embedding}
        )
        self.library.setdefault(skill_id, [])
        return MisconceptionRef(
            id=mid,
            name=name,
            description=description,
            error_class=error_class,
            skill_ids=[skill_id],
        )

    # personal
    async def get_state(self, _driver, _sid, skill_id, exam_id):
        return self.states.get((skill_id, exam_id))

    async def get_misc_states(self, _driver, _sid, skill_ids):
        return [m for m in self.misc.values() if set(m.skill_ids) & set(skill_ids)]

    async def list_evidence_keys_for_event(self, _driver, _sid, event_id):
        return {
            (skill, ordinal)
            for (eid, skill, ordinal) in self.evidence
            if eid == event_id
        }

    async def apply_chat_observation_tx(
        self,
        _driver,
        _sid,
        ev: EvidenceIn,
        new_state,
        change: MisconceptionChange | None,
        triggers,
        source_event_id,
        *,
        cross_state=None,
    ):
        self.tx_calls += 1
        self.order.append(f"tx:{ev.skill_id}:{ev.ordinal}")
        if self.fail_after is not None and self.tx_calls > self.fail_after:
            raise ServiceUnavailable("down")
        key = (ev.event_id, ev.skill_id, ev.ordinal)
        if key not in self.evidence:
            self.evidence[key] = ev
            self.states[(new_state.skill_id, new_state.exam_id)] = new_state
            self.history.append(new_state)
            if cross_state is not None:
                self.states[(cross_state.skill_id, cross_state.exam_id)] = cross_state
            if change is not None:
                old = self.misc.get(change.misconception_id)
                self.misc[change.misconception_id] = misc(
                    change.misconception_id,
                    status=change.to_status,
                    occ=change.counters["occurrence_count"],
                    strong=change.counters["strong_count"],
                    avoided=change.counters["consecutive_avoided"],
                    skill=old.skill_ids[0] if old else ev.skill_id,
                ).model_copy(update={"triggers": triggers or {}})
        return evidence_id(*key)

    async def latest_incorrect_evidence(self, _driver, _sid, skill_id):
        found = [
            (k, e)
            for k, e in self.evidence.items()
            if k[1] == skill_id and e.direction == -1
        ]
        if not found:
            return None
        (eid, skill, ordinal), ev = max(found, key=lambda item: item[0])
        return EvidenceOut(
            evidence_id=evidence_id(eid, skill, ordinal),
            event_id=eid,
            ordinal=ordinal,
            skill_id=skill,
            kind=ev.kind,
            tier=ev.tier,
            source=ev.source,
            weight=ev.weight,
            direction=ev.direction,
            observed_at=ev.observed_at,
            summary=ev.summary,
            instance_id=None,
            message_id=None,
        )

    async def add_root_cause(self, _driver, ev_id, root_skill_id, confidence, source):
        key = (ev_id, root_skill_id)
        created = key not in self.roots
        self.roots.add(key)
        return created

    def install(self, monkeypatch, module) -> None:
        for name in (
            "get_state",
            "get_misc_states",
            "list_evidence_keys_for_event",
            "apply_chat_observation_tx",
            "latest_incorrect_evidence",
            "add_root_cause",
        ):
            monkeypatch.setattr(module.personal_q, name, getattr(self, name))
        for name in (
            "get_prerequisites",
            "list_misconceptions_for_skill",
            "create_personal_misconception",
        ):
            monkeypatch.setattr(module.canonical_q, name, getattr(self, name))


def mock(value: Any = None) -> AsyncMock:
    return AsyncMock(return_value=value)
