"""`GET /texts` and the four statuses of §3.5 — §13.3 `test_api_texts.py`."""

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api import texts as texts_api
from app.config import KnowledgeParams
from app.events.dispatch import RuleDeps
from app.events.outbox import JobOutbox
from app.main import create_app
from app.schemas.auth import StudentCtx
from app.schemas.sets import SetOut, SetProgress, TopicOut
from app.schemas.texts import GeneratedText

pytestmark = pytest.mark.phase4

CLOCK = datetime(2026, 9, 19, 12, tzinfo=UTC)
SKILL = "alg.linear"


class _Session:
    async def commit(self):
        pass

    async def flush(self):
        pass


class _Redis:
    """Loop-agnostic stand-in: TestClient runs its own event loop, and a
    real async client bound to the test's loop cannot be shared with it."""

    def __init__(self, values: dict | None = None) -> None:
        self.values = dict(values or {})

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, **_kwargs):
        self.values[key] = value
        return True

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)


def _set(set_id) -> SetOut:
    return SetOut(
        id=set_id,
        exam_id="SAT_MATH",
        area_ids=["algebra"],
        status="current",
        kind="regular",
        position=0,
        deadline=date(2026, 10, 1),
        reason="по модели знаний",
        topics=[
            TopicOut(
                skill_id=SKILL,
                name="Линейные уравнения",
                kind="topic",
                position=0,
                status="open",
                level="shaky",
                is_root=False,
                misconception_labels=[],
                subtitle=None,
            )
        ],
        progress=SetProgress(
            topics_closed=0, topics_total=1, tasks_answered=0, tasks_correct=0
        ),
    )


def _row(status: str, text: str | None, digest: str = "hash-now") -> GeneratedText:
    return GeneratedText(
        id=uuid4(),
        kind="guideline",
        input_hash=digest,
        text=text,
        model="model",
        prompt_version="guideline_v1",
        created_at=CLOCK,
        subject=SKILL,
        status=status,
    )


@pytest.fixture
def transport(monkeypatch):
    student = StudentCtx(student_id=uuid4(), email="s@example.com")
    set_id = uuid4()
    outbox = JobOutbox()
    rule_deps = RuleDeps(
        graph=None,
        redis=_Redis(),
        params=KnowledgeParams(),
        now=lambda: CLOCK,
        jobs=outbox,
    )
    app = create_app()

    async def session_override():
        yield _Session()

    async def noop():
        yield None

    app.dependency_overrides[deps.get_session] = session_override
    app.dependency_overrides[deps.get_current_student] = lambda: student
    app.dependency_overrides[deps.get_rule_deps] = lambda: rule_deps
    app.dependency_overrides[deps.flush_outbox] = noop

    async def get_set(_session, owner, requested):
        return (
            _set(set_id)
            if owner == student.student_id and requested == set_id
            else None
        )

    async def current_hash(*_args, **_kwargs):
        return "hash-now", SimpleNamespace()

    async def set_job_id(*_args, **_kwargs):
        return f"pregen:{set_id}:abc123"

    monkeypatch.setattr(texts_api.sets_repo, "get_set", get_set)
    monkeypatch.setattr(texts_api.apply_texts, "current_hash", current_hash)
    monkeypatch.setattr(texts_api.apply_texts, "set_job_id", set_job_id)
    return SimpleNamespace(
        app=app,
        student=student,
        set_id=set_id,
        outbox=outbox,
        monkeypatch=monkeypatch,
    )


def _patch_cache(transport, current, last):
    async def get_current(*_args, **_kwargs):
        return current, last

    transport.monkeypatch.setattr(texts_api.texts_repo, "get_current", get_current)


def _get(transport, kind="guideline"):
    with TestClient(transport.app) as client:
        return client.get(f"/texts/{transport.set_id}/{SKILL}?kind={kind}")


def test_a_ready_text_is_marked_as_generated(transport):
    _patch_cache(transport, _row("ready", "## Как готовиться\n…"), None)
    body = _get(transport).json()
    assert body["status"] == "ready"
    assert body["mark"] == "generated"
    assert body["prompt_version"] == "guideline_v1"
    assert body["input_hash"] == "hash-now"
    # Уже готово — переставлять задачу незачем.
    assert transport.outbox.entries == []


