"""`set.completed` freezes the facts and queues the text — §13.1."""

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.apply import summary_stats
from app.config import KnowledgeParams
from app.events.dispatch import RuleDeps
from app.events.outbox import JobOutbox
from app.schemas.events import Event, EventType
from app.schemas.sets import SetOut, SetProgress, TopicOut

pytestmark = pytest.mark.phase4

CLOCK = datetime(2026, 9, 19, 12, tzinfo=UTC)
STUDENT = uuid4()
SET_ID = uuid4()


class _Session:
    async def commit(self):
        pass

    async def flush(self):
        pass

    async def scalar(self, *_args, **_kwargs):
        return None


@pytest.fixture
def deps() -> RuleDeps:
    return RuleDeps(
        graph=None,
        redis=SimpleNamespace(),
        params=KnowledgeParams(),
        now=lambda: CLOCK,
        jobs=JobOutbox(),
    )


def _set() -> SetOut:
    return SetOut(
        id=SET_ID,
        exam_id="SAT_MATH",
        area_ids=["algebra"],
        status="done",
        kind="regular",
        position=0,
        deadline=date(2026, 9, 21),
        reason="по модели знаний",
        topics=[
            TopicOut(
                skill_id="a",
                name="Линейные уравнения",
                kind="topic",
                position=0,
                status="closed",
                level="solid",
                is_root=False,
                misconception_labels=[],
                subtitle=None,
            )
        ],
        progress=SetProgress(
            topics_closed=1, topics_total=1, tasks_answered=5, tasks_correct=4
        ),
        opened_at=datetime(2026, 9, 10, tzinfo=UTC),
        completed_at=CLOCK,
    )


def _event() -> Event:
    return Event(
        id=10,
        type=EventType.set_completed,
        payload={"set_id": str(SET_ID)},
        student_id=STUDENT,
        exam_id="SAT_MATH",
        set_id=SET_ID,
        occurred_at=CLOCK,
        ingested_at=CLOCK,
    )


@pytest.fixture
def patched(monkeypatch):
    stored: dict = {}

    async def rebuild(*_args):
        stored["rebuilt"] = True

    async def get_set(*_args):
        return _set()

    async def count_progress(*_args):
        return _set().progress

    async def list_sets(*_args):
        return []

    async def p_target(*_args, **_kwargs):
        return 0.9

    async def forecast_get(*_args):
        return None

    async def get_latest(*_args, **_kwargs):
        return None

    async def upsert_stats(_session, student_id, set_id, exam_id, stats, **kwargs):
        stored["stats"] = stats
        stored["input_hash"] = kwargs["input_hash"]
        stored["status"] = kwargs.get("status", "generating")
        return SimpleNamespace(stats=stats)

    monkeypatch.setattr(summary_stats, "rebuild_sets", rebuild)
    monkeypatch.setattr(summary_stats.sets_repo, "get_set", get_set)
    monkeypatch.setattr(summary_stats.sets_repo, "count_progress", count_progress)
    monkeypatch.setattr(summary_stats.sets_repo, "list_sets", list_sets)
    monkeypatch.setattr(summary_stats, "p_target_for", p_target)
    monkeypatch.setattr(summary_stats.forecast_repo, "get", forecast_get)
    monkeypatch.setattr(summary_stats.summaries_repo, "get_latest", get_latest)
    monkeypatch.setattr(summary_stats.summaries_repo, "upsert_stats", upsert_stats)
    return stored


async def test_the_statistics_are_written_inside_the_event_transaction(patched, deps):
    stats = await summary_stats.on_set_completed(_Session(), _event(), deps)
    assert stats is not None
    assert patched["status"] == "generating"
    assert patched["stats"].tasks_answered == 5
    assert patched["stats"].tasks_correct == 4
    assert patched["stats"].days_vs_deadline == 2
    # Пересборка вызвана явно — иначе «прогноз после» и «следующий сет»
    # были бы вчерашними (§4.3).
    assert patched["rebuilt"] is True


async def test_the_text_is_queued_on_the_interactive_queue(patched, deps):
    await summary_stats.on_set_completed(_Session(), _event(), deps)
    [job] = deps.jobs.entries
    assert (job.queue, job.fn_name) == ("interactive", "set_summary")
    assert job.job_id == f"summary:{SET_ID}"


async def test_the_input_hash_changes_with_the_prompt_version(patched, deps):
    from app.sets.report import ReportInputs, set_stats

    stats = set_stats(
        ReportInputs(set_id=SET_ID, exam_id="SAT_MATH", deadline=date(2026, 9, 21)),
        KnowledgeParams(),
        CLOCK,
    )
    first = summary_stats.input_hash(stats, "set_summary_v1", "model")
    assert first == summary_stats.input_hash(stats, "set_summary_v1", "model")
    assert first != summary_stats.input_hash(stats, "set_summary_v2", "model")
    assert first != summary_stats.input_hash(stats, "set_summary_v1", "other")


async def test_a_broken_statistic_never_fails_the_student_request(
    monkeypatch, patched, deps
):
    """§2.2: обработчик фона не имеет права уронить закрытие сета."""

    async def boom(*_args, **_kwargs):
        raise RuntimeError("graph exploded")

    monkeypatch.setattr(summary_stats, "build_stats", boom)
    assert await summary_stats.on_set_completed(_Session(), _event(), deps) is None
    assert deps.jobs.entries == []


async def test_a_missing_set_is_skipped(monkeypatch, patched, deps):
    async def get_set(*_args):
        return None

    monkeypatch.setattr(summary_stats.sets_repo, "get_set", get_set)
    assert await summary_stats.on_set_completed(_Session(), _event(), deps) is None
