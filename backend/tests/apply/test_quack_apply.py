"""Accepting, declining and batching — §13.1 `tests/apply/test_quack_apply.py`."""

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.apply import quack as apply_quack
from app.config import KnowledgeParams
from app.errors import Conflict
from app.events.dispatch import RuleDeps
from app.events.outbox import JobOutbox
from app.schemas.events import Event, EventType, RecommendationAcceptedPayload
from app.schemas.quack import BatchResult, RecommendationAction, RecommendationOut

pytestmark = pytest.mark.phase4

CLOCK = datetime(2026, 9, 19, 12, tzinfo=UTC)
STUDENT = uuid4()


class _Redis:
    def __init__(self) -> None:
        self.values: dict = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, nx=False, ex=None, **_kwargs):
        if nx and key in self.values:
            return None
        self.values[key] = value
        return True

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)


class _Session:
    async def commit(self):
        pass

    async def flush(self):
        pass


@pytest.fixture
def deps() -> RuleDeps:
    return RuleDeps(
        graph=None,
        redis=_Redis(),
        params=KnowledgeParams(),
        now=lambda: CLOCK,
        jobs=JobOutbox(),
    )


def _recommendation(action: RecommendationAction, **overrides) -> RecommendationOut:
    base = {
        "id": uuid4(),
        "kind": "pace_variant",
        "urgency": "urgent",
        "position": 0,
        "status": "pending",
        "title": "заголовок",
        "reason": "причина",
        "action_text": "действие",
        "action": action,
        "reason_hash": "hash-1",
        "created_at": CLOCK,
        "exam_id": "SAT_MATH",
    }
    return RecommendationOut(**{**base, **overrides})


def _event(row: RecommendationOut) -> Event:
    return Event(
        id=42,
        type=EventType.recommendation_accepted,
        payload=RecommendationAcceptedPayload(
            recommendation_id=row.id,
            reason_hash=row.reason_hash,
            kind=row.kind,
            action=row.action,
        ).model_dump(mode="json"),
        student_id=STUDENT,
        occurred_at=CLOCK,
        ingested_at=CLOCK,
    )


def _patch_repo(monkeypatch, row, decided=None):
    decisions: list = []

    async def get(*_args):
        return row

    async def decide(_session, _student, _rec_id, status, *, now, **kwargs):
        decisions.append((status, kwargs.get("decision_event_id")))
        return decided or row.model_copy(update={"status": status, "decided_at": now})

    async def expire_siblings(*_args, **_kwargs):
        return 2

    monkeypatch.setattr(apply_quack.recs_repo, "get", get)
    monkeypatch.setattr(apply_quack.recs_repo, "decide", decide)
    monkeypatch.setattr(apply_quack.recs_repo, "expire_siblings", expire_siblings)
    return decisions


def _patch_events(monkeypatch):
    events: list = []

    async def append(_session, _redis, event_in, *args, **kwargs):
        events.append(event_in)
        return SimpleNamespace(id=99, type=event_in.type)

    monkeypatch.setattr(apply_quack.events_store, "append", append)
    return events


# --- one nested event per action kind (§8.4) ---


async def test_accepting_a_pace_variant_writes_a_profile_update(monkeypatch, deps):
    row = _recommendation(
        RecommendationAction(
            kind="profile_update", profile_path="pace.hours_per_week", profile_value=6
        )
    )
    decisions = _patch_repo(monkeypatch, row)
    events = _patch_events(monkeypatch)

    async def apply_update(_session, _student, update):
        assert update.path == "pace.hours_per_week"
        assert update.by == "user"
        return None

    monkeypatch.setattr(apply_quack.profiles_repo, "apply_profile_update", apply_update)
    await apply_quack.apply_accept(_Session(), _event(row), deps)

    assert [event.type.value for event in events] == ["profile.updated"]
    assert events[0].payload["value"] == 6
    assert decisions == [("accepted", 42)]
    # Лента должна обновиться сразу — остальные варианты темпа снимаются.
    [job] = deps.jobs.entries
    assert job.fn_name == "recommendations_batch"
    assert job.kwargs["urgent"] is True
    assert job.defer_by == 5


