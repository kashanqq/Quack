"""T10–T14, T27: what is recoverable, in what order, and what is not (§12, D02)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.events import recovery
from app.events.dispatch import RuleDeps, dispatch, on
from app.schemas.events import Event, EventType
from app.schemas.tasks import AnswerResult, Grade

pytestmark = pytest.mark.phase5

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


def _event(event_id: int, type_: EventType, student_id=None) -> Event:
    return Event(
        id=event_id,
        student_id=student_id or uuid4(),
        type=type_,
        payload={},
        occurred_at=NOW,
        ingested_at=NOW,
    )


def test_t14_only_graph_mutating_types_are_recoverable():
    """Сырые сообщения и служебные записи графу не отдаются (§12)."""
    assert recovery.is_recoverable(EventType.task_answered)
    assert recovery.is_recoverable(EventType.observation_extracted)
    assert recovery.is_recoverable(EventType.diagnostic_completed)

    for excluded in (
        EventType.message_user,
        EventType.message_assistant,
        EventType.observer_requested,
        EventType.job_failed,
        EventType.guideline_opened,
        EventType.recommendation_accepted,
        EventType.set_opened,
    ):
        assert not recovery.is_recoverable(excluded), excluded


def test_the_allowlist_only_names_types_that_exist():
    for event_type in recovery.RECOVERABLE:
        assert isinstance(event_type, EventType)


class _Session:
    """Just enough session for the dispatcher's ordering check."""

    def __init__(self, backlog_before: bool = False) -> None:
        self.backlog_before = backlog_before
        self.marked: list[list[int]] = []

    async def scalar(self, _statement):
        return 1 if self.backlog_before else None

    async def execute(self, _statement):
        self.marked.append([1])
        return None


@pytest.fixture
def deps(redis):
    return RuleDeps(graph=object(), redis=redis, params=None, now=lambda: NOW)


async def test_t11_a_pending_projection_leaves_the_event_unprocessed(deps, monkeypatch):
    """Обработчик сказал «сохранил, но не спроецировал» — событие остаётся."""
    kind = EventType.misconception_disputed
    result = AnswerResult(
        grade=Grade(correct=True),
        solution=[],
        state_words="",
        knowledge_version=0,
        projection_status="pending",
    )

    async def handler(_session, _event, _deps):
        return result

    monkeypatch.setitem(
        dispatch.__globals__["_handlers"],
        kind,
        [handler],  # type: ignore[index]
    )
    session = _Session()
    await dispatch(session, _event(5, kind), deps)
    assert session.marked == []


async def test_a_finished_projection_marks_the_event(deps, monkeypatch):
    kind = EventType.misconception_undisputed

    async def handler(_session, _event, _deps):
        return None

    monkeypatch.setitem(dispatch.__globals__["_handlers"], kind, [handler])
    session = _Session()
    event = _event(5, kind)
    await dispatch(session, event, deps)
    assert session.marked == [[1]]
    assert event.processed_at == NOW


async def test_a_new_event_does_not_overtake_an_older_pending_one(deps, monkeypatch):
    """§11 A2: иначе состояние считается из неверной базы."""
    kind = EventType.task_answered
    ran = []

    async def handler(_session, _event, _deps):
        ran.append(1)

    monkeypatch.setitem(dispatch.__globals__["_handlers"], kind, [handler])
    session = _Session(backlog_before=True)
    await dispatch(session, _event(9, kind), deps)
    assert ran == []
    assert session.marked == []


async def test_an_event_without_backlog_behind_it_is_applied(deps, monkeypatch):
    kind = EventType.task_answered
    ran = []

    async def handler(_session, _event, _deps):
        ran.append(1)

    monkeypatch.setitem(dispatch.__globals__["_handlers"], kind, [handler])
    session = _Session(backlog_before=False)
    await dispatch(session, _event(9, kind), deps)
    assert ran == [1]


async def test_a_non_graph_event_is_never_held_back(deps, monkeypatch):
    """set.opened только ставит предгенерацию — ждать графа ему незачем."""
    kind = EventType.set_opened
    ran = []

    async def handler(_session, _event, _deps):
        ran.append(1)

    monkeypatch.setitem(dispatch.__globals__["_handlers"], kind, [handler])
    session = _Session(backlog_before=True)
    await dispatch(session, _event(9, kind), deps)
    assert ran == [1]


def test_on_registers_without_disturbing_the_table():
    """`on` остаётся тем же контрактом — фаза 5 его не меняет."""
    assert callable(on(EventType.task_answered))
