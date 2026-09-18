"""apply.dispute — 20-B1-phase2.md §7."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.apply.dispute import apply_dispute
from app.events.dispatch import RuleDeps
from app.schemas.events import Event, EventType
from app.schemas.knowledge import MisconceptionStateOut

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


def _event(
    *,
    event_type: EventType,
    misconception_id: str = "lib.abs_single_branch",
) -> Event:
    return Event(
        id=1,
        type=event_type,
        payload={"misconception_id": misconception_id},
        student_id=uuid4(),
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


def _state(*, status: str = "confirmed") -> MisconceptionStateOut:
    return MisconceptionStateOut(
        misconception_id="lib.abs_single_branch",
        name="Раскрытие модуля только в одной ветви",
        status=status,  # type: ignore[arg-type]
        occurrence_count=3,
        strong_count=1,
        consecutive_avoided=0,
        triggers={},
        first_seen_at=NOW,
        updated_at=NOW,
        skill_ids=["math.alg.abs_value_eq"],
    )


# --- tests ---


async def test_dispute_graph_none_raises():
    ev = _event(event_type=EventType.misconception_disputed)
    with pytest.raises(RuntimeError):
        await apply_dispute(None, ev, _deps(graph=None))


async def test_dispute_wrong_event_type_raises():
    ev = _event(event_type=EventType.task_answered)
    with pytest.raises(ValueError):
        await apply_dispute(None, ev, _deps(graph=object()))


async def test_dispute_missing_payload_id_raises():
    ev = Event(
        id=1,
        type=EventType.misconception_disputed,
        payload={},
        student_id=uuid4(),
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
    with pytest.raises(ValueError):
        await apply_dispute(None, ev, _deps(graph=object()))


async def test_dispute_not_found_raises(monkeypatch):
    async def fake_list(driver, exam_id):
        return []

    async def fake_states(driver, student_id, skill_ids):
        return []

    monkeypatch.setattr("app.apply.dispute.canonical_q.list_exam_skills", fake_list)
    monkeypatch.setattr("app.apply.dispute.personal_q.get_misc_states", fake_states)

    ev = _event(event_type=EventType.misconception_disputed)
    with pytest.raises(ValueError):
        await apply_dispute(None, ev, _deps(graph=object()))


async def test_dispute_flips_to_disputed(monkeypatch):
    sid = uuid4()
    existing = _state(status="confirmed")

    async def fake_list(driver, exam_id):
        from app.schemas.knowledge import SkillRef, SkillWeight

        return [
            SkillWeight(
                skill=SkillRef(
                    id="math.alg.abs_value_eq",
                    name="...",
                    description="...",
                    exam_ids=["SAT_MATH"],  # type: ignore[list-item]
                    effort_h=4.0,
                    base_half_life_h=None,
                ),
                area_id="area.sat.algebra",
                weight=3.0,
            )
        ]

    async def fake_states(driver, student_id, skill_ids):
        return [existing]

    captured = {}

    async def fake_upsert(
        driver, student_id, misconception_id, status, counters, triggers=None
    ):
        captured["status"] = status
        captured["misconception_id"] = misconception_id
        return existing.model_copy(update={"status": status})

    monkeypatch.setattr("app.apply.dispute.canonical_q.list_exam_skills", fake_list)
    monkeypatch.setattr("app.apply.dispute.personal_q.get_misc_states", fake_states)
    monkeypatch.setattr("app.apply.dispute.personal_q.upsert_misc_state", fake_upsert)

    ev = _event(event_type=EventType.misconception_disputed)
    ev.student_id = sid
    result = await apply_dispute(None, ev, _deps(graph=object()))

    assert captured["status"] == "disputed"
    assert captured["misconception_id"] == "lib.abs_single_branch"
    assert result.status == "disputed"