def test_a_changed_knowledge_model_shows_the_saved_version(transport):
    previous = _row("ready", "старый текст", digest="hash-old")
    _patch_cache(transport, None, previous)
    body = _get(transport).json()
    assert body["status"] == "stale"
    assert body["mark"] == "saved_version"
    assert body["text"] == "старый текст"
    # И ставит регенерацию — но только потому, что задачи нет (§3.6).
    [entry] = transport.outbox.entries
    assert entry.fn_name == "pregenerate_set"


def test_a_generating_row_reports_progress_without_a_text(transport):
    _patch_cache(transport, _row("generating", None), None)
    body = _get(transport).json()
    assert body["status"] == "generating"
    assert body["text"] is None
    assert transport.outbox.entries == []


def test_a_failed_row_explains_itself(transport):
    row = _row("failed", None)
    row.error = "invalid_output"
    _patch_cache(transport, row, None)
    body = _get(transport).json()
    assert body["status"] == "failed"
    assert body["reason"] == "invalid_output"


def test_nothing_in_cache_queues_the_pre_generation(transport):
    _patch_cache(transport, None, None)
    body = _get(transport).json()
    assert body["status"] == "generating"
    assert body["reason"] == "not_generated"
    [entry] = transport.outbox.entries
    assert entry.fn_name == "pregenerate_set"
    assert entry.job_id.startswith(f"pregen:{transport.set_id}:")


def test_a_live_job_stops_the_route_from_queueing_another(transport):
    """`keys.text_job` живёт 600 с: пока задача жива, роутер не дублирует
    её, а после TTL считает потерянной и ставит заново (§16.3)."""
    from app import keys

    _patch_cache(transport, None, None)
    rule_deps = transport.app.dependency_overrides[deps.get_rule_deps]()
    rule_deps.redis.values[keys.text_job("guideline", "hash-now")] = "job-1"
    with TestClient(transport.app) as client:
        assert client.get(f"/texts/{transport.set_id}/{SKILL}").status_code == 200
    assert transport.outbox.entries == []


def test_a_foreign_set_is_not_found(transport):
    with TestClient(transport.app) as client:
        assert client.get(f"/texts/{uuid4()}/{SKILL}").status_code == 404


def test_an_unknown_topic_is_not_found(transport):
    _patch_cache(transport, None, None)
    with TestClient(transport.app) as client:
        response = client.get(f"/texts/{transport.set_id}/other.skill")
    assert response.status_code == 404


def test_an_invalid_kind_is_rejected(transport):
    _patch_cache(transport, None, None)
    with TestClient(transport.app) as client:
        assert (
            client.get(f"/texts/{transport.set_id}/{SKILL}?kind=realism").status_code
            == 400
        )


def test_opened_writes_the_event_with_the_text_hash(transport):
    events: list = []

    async def append(_session, _redis, event_in, *args, **kwargs):
        events.append(event_in)
        return SimpleNamespace(
            id=1,
            type=event_in.type,
            payload=event_in.payload,
            student_id=event_in.student_id,
        )

    async def dispatch(*_args):
        return {}

    transport.monkeypatch.setattr(texts_api.store, "append", append)
    transport.monkeypatch.setattr(texts_api.dispatch, "dispatch", dispatch)
    with TestClient(transport.app) as client:
        response = client.post(
            f"/texts/{transport.set_id}/{SKILL}/opened", json={"kind": "guideline"}
        )
    assert response.status_code == 204
    assert events[0].type.value == "guideline.opened"
    assert events[0].payload["text_hash"] == "hash-now"
    assert events[0].topic_skill_id == SKILL


def test_regenerate_clears_the_attempt_guard_and_queues(transport):
    reset: list = []

    async def reset_attempts(_session, kind, digest):
        reset.append((kind, digest))

    transport.monkeypatch.setattr(
        texts_api.texts_repo, "reset_attempts", reset_attempts
    )
    with TestClient(transport.app) as client:
        response = client.post(f"/texts/{transport.set_id}/{SKILL}/regenerate")
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert {kind for kind, _ in reset} == {"guideline", "explanation"}
    assert transport.outbox.entries[0].fn_name == "pregenerate_set"
