"""apply.profile_updated — 20-B1-phase2.md §7."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.apply.profile_updated import apply_profile_updated
from app.events.dispatch import RuleDeps
from app.schemas.events import Event, EventType

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


def _event(*, field: str, event_type: EventType = EventType.profile_updated) -> Event:
    return Event(
        id=1,
        type=event_type,
        payload={"field": field, "value": 10, "by": "user"},
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


# --- tests ---


async def test_ignores_non_key_field(monkeypatch):
    calls = []

    async def fake_rebuild(session, deps, student_id, exam_id):
        calls.append(exam_id)

    monkeypatch.setattr("app.apply.profile_updated.rebuild_sets", fake_rebuild)

    # traits.summary не в списке ключевых
    await apply_profile_updated(None, _event(field="traits.summary"), _deps())
    assert calls == []


async def test_rebuilds_both_exams_on_hours_per_week(monkeypatch):
    calls = []

    async def fake_rebuild(session, deps, student_id, exam_id):
        calls.append(exam_id)

    monkeypatch.setattr("app.apply.profile_updated.rebuild_sets", fake_rebuild)

    await apply_profile_updated(None, _event(field="pace.hours_per_week"), _deps())
    assert set(calls) == {"SAT_MATH", "ENT_MATH"}


async def test_rebuilds_on_sat_date(monkeypatch):
    calls = []

    async def fake_rebuild(session, deps, student_id, exam_id):
        calls.append(exam_id)

    monkeypatch.setattr("app.apply.profile_updated.rebuild_sets", fake_rebuild)

    await apply_profile_updated(None, _event(field="academics.sat_date"), _deps())
    assert len(calls) == 2


async def test_ignores_wrong_event_type(monkeypatch):
    calls = []

    async def fake_rebuild(session, deps, student_id, exam_id):
        calls.append(exam_id)

    monkeypatch.setattr("app.apply.profile_updated.rebuild_sets", fake_rebuild)

    ev = _event(field="pace.hours_per_week", event_type=EventType.task_answered)
    await apply_profile_updated(None, ev, _deps())
    assert calls == []


async def test_does_not_crash_if_rebuild_raises(monkeypatch):
    async def failing_rebuild(session, deps, student_id, exam_id):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.apply.profile_updated.rebuild_sets", failing_rebuild)

    # не должно бросить
    await apply_profile_updated(None, _event(field="pace.hours_per_week"), _deps())
