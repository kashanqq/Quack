"""T01–T04, T17: how the API answers while a dependency is down (§10, §11)."""

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

pytestmark = pytest.mark.phase5

CLOCK = datetime(2026, 9, 19, 12, tzinfo=UTC)
SKILL = "alg.linear"


class _Session:
    async def commit(self):
        pass

    async def flush(self):
        pass


class _Redis:
    def __init__(self) -> None:
        self.values: dict = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, **_kwargs):
        self.values[key] = value
        return True

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)


class _LLM:
    def __init__(self, status: str) -> None:
        self._status = status

    async def status(self):
        return self._status


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


def _row(status: str, text: str | None, digest: str = "hash-now", student_id=None):
    return GeneratedText(
        id=uuid4(),
        kind="guideline",
        input_hash=digest,
        text=text,
        model="model",
        prompt_version="guideline_v1",
        created_at=CLOCK,
        subject=SKILL,
        status=status,  # type: ignore[arg-type]
        student_id=student_id,
    )


@pytest.fixture
def transport(monkeypatch):
    student = StudentCtx(student_id=uuid4(), email="s@example.com")
    set_id = uuid4()
    outbox = JobOutbox()
    state = SimpleNamespace(llm_status="ok", hash="hash-now")
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
    app.dependency_overrides[deps.get_llm] = lambda: _LLM(state.llm_status)

    async def get_set(_session, owner, requested):
        return (
            _set(set_id)
            if owner == student.student_id and requested == set_id
            else None
        )

    async def current_hash(*_args, **_kwargs):
        return state.hash, SimpleNamespace()

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
        state=state,
        monkeypatch=monkeypatch,
    )


def _patch_cache(transport, current, last):
    async def get_current(*_args, **_kwargs):
        return current, last

    transport.monkeypatch.setattr(texts_api.texts_repo, "get_current", get_current)


def _get(transport, kind="guideline"):
    with TestClient(transport.app) as client:
        return client.get(f"/texts/{transport.set_id}/{SKILL}?kind={kind}")


def test_t01_the_same_text_comes_back_marked_saved_while_the_model_is_down(transport):
    _patch_cache(transport, _row("ready", "## Как готовиться\n…"), None)
    live = _get(transport).json()
    assert (live["status"], live["mark"]) == ("ready", "generated")

    transport.state.llm_status = "down"
    down = _get(transport).json()
    assert down["status"] == "ready"
    assert down["mark"] == "saved_version"
    assert down["text"] == live["text"]
    assert down["reason"] == "llm_unavailable"


def test_t02_the_stale_lookup_is_scoped_to_the_owner(transport):
    """Чужой last_ready не возвращается: владение проверено до поиска."""
    called: list = []

    async def get_current(_session, owner, kind, subject, digest):
        called.append(owner)
        return None, None

    transport.monkeypatch.setattr(texts_api.texts_repo, "get_current", get_current)
    body = _get(transport).json()
    assert called == [transport.student.student_id]
    assert body["text"] is None


def test_an_explanation_is_looked_up_as_a_shared_text(transport):
    """§3.1: объяснение общее, гайдлайн — личный. Область не расширяется."""
    called: list = []

    async def get_current(_session, owner, kind, subject, digest):
        called.append((owner, kind))
        return None, None

    transport.monkeypatch.setattr(texts_api.texts_repo, "get_current", get_current)
    _get(transport, kind="explanation")
    assert called == [(None, "explanation")]


def test_a_graph_outage_gives_no_hash_and_no_text(transport):
    async def current_hash(*_args, **_kwargs):
        return None, None

    transport.monkeypatch.setattr(texts_api.apply_texts, "current_hash", current_hash)
    _patch_cache(transport, _row("ready", "тело"), None)
    body = _get(transport).json()
    assert body["status"] == "generating"
    assert body["text"] is None
    assert body["reason"] == "graph_unavailable"
    # И задачу не ставим: под каким хэшем её ставить — неизвестно.
    assert transport.outbox.entries == []


def test_someone_elses_set_is_not_found(transport):
    with TestClient(transport.app) as client:
        response = client.get(f"/texts/{uuid4()}/{SKILL}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
