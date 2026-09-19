"""In-memory event store and ARQ context for job tests (phase3 §6.8, §6.10)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

from app.schemas.events import Event, EventIn, EventType
from app.schemas.sets import SetOut, SetProgress

NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)


class MemoryStore:
    """Just enough of `app.events.store` for the jobs."""

    def __init__(self) -> None:
        self.events: list[Event] = []
        self.appended: list[EventIn] = []
        self.processed: list[int] = []
        self._next = 1000

    def add(
        self, type_: EventType, *, chat_id=None, payload=None, processed=False, **kw
    ):
        self._next += 1
        event = Event(
            id=self._next,
            type=type_,
            payload=payload or {},
            student_id=kw.pop("student_id", uuid4()),
            chat_id=chat_id,
            occurred_at=NOW + timedelta(seconds=self._next - 1000),
            ingested_at=NOW,
            processed_at=NOW if processed else None,
            session_id=kw.pop("session_id", None),
            **kw,
        )
        self.events.append(event)
        return event

    async def list_unprocessed(self, _session, chat_id, limit=50, types=None):
        out = [
            e
            for e in self.events
            if e.chat_id == chat_id
            and e.processed_at is None
            and (types is None or e.type in types)
        ]
        return sorted(out, key=lambda e: e.id)[:limit]

    async def count_unprocessed(self, session, chat_id, types=None):
        return len(await self.list_unprocessed(session, chat_id, 10_000, types))

    async def mark_processed(self, _session, ids):
        self.processed.extend(ids)
        for event in self.events:
            if event.id in ids:
                event.processed_at = NOW

    async def append(
        self, _session, _redis, ev: EventIn, deps=None, *, dispatch_event=True
    ):
        self.appended.append(ev)
        return self.add(
            ev.type,
            chat_id=ev.chat_id,
            payload=ev.payload,
            student_id=ev.student_id,
            set_id=ev.set_id,
            exam_id=ev.exam_id,
            topic_skill_id=ev.topic_skill_id,
            extractor_version=ev.extractor_version,
            source_event_ids=ev.source_event_ids,
        )

    async def get_event(self, _session, _student_id, event_id):
        return next((e for e in self.events if e.id == event_id), None)

    async def list_by_type(
        self,
        _s,
        _sid,
        types,
        since,
        limit,
        *,
        chat_id=None,
        after_id=None,
        session_id=None,
    ):
        return [
            e
            for e in self.events
            if e.type in types and (after_id is None or e.id > after_id)
        ][:limit]

    def of(self, type_: EventType) -> list[EventIn]:
        return [e for e in self.appended if e.type == type_]


def set_out(set_id: UUID, skill_id: str = "math.alg.abs_value_eq") -> SetOut:
    return SetOut(
        id=set_id,
        exam_id="SAT_MATH",
        area_ids=["alg"],
        status="current",
        kind="regular",
        position=1,
        deadline=NOW.date() + timedelta(days=10),
        reason="",
        topics=[],
        progress=SetProgress(
            topics_closed=0, topics_total=0, tasks_answered=0, tasks_correct=0
        ),
    )


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def commit(self):
        return None


def arq_ctx(
    llm, redis, *, graph: Any = "graph", job_try: int = 1, embedder=None
) -> dict:
    return {
        "sessionmaker": FakeSession,
        "redis": redis,
        "neo4j": object() if graph == "graph" else graph,
        "llm": llm,
        "job_try": job_try,
        "job_id": "job-1",
        "embedder": embedder,
    }


def patch_store(monkeypatch, module, memory: MemoryStore) -> None:
    for name in (
        "list_unprocessed",
        "count_unprocessed",
        "mark_processed",
        "append",
        "get_event",
        "list_by_type",
    ):
        monkeypatch.setattr(module.store, name, getattr(memory, name))


def no_messages_repo(monkeypatch, module) -> None:
    monkeypatch.setattr(
        module.messages_repo, "list_by_event_ids", AsyncMock(return_value={})
    )


def ns(**kw) -> SimpleNamespace:
    return SimpleNamespace(**kw)
