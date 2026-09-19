"""Quack, texts and program-search transport — §13.3."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.config import KnowledgeParams
from app.events.dispatch import RuleDeps
from app.events.outbox import JobOutbox
from app.main import create_app
from app.schemas.auth import StudentCtx
from app.schemas.profile import Profile
from app.schemas.quack import (
    ActivityOut,
    PaceOut,
    RecommendationAction,
    RecommendationOut,
)

pytestmark = pytest.mark.phase4

CLOCK = datetime(2026, 9, 19, 12, tzinfo=UTC)


class _Session:
    """Everything these routes read is monkeypatched; the session only has
    to exist and to commit."""

    def __init__(self) -> None:
        self.added: list = []

    async def commit(self):
        pass

    async def flush(self):
        pass

    def add(self, row):
        # Фаза 5: маршрут пишет намерение задачи в ту же транзакцию (§9.2).
        row.id = len(self.added) + 1
        self.added.append(row)

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def scalar(self, *args, **kwargs):
        return None

    async def scalars(self, *args, **kwargs):
        return SimpleNamespace(all=lambda: [])

    async def get(self, *args, **kwargs):
        return None


def _recommendation(**overrides) -> RecommendationOut:
    base = {
        "id": uuid4(),
        "kind": "pace_variant",
        "urgency": "urgent",
        "position": 0,
        "status": "pending",
        "title": "SAT: добавить часы",
        "reason": "готовность позже теста",
        "action_text": "6 ч/нед → готов 3 ноября",
        "action": RecommendationAction(
            kind="profile_update", profile_path="pace.hours_per_week", profile_value=6
        ),
        "reason_hash": "hash-1",
        "created_at": CLOCK,
    }
    return RecommendationOut(**{**base, **overrides})


@pytest.fixture
def transport(monkeypatch):
    student = StudentCtx(student_id=uuid4(), email="s@example.com")
    session = _Session()
    redis = fakeredis.aioredis.FakeRedis()
    outbox = JobOutbox()
    rule_deps = RuleDeps(
        graph=None,
        redis=redis,
        params=KnowledgeParams(),
        now=lambda: CLOCK,
        jobs=outbox,
    )
    app = create_app()

    async def session_override():
        yield session

    async def noop():
        yield None

    app.dependency_overrides[deps.get_session] = session_override
    app.dependency_overrides[deps.get_current_student] = lambda: student
    app.dependency_overrides[deps.get_rule_deps] = lambda: rule_deps
    # Флаш идёт по настоящему пути в одном тесте ниже; здесь он мешал бы
    # читать накопленный outbox после ответа.
    app.dependency_overrides[deps.flush_outbox] = noop

    from app.api import quack as quack_api

    async def profile(*_args):
        return Profile(student_id=student.student_id)

    monkeypatch.setattr(quack_api.profiles_repo, "get_profile", profile)
    return SimpleNamespace(
        app=app,
        student=student,
        deps=rule_deps,
        outbox=outbox,
        redis=redis,
        monkeypatch=monkeypatch,
    )


def _patch_quack(transport, *, items=None, pace=None, activity=None):
    from app.api import quack as quack_api

    async def compute_all(*_args):
        return pace or PaceOut(exams=[], as_of=CLOCK)

    async def list_open(*_args, **_kwargs):
        return list(items or [])

    async def activity_out(*_args, **_kwargs):
        return activity or ActivityOut(
            days=[], window_days=14, active_days=0, tz="Asia/Almaty"
        )

    transport.monkeypatch.setattr(quack_api.apply_pace, "compute_all", compute_all)
    transport.monkeypatch.setattr(quack_api.recs_repo, "list_open", list_open)
    transport.monkeypatch.setattr(quack_api.aggregates_repo, "activity", activity_out)


# --- GET /quack ---


def test_quack_assembles_pace_feed_and_activity(transport):
    item = _recommendation()
    _patch_quack(transport, items=[item])
    with TestClient(transport.app) as client:
        body = client.get("/quack").json()
    assert body["items"][0]["title"] == item.title
    assert body["items"][0]["action"]["profile_path"] == "pace.hours_per_week"
    assert body["activity"]["tz"] == "Asia/Almaty"
    # Есть непоказанные — фронт «крякает».
    assert body["new_batch"] is True and body["n_new"] == 1


def test_quack_is_quiet_when_everything_has_been_seen(transport):
    _patch_quack(transport, items=[_recommendation(status="shown")])
    with TestClient(transport.app) as client:
        body = client.get("/quack").json()
    assert body["new_batch"] is False and body["n_new"] == 0


def test_activity_window_is_capped(transport):
    _patch_quack(transport)
    with TestClient(transport.app) as client:
        assert client.get("/quack/activity?days=100").status_code == 400
        assert client.get("/quack/activity?days=14").status_code == 200


# --- seen ---


def test_seen_marks_shown_and_refreshes_the_aggregates(transport):
    from app.api import quack as quack_api

    marked = []

    async def mark_shown(_session, student_id, ids, *, now):
        marked.append((student_id, ids))
        return 2

    transport.monkeypatch.setattr(quack_api.recs_repo, "mark_shown", mark_shown)
    with TestClient(transport.app) as client:
        body = client.post("/quack/seen", json={"recommendation_ids": None}).json()
    assert body == {"shown": 2}
    assert marked[0][1] is None
    # Открытие Quack событием не считается — только задача агрегатов (§8.5).
    [entry] = transport.outbox.entries
    assert entry.fn_name == "daily_aggregates"
    assert entry.job_id.startswith(f"aggr:{transport.student.student_id}:")


# --- accept / decline ---


def test_accept_dispatches_and_returns_the_updated_row(transport):
    from app.api import quack as quack_api

    item = _recommendation()
    accepted = item.model_copy(update={"status": "accepted", "decided_at": CLOCK})
    events: list = []

    async def get(_session, _student_id, _rec_id):
        return item

    async def append(_session, _redis, event_in, *args, **kwargs):
        events.append(event_in)
        return SimpleNamespace(
            id=1,
            type=event_in.type,
            payload=event_in.payload,
            student_id=event_in.student_id,
        )

    async def dispatch(_session, _event, _deps):
        return {"apply_accept": accepted}

    transport.monkeypatch.setattr(quack_api.recs_repo, "get", get)
    transport.monkeypatch.setattr(quack_api.store, "append", append)
    transport.monkeypatch.setattr(quack_api.dispatch, "dispatch", dispatch)

    with TestClient(transport.app) as client:
        response = client.post(f"/quack/{item.id}/accept")
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    # Правила могли пересобрать сеты (§8.5).
    assert "X-Knowledge-Version" in response.headers
    assert [event.type.value for event in events] == ["recommendation.accepted"]
    assert events[0].payload["reason_hash"] == item.reason_hash


def test_accepting_twice_writes_no_second_event(transport):
    from app.api import quack as quack_api

    item = _recommendation(status="accepted")
    events: list = []

    async def get(_session, _student, _rec_id):
        return item

    async def append(*_args, **_kwargs):
        events.append(1)

    transport.monkeypatch.setattr(quack_api.recs_repo, "get", get)
    transport.monkeypatch.setattr(quack_api.store, "append", append)
    with TestClient(transport.app) as client:
        response = client.post(f"/quack/{item.id}/accept")
    assert response.status_code == 200
    assert events == []


def test_an_unknown_recommendation_is_not_found(transport):
    from app.api import quack as quack_api

    async def get(*_args):
        return None

    transport.monkeypatch.setattr(quack_api.recs_repo, "get", get)
    with TestClient(transport.app) as client:
        assert client.post(f"/quack/{uuid4()}/accept").status_code == 404
        assert (
            client.post(f"/quack/{uuid4()}/decline", json={"reason": None}).status_code
            == 404
        )


def test_decline_after_accept_is_a_conflict(transport):
    from app.api import quack as quack_api
    from app.errors import Conflict

    item = _recommendation(status="accepted")

    async def get(*_args):
        return item

    async def append(_session, _redis, event_in, *args, **kwargs):
        return SimpleNamespace(id=1, type=event_in.type, payload=event_in.payload)

    async def dispatch(*_args):
        raise Conflict("recommendation already decided")

    transport.monkeypatch.setattr(quack_api.recs_repo, "get", get)
    transport.monkeypatch.setattr(quack_api.store, "append", append)
    transport.monkeypatch.setattr(quack_api.dispatch, "dispatch", dispatch)
    with TestClient(transport.app) as client:
        response = client.post(f"/quack/{item.id}/decline", json={"reason": "нет"})
    assert response.status_code == 409


# --- program search and flag ---


def test_search_returns_202_with_a_query_derived_id(transport):
    with TestClient(transport.app) as client:
        first = client.post("/programs/search", json={"query": "math in Spain"})
        second = client.post("/programs/search", json={"query": "  MATH IN spain "})
    assert first.status_code == 202
    assert first.json()["status"] == "queued"
    # Тот же вопрос от двух учеников — одна задача и один расход бюджета.
    assert first.json()["search_id"] == second.json()["search_id"]
    entry = transport.outbox.entries[0]
    assert entry.fn_name == "search_programs"
    assert entry.job_id == first.json()["search_id"]


def test_a_short_query_is_rejected(transport):
    with TestClient(transport.app) as client:
        assert client.post("/programs/search", json={"query": "a"}).status_code == 400


def test_search_status_defaults_to_queued(transport):
    with TestClient(transport.app) as client:
        body = client.get("/programs/search/search:unknown").json()
    assert body["status"] == "queued"
    assert body["found"] == [] and body["rejected"] == 0


def test_flagging_a_curated_program_is_refused(transport):
    from app.api import programs as programs_api
    from app.errors import Conflict
    from tests.quack.conftest import make_program

    async def flag(_session, program_id, reason):
        if program_id == "floor":
            raise Conflict("curated program cannot be flagged")
        return make_program(1, flagged=True, extracted_auto=True)

    transport.monkeypatch.setattr(programs_api.program_repo, "flag", flag)
    with TestClient(transport.app) as client:
        assert (
            client.post("/programs/floor/flag", json={"reason": "неверно"}).status_code
            == 409
        )
        ok = client.post("/programs/auto/flag", json={"reason": "неверно"})
    assert ok.status_code == 200
    assert ok.json()["flagged"] is True


def test_the_outbox_is_flushed_only_after_the_response():
    """Задача ставится после коммита — иначе воркер прочитает БД раньше,
    чем в ней появится событие (§1.4). Здесь работает настоящая связка
    `get_rule_deps` → `flush_outbox`, без подмен."""
    student = StudentCtx(student_id=uuid4(), email="s@example.com")
    app = create_app()
    enqueued: list = []

    class _Arq:
        async def enqueue_job(self, fn_name, **kwargs):
            enqueued.append((fn_name, kwargs))
            return SimpleNamespace(job_id=kwargs.get("_job_id"))

    async def session_override():
        yield _Session()

    app.dependency_overrides[deps.get_session] = session_override
    app.dependency_overrides[deps.get_current_student] = lambda: student

    with TestClient(app) as client:
        client.app.state.arq = _Arq()
        # Тест не должен трогать настоящую базу: `_drain` берёт sessionmaker
        # приложения, а с ним в `job_outbox` оседали бы строки прогонов.
        client.app.state.sessionmaker = _Session
        response = client.post("/programs/search", json={"query": "math in Spain"})
    assert response.status_code == 202
    [(fn_name, kwargs)] = enqueued
    assert fn_name == "search_programs"
    assert kwargs["_job_id"] == response.json()["search_id"]
    assert kwargs["_queue_name"] == "bulk"


def test_compare_hash_is_stable_for_the_same_selection():
    from app.apply.matching import compare_hash

    profile = Profile(student_id=uuid4())
    rows = [
        SimpleNamespace(
            param="стоимость",
            values={"a": "1", "b": "2"},
            differs=True,
            relevant_to_student=True,
        ),
        SimpleNamespace(
            param="город",
            values={"a": "x", "b": "x"},
            differs=False,
            relevant_to_student=True,
        ),
    ]
    first = compare_hash(profile.student_id, ["b", "a"], rows, profile, "v1", "m")
    again = compare_hash(profile.student_id, ["a", "b"], rows, profile, "v1", "m")
    assert first == again
    assert first != compare_hash(
        profile.student_id, ["a", "b"], rows, profile, "v2", "m"
    )


def test_realism_hash_ignores_the_soft_factor():
    from app.apply.matching import realism_hash
    from app.schemas.matching import FactorOut, MatchOut
    from tests.quack.conftest import make_program

    def _match(factors):
        return MatchOut(
            program=make_program(1),
            realism="try",
            factors=factors,
            assumptions=[],
            score=1.0,
            fits_text=None,
            soft_pending=False,
        )

    hard = FactorOut(
        id="exam_score",
        kind="hard",
        status="below",
        text="нужно 1400",
        source=None,
        weight=3.0,
    )
    soft = FactorOut(
        id="soft:environment",
        kind="soft",
        status="in_range",
        text="тепло",
        source=None,
        weight=2.0,
    )
    student = uuid4()
    assert realism_hash(student, _match([hard]), "v", "m") == realism_hash(
        student, _match([hard, soft]), "v", "m"
    )