async def test_requirement_update_maps_to_the_right_profile_path(monkeypatch, deps):
    paths: list = []

    async def apply_update(_session, _student, update):
        paths.append((update.path, update.value))

    monkeypatch.setattr(apply_quack.profiles_repo, "apply_profile_update", apply_update)
    _patch_events(monkeypatch)

    for exam_id in ("SAT_MATH", "ENT_MATH"):
        row = _recommendation(
            RecommendationAction(
                kind="requirement_update", exam_id=exam_id, test_date=date(2026, 12, 5)
            ),
            exam_id=exam_id,
        )
        _patch_repo(monkeypatch, row)
        await apply_quack.apply_accept(_Session(), _event(row), deps)
    assert [path for path, _ in paths] == [
        "academics.sat_date",
        "academics.ent_date",
    ]


async def test_removing_a_program_writes_program_removed(monkeypatch, deps):
    row = _recommendation(
        RecommendationAction(kind="program_remove", program_id="program-1"),
        kind="pace_variant",
    )
    _patch_repo(monkeypatch, row)
    events = _patch_events(monkeypatch)

    async def list_saved(*_args):
        return [SimpleNamespace(program_id="program-1")]

    async def remove_saved(*_args):
        return None

    monkeypatch.setattr(apply_quack.programs_repo, "list_saved", list_saved)
    monkeypatch.setattr(apply_quack.programs_repo, "remove_saved", remove_saved)
    await apply_quack.apply_accept(_Session(), _event(row), deps)
    assert [event.type.value for event in events] == ["program.removed"]


async def test_acknowledge_changes_nothing_but_the_status(monkeypatch, deps):
    row = _recommendation(RecommendationAction(kind="acknowledge"), kind="conflict")
    decisions = _patch_repo(monkeypatch, row)
    events = _patch_events(monkeypatch)
    await apply_quack.apply_accept(_Session(), _event(row), deps)
    assert events == []
    assert decisions == [("accepted", 42)]


# --- idempotency and staleness ---


async def test_accepting_twice_performs_nothing_the_second_time(monkeypatch, deps):
    row = _recommendation(RecommendationAction(kind="acknowledge"), status="accepted")
    _patch_repo(monkeypatch, row)
    events = _patch_events(monkeypatch)
    result = await apply_quack.apply_accept(_Session(), _event(row), deps)
    assert result is row
    assert events == []
    assert deps.jobs.entries == []


async def test_accepting_a_declined_recommendation_conflicts(monkeypatch, deps):
    row = _recommendation(RecommendationAction(kind="acknowledge"), status="declined")
    _patch_repo(monkeypatch, row)
    _patch_events(monkeypatch)
    with pytest.raises(Conflict):
        await apply_quack.apply_accept(_Session(), _event(row), deps)


async def test_a_program_no_longer_saved_makes_the_action_stale(monkeypatch, deps):
    row = _recommendation(
        RecommendationAction(kind="program_remove", program_id="program-1")
    )
    decisions = _patch_repo(monkeypatch, row)
    _patch_events(monkeypatch)

    async def list_saved(*_args):
        return []

    monkeypatch.setattr(apply_quack.programs_repo, "list_saved", list_saved)
    with pytest.raises(Conflict, match="stale_recommendation"):
        await apply_quack.apply_accept(_Session(), _event(row), deps)
    assert decisions == [("expired", 42)]


async def test_a_finished_set_makes_set_open_stale(monkeypatch, deps):
    set_id = uuid4()
    row = _recommendation(
        RecommendationAction(kind="set_open", set_id=set_id), kind="next_set"
    )
    _patch_repo(monkeypatch, row)
    _patch_events(monkeypatch)

    async def get_set(*_args):
        return SimpleNamespace(status="done", exam_id="SAT_MATH", topics=[])

    monkeypatch.setattr(apply_quack.sets_repo, "get_set", get_set)
    with pytest.raises(Conflict, match="stale_recommendation"):
        await apply_quack.apply_accept(_Session(), _event(row), deps)


# --- decline ---


async def test_declining_records_the_decision_once(monkeypatch, deps):
    from app.schemas.events import RecommendationDeclinedPayload

    row = _recommendation(RecommendationAction(kind="acknowledge"))
    decisions = _patch_repo(monkeypatch, row)
    event = Event(
        id=7,
        type=EventType.recommendation_declined,
        payload=RecommendationDeclinedPayload(
            recommendation_id=row.id,
            reason_hash=row.reason_hash,
            kind=row.kind,
            reason="не хочу",
        ).model_dump(mode="json"),
        student_id=STUDENT,
        occurred_at=CLOCK,
        ingested_at=CLOCK,
    )
    await apply_quack.log_decline(_Session(), event, deps)
    assert decisions == [("declined", 7)]


