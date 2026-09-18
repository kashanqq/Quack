"""apply.sets — set rebuild and wrappers.

Unit tests with monkeypatched repos and a None graph.
Integration cases live behind @pytest.mark.integration and skip without
a live Postgres + Neo4j.

Source: 20-B1-phase2.md §8.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.apply.sets import (
    on_program_change,
    on_run_completed,
    on_set_change,
    open_set,
    rebuild_sets,
)
from app.errors import NotFound
from app.events.dispatch import RuleDeps
from app.schemas.events import Event, EventType
from app.schemas.sets import SetOut, SetsByExam

pytestmark = pytest.mark.phase1

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(
        self, key: str, value: str, *, ex: int | None = None, nx: bool = False
    ):
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def incr(self, key: str) -> int:
        v = int(self.store.get(key, "0")) + 1
        self.store[key] = str(v)
        return v

    async def get(self, key: str) -> str | None:
        return self.store.get(key)


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


def _set_out(
    set_id,
    *,
    exam_id: str = "SAT_MATH",
    status: str = "upcoming",
) -> SetOut:
    return SetOut(
        id=set_id,
        exam_id=exam_id,  # type: ignore[arg-type]
        area_ids=[],
        status=status,  # type: ignore[arg-type]
        kind="regular",
        position=0,
        deadline=date(2026, 10, 1),
        reason="...",
        topics=[],
        progress=__import__("app.schemas.sets", fromlist=["SetProgress"]).SetProgress(
            topics_closed=0, topics_total=0, tasks_answered=0, tasks_correct=0
        ),
    )


def _event(type_: EventType, *, exam_id: str | None = None) -> Event:
    return Event(
        id=1,
        type=type_,
        payload={},
        student_id=uuid4(),
        session_id=None,
        exam_id=exam_id,  # type: ignore[arg-type]
        set_id=None,
        topic_skill_id=None,
        chat_id=None,
        occurred_at=NOW,
        extractor_version=None,
        source_event_ids=None,
        ingested_at=NOW,
        processed_at=None,
    )


# --- rebuild_sets with graph=None ---


async def test_rebuild_sets_graph_none_returns_empty(monkeypatch):
    sid = uuid4()

    async def fake_list_sets(session, student_id, exam_id):
        return []

    from app.db.repo import forecast as forecast_repo

    async def fake_forecast_get(session, student_id, exam_id):
        return None

    monkeypatch.setattr("app.apply.sets.sets_repo.list_sets", fake_list_sets)
    monkeypatch.setattr("app.apply.sets.forecast_repo.get", fake_forecast_get)
    _ = forecast_repo

    deps = _deps(graph=None)
    result = await rebuild_sets(None, deps, sid, "SAT_MATH")

    assert isinstance(result, SetsByExam)
    assert result.exam_id == "SAT_MATH"
    assert result.current is None
    assert result.upcoming == []
    assert result.done == []


# --- open_set ---


async def test_open_set_not_found(monkeypatch):
    async def fake_get_set(session, student_id, set_id):
        return None

    monkeypatch.setattr("app.apply.sets.sets_repo.get_set", fake_get_set)

    with pytest.raises(NotFound):
        await open_set(None, _deps(), uuid4(), uuid4())


async def test_open_set_demotes_previous_current(monkeypatch):
    sid = uuid4()
    target = uuid4()
    other = uuid4()

    # get_set возвращает target
    async def fake_get_set(session, student_id, set_id):
        return _set_out(set_id, status="current")

    # list_sets возвращает [other(current), target(upcoming)]
    async def fake_list_sets(session, student_id, exam_id):
        return [
            _set_out(other, status="current"),
            _set_out(target, status="upcoming"),
        ]

    status_calls: list = []

    async def fake_set_status(session, student_id, set_id, status):
        status_calls.append((set_id, status))

    monkeypatch.setattr("app.apply.sets.sets_repo.get_set", fake_get_set)
    monkeypatch.setattr("app.apply.sets.sets_repo.list_sets", fake_list_sets)
    monkeypatch.setattr("app.apply.sets.sets_repo.set_status", fake_set_status)

    await open_set(None, _deps(), sid, target)

    assert (other, "upcoming") in status_calls
    assert (target, "current") in status_calls


# --- wrappers: on_program_change ---


async def test_on_program_change_rebuilds_both_exams(monkeypatch):
    sid = uuid4()
    rebuilt: list[str] = []

    async def fake_rebuild(session, deps, student_id, exam_id):
        rebuilt.append(exam_id)
        return await _empty(session, student_id, exam_id)

    async def _empty(session, student_id, exam_id):
        return SetsByExam(
            exam_id=exam_id,
            forecast=None,
            current=None,
            upcoming=[],
            done=[],
        )

    monkeypatch.setattr("app.apply.sets.rebuild_sets", fake_rebuild)

    event = _event(EventType.program_saved)
    event.student_id = sid
    await on_program_change(None, event, _deps())

    assert set(rebuilt) == {"SAT_MATH", "ENT_MATH"}


async def test_on_program_change_ignores_other_types(monkeypatch):
    called = []

    async def fake_rebuild(*args, **kwargs):
        called.append(True)

    monkeypatch.setattr("app.apply.sets.rebuild_sets", fake_rebuild)
    await on_program_change(None, _event(EventType.task_answered), _deps())
    assert called == []


# --- wrappers: on_set_change ---


async def test_on_set_change_uses_event_exam(monkeypatch):
    calls = []

    async def fake_rebuild(session, deps, student_id, exam_id):
        calls.append(exam_id)

    monkeypatch.setattr("app.apply.sets.rebuild_sets", fake_rebuild)

    await on_set_change(
        None, _event(EventType.set_switched_by_user, exam_id="ENT_MATH"), _deps()
    )
    assert calls == ["ENT_MATH"]


# --- wrappers: on_run_completed ---


async def test_on_run_completed_uses_event_exam(monkeypatch):
    calls = []

    async def fake_rebuild(session, deps, student_id, exam_id):
        calls.append(exam_id)

    monkeypatch.setattr("app.apply.sets.rebuild_sets", fake_rebuild)

    await on_run_completed(
        None, _event(EventType.mock_completed, exam_id="ENT_MATH"), _deps()
    )
    assert calls == ["ENT_MATH"]