# --- the batch lock ---


async def test_a_second_batch_for_the_same_student_is_refused(monkeypatch, deps):
    async def collect(*_args):
        raise AssertionError("locked runs must not collect inputs")

    async def reconcile(*_args, **_kwargs):
        return BatchResult()

    monkeypatch.setattr(apply_quack, "collect_inputs", collect)
    monkeypatch.setattr(apply_quack.recs_repo, "reconcile", reconcile)

    from app import keys

    deps.redis.values[keys.lock(f"recs:{STUDENT}")] = "someone-else"
    with pytest.raises(apply_quack.BatchLocked):
        await apply_quack.run_batch(_Session(), deps, STUDENT, urgent=True)


async def test_the_lock_is_released_after_a_batch(monkeypatch, deps):
    from app import keys
    from app.quack.plan import PlanInputs
    from app.schemas.profile import Profile

    async def collect(*_args):
        return PlanInputs(today=date(2026, 9, 19), profile=Profile(student_id=STUDENT))

    async def reconcile(*_args, **_kwargs):
        return BatchResult(created=1)

    monkeypatch.setattr(apply_quack, "collect_inputs", collect)
    monkeypatch.setattr(apply_quack.recs_repo, "reconcile", reconcile)
    result = await apply_quack.run_batch(_Session(), deps, STUDENT, urgent=False)
    assert result.created == 1
    assert keys.lock(f"recs:{STUDENT}") not in deps.redis.values


# --- the handlers that only enqueue ---


async def test_profile_summary_edit_debounces_one_soft_match(monkeypatch, deps):
    from app.schemas.profile import Profile

    profile = Profile(student_id=STUDENT)
    profile.traits.summary = "тёплый климат"

    async def get_profile(*_args):
        return profile

    monkeypatch.setattr(apply_quack.profiles_repo, "get_profile", get_profile)
    event = Event(
        id=1,
        type=EventType.profile_updated,
        payload={"field": "traits.summary", "value": "тёплый климат", "by": "user"},
        student_id=STUDENT,
        occurred_at=CLOCK,
        ingested_at=CLOCK,
    )
    await apply_quack.on_profile_updated_enqueue(_Session(), event, deps)
    [job] = deps.jobs.entries
    assert job.fn_name == "soft_match"
    assert job.defer_by == deps.params.soft_match_debounce_s
    assert job.kwargs["program_ids"] == []


async def test_an_empty_summary_queues_no_soft_match(monkeypatch, deps):
    from app.schemas.profile import Profile

    async def get_profile(*_args):
        return Profile(student_id=STUDENT)

    monkeypatch.setattr(apply_quack.profiles_repo, "get_profile", get_profile)
    event = Event(
        id=1,
        type=EventType.profile_updated,
        payload={"field": "traits.summary", "value": "   ", "by": "user"},
        student_id=STUDENT,
        occurred_at=CLOCK,
        ingested_at=CLOCK,
    )
    await apply_quack.on_profile_updated_enqueue(_Session(), event, deps)
    assert deps.jobs.entries == []


async def test_pace_fields_trigger_an_urgent_batch(monkeypatch, deps):
    from app.schemas.profile import Profile

    async def get_profile(*_args):
        return Profile(student_id=STUDENT)

    monkeypatch.setattr(apply_quack.profiles_repo, "get_profile", get_profile)
    event = Event(
        id=1,
        type=EventType.profile_updated,
        payload={"field": "pace.hours_per_week", "value": 6, "by": "user"},
        student_id=STUDENT,
        occurred_at=CLOCK,
        ingested_at=CLOCK,
    )
    await apply_quack.on_profile_updated_enqueue(_Session(), event, deps)
    assert [job.fn_name for job in deps.jobs.entries] == ["recommendations_batch"]


async def test_every_listed_event_queues_the_urgent_batch(deps):
    event = Event(
        id=1,
        type=EventType.program_saved,
        payload={"program_id": "p"},
        student_id=STUDENT,
        occurred_at=CLOCK,
        ingested_at=CLOCK,
    )
    await apply_quack.enqueue_recs_urgent(_Session(), event, deps)
    [job] = deps.jobs.entries
    assert job.job_id == f"recs:{STUDENT}"
    assert job.kwargs["urgent"] is True
