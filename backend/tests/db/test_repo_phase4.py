"""Phase-4 repositories against a real Postgres — §13.3."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from app.db.repo import aggregates as aggregates_repo
from app.db.repo import programs as programs_repo
from app.db.repo import recommendations as recs_repo
from app.db.repo import soft_matches as soft_repo
from app.db.repo import summaries as summaries_repo
from app.db.repo import texts as texts_repo
from app.schemas.programs import ExtractionMeta
from app.schemas.quack import (
    DailyAggregatePayload,
    RecDraft,
    RecommendationAction,
    StudentAggregates,
)
from app.schemas.sets import SetStats
from tests.quack.conftest import make_program

pytestmark = [pytest.mark.integration, pytest.mark.phase4]

NOW = datetime(2026, 9, 19, 12, tzinfo=UTC)
TODAY = date(2026, 9, 19)


def _stats(set_id) -> SetStats:
    return SetStats(
        set_id=set_id,
        exam_id="SAT_MATH",
        kind="regular",
        deadline=TODAY,
        tasks_answered=5,
        tasks_correct=4,
    )


def _draft(reason_hash: str, urgency: str = "urgent", **overrides) -> RecDraft:
    base = {
        "kind": "pace_variant",
        "urgency": urgency,
        "title": "заголовок",
        "reason": "причина",
        "action_text": "действие",
        "action": RecommendationAction(kind="acknowledge"),
        "reason_hash": reason_hash,
        "exam_id": "SAT_MATH",
    }
    return RecDraft(**{**base, **overrides})


# --- generated_texts (§3.5) ---


async def test_texts_status_lifecycle_and_stale_fallback(db_session):
    student = uuid4()
    subject = f"skill-{uuid4().hex[:8]}"

    await texts_repo.mark(
        db_session,
        "guideline",
        "hash-old",
        "ready",
        text="старый",
        student_id=student,
        subject=subject,
        model="m",
        prompt_version="guideline_v1",
    )
    current, last = await texts_repo.get_current(
        db_session, student, "guideline", subject, "hash-new"
    )
    # Текущего нет, но прошлая готовая версия есть — это `stale` для читателя.
    assert current is None
    assert last is not None and last.text == "старый"

    await texts_repo.mark(
        db_session,
        "guideline",
        "hash-new",
        "generating",
        student_id=student,
        subject=subject,
    )
    current, last = await texts_repo.get_current(
        db_session, student, "guideline", subject, "hash-new"
    )
    assert current.status == "generating" and current.attempts == 1
    assert last.input_hash == "hash-old"

    await texts_repo.mark(
        db_session,
        "guideline",
        "hash-new",
        "failed",
        error="invalid_output",
        subject=subject,
    )
    row = await texts_repo.get_generated(db_session, "guideline", "hash-new")
    assert row.status == "failed" and row.attempts == 2

    await texts_repo.reset_attempts(db_session, "guideline", "hash-new")
    row = await texts_repo.get_generated(db_session, "guideline", "hash-new")
    assert row.attempts == 0 and row.error is None

    await texts_repo.mark(
        db_session, "guideline", "hash-new", "ready", text="новый", subject=subject
    )
    current, _ = await texts_repo.get_current(
        db_session, student, "guideline", subject, "hash-new"
    )
    assert current.status == "ready" and current.text == "новый"


async def test_shared_explanations_are_found_by_a_null_owner(db_session):
    subject = f"skill-{uuid4().hex[:8]}"
    await texts_repo.mark(
        db_session,
        "explanation",
        f"hash-{uuid4().hex[:8]}",
        "ready",
        text="общий текст",
        student_id=None,
        subject=subject,
    )
    shared = await texts_repo.last_ready(db_session, None, "explanation", subject)
    assert shared is not None and shared.text == "общий текст"
    # Тот же subject, но с владельцем — другая выборка, пусто.
    owned = await texts_repo.last_ready(db_session, uuid4(), "explanation", subject)
    assert owned is None


# --- set_summaries (§4.5) ---


async def test_one_summary_per_set_and_ready_text_survives_a_replay(db_session):
    student, set_id = uuid4(), uuid4()
    await summaries_repo.upsert_stats(
        db_session, student, set_id, "SAT_MATH", _stats(set_id), input_hash="h1"
    )
    await summaries_repo.set_text(db_session, set_id, "готовый текст", "v1", "ready")

    # Повтор `set.completed` не перезаписывает готовый текст.
    await summaries_repo.upsert_stats(
        db_session, student, set_id, "SAT_MATH", _stats(set_id), input_hash="h2"
    )
    row = await summaries_repo.get(db_session, set_id)
    assert row.status == "ready" and row.text == "готовый текст"
    assert row.stats.tasks_answered == 5

    latest = await summaries_repo.get_latest(db_session, student, "SAT_MATH")
    assert latest.set_id == set_id
    assert await summaries_repo.get_latest(db_session, student, "ENT_MATH") is None


async def test_previous_summary_skips_the_current_set(db_session):
    student = uuid4()
    first, second = uuid4(), uuid4()
    for set_id in (first, second):
        await summaries_repo.upsert_stats(
            db_session, student, set_id, "SAT_MATH", _stats(set_id), input_hash="h"
        )
    previous = await summaries_repo.get_previous(
        db_session, student, before_set_id=second
    )
    assert previous.set_id == first


# --- recommendations (§8.4) ---


async def test_reconcile_creates_updates_and_expires(db_session):
    student = uuid4()
    created = await recs_repo.reconcile(
        db_session,
        student,
        [_draft("cause-a"), _draft("cause-b", "normal")],
        urgent_only=False,
        now=NOW,
        batch_id=uuid4(),
    )
    assert (created.created, created.updated, created.expired) == (2, 0, 0)

    again = await recs_repo.reconcile(
        db_session,
        student,
        [_draft("cause-a", title="новый заголовок")],
        urgent_only=False,
        now=NOW,
    )
    # Причина «b» исчезла — рекомендация по ней больше не актуальна.
    assert (again.created, again.updated, again.expired) == (0, 1, 1)
    [open_row] = await recs_repo.list_open(db_session, student, now=NOW)
    assert open_row.reason_hash == "cause-a"


async def test_an_urgent_run_does_not_touch_the_quiet_ones(db_session):
    student = uuid4()
    await recs_repo.reconcile(
        db_session,
        student,
        [_draft("urgent-1"), _draft("quiet-1", "normal")],
        urgent_only=False,
        now=NOW,
    )
    result = await recs_repo.reconcile(
        db_session, student, [_draft("urgent-2")], urgent_only=True, now=NOW
    )
    assert result.created == 1
    # `normal` не записывается и не экспайрится до крона (§8.2).
    open_hashes = {
        row.reason_hash for row in await recs_repo.list_open(db_session, student)
    }
    assert open_hashes == {"urgent-2", "quiet-1"}


async def test_only_one_open_recommendation_per_cause(db_session):
    student = uuid4()
    await recs_repo.reconcile(
        db_session, student, [_draft("cause")], urgent_only=False, now=NOW
    )
    await recs_repo.reconcile(
        db_session, student, [_draft("cause")], urgent_only=False, now=NOW
    )
    rows = await recs_repo.list_open(db_session, student)
    assert len(rows) == 1


async def test_declined_causes_are_remembered_for_the_window(db_session):
    student = uuid4()
    await recs_repo.reconcile(
        db_session, student, [_draft("cause")], urgent_only=False, now=NOW
    )
    [row] = await recs_repo.list_open(db_session, student)
    await recs_repo.decide(db_session, student, row.id, "declined", now=NOW)

    recent = await recs_repo.declined_hashes(db_session, student, 90, now=NOW)
    assert recent == {"cause"}
    later = await recs_repo.declined_hashes(
        db_session, student, 90, now=NOW + timedelta(days=100)
    )
    assert later == set()
    assert [item.status for item in await recs_repo.history(db_session, student)] == [
        "declined"
    ]


async def test_mark_shown_and_expired_filtering(db_session):
    student = uuid4()
    await recs_repo.reconcile(
        db_session,
        student,
        [
            _draft("cause-a"),
            _draft("cause-b", expires_at=NOW - timedelta(days=1)),
        ],
        urgent_only=False,
        now=NOW,
    )
    # Просроченная по дате не показывается, хотя в БД ещё открыта (§8.4).
    assert [
        row.reason_hash
        for row in await recs_repo.list_open(db_session, student, now=NOW)
    ] == ["cause-a"]
    assert await recs_repo.mark_shown(db_session, student, None, now=NOW) == 2
    [row] = await recs_repo.list_open(db_session, student, now=NOW)
    assert row.status == "shown" and row.shown_at is not None


async def test_accepting_one_variant_expires_its_siblings(db_session):
    student = uuid4()
    await recs_repo.reconcile(
        db_session,
        student,
        [_draft("v1"), _draft("v2"), _draft("v3")],
        urgent_only=False,
        now=NOW,
    )
    rows = await recs_repo.list_open(db_session, student)
    keep = rows[0]
    await recs_repo.decide(db_session, student, keep.id, "accepted", now=NOW)
    expired = await recs_repo.expire_siblings(
        db_session, student, "pace_variant", "SAT_MATH", keep_id=keep.id, now=NOW
    )
    assert expired == 2
    assert await recs_repo.list_open(db_session, student) == []


# --- soft_matches (§5.5) ---


async def test_soft_matches_are_keyed_by_summary_program_and_version(db_session):
    digest = f"summary-{uuid4().hex[:8]}"
    program_id = f"program-{uuid4().hex[:8]}"
    await soft_repo.put(
        db_session,
        digest,
        program_id,
        "soft_match_v1",
        score=0.8,
        text="подходит",
        model="m",
    )
    rows = await soft_repo.get_many(db_session, digest, [program_id], "soft_match_v1")
    assert rows[program_id].score == 0.8 and rows[program_id].stale is False

    # Новая версия промпта — пока строки нет, читается старая как stale.
    rows = await soft_repo.get_many(db_session, digest, [program_id], "soft_match_v2")
    assert rows[program_id].stale is True

    assert await soft_repo.delete_for_program(db_session, program_id) == 1
    assert (
        await soft_repo.get_many(db_session, digest, [program_id], "soft_match_v1")
        == {}
    )


# --- aggregates (§9) ---


async def test_the_window_is_rewritten_and_pace_signals_survive(db_session):
    student = uuid4()
    await aggregates_repo.add_pace_signal(db_session, student, TODAY, "slow", 1, 0)
    await aggregates_repo.upsert_days(
        db_session,
        student,
        [
            DailyAggregatePayload(
                day=TODAY, tz="Asia/Almaty", tasks_answered=3, active_minutes=25
            )
        ],
    )
    days = await aggregates_repo.list_days(db_session, student, TODAY, TODAY)
    assert days[0].tasks_answered == 3
    # Наблюдатель пишет сигналы в тот же payload — пересчёт их не стирает.
    from app.db.models import DailyAggregate

    row = await db_session.get(DailyAggregate, (student, TODAY))
    assert row.payload["pace_signals"][0]["signal"] == "slow"


async def test_the_activity_calendar_covers_every_day(db_session):
    student = uuid4()
    await aggregates_repo.upsert_days(
        db_session,
        student,
        [
            DailyAggregatePayload(
                day=TODAY, tz="Asia/Almaty", tasks_answered=2, active_minutes=30
            )
        ],
    )
    await aggregates_repo.put_summary(
        db_session,
        student,
        StudentAggregates(
            student_id=student,
            window_days=14,
            computed_at=NOW,
            hours_per_week_actual=1.5,
        ),
    )
    activity = await aggregates_repo.activity(
        db_session, student, today=TODAY, days=14, tz="Asia/Almaty", hours_declared=4
    )
    assert len(activity.days) == 14
    assert activity.active_days == 1
    assert activity.days[-1].day == TODAY and activity.days[-1].active is True
    assert activity.hours_per_week_actual == 1.5
    assert activity.hours_per_week_declared == 4


# --- programs (§6.7) ---


def _meta() -> ExtractionMeta:
    return ExtractionMeta(
        prompt_version="extract_program_v1",
        model="m",
        page_chars=2000,
        extracted_at=NOW,
    )


async def test_an_extracted_program_is_stored_with_its_metadata(db_session):
    suffix = uuid4().hex[:8]
    program = make_program(1, threshold=1400, extracted_auto=True)
    program = program.model_copy(update={"id": f"auto-{suffix}"})
    url = f"https://example.test/{suffix}"
    outcome = await programs_repo.upsert_extracted(
        db_session,
        program,
        _meta(),
        normalized_url=url,
        university_slug=f"uni-{suffix}",
        direction_slug="math",
    )
    assert outcome == "created"
    stored = await programs_repo.get_by_normalized_url(db_session, url)
    assert stored.id == program.id
    assert stored.extraction.prompt_version == "extract_program_v1"


async def test_the_curated_floor_always_wins_a_duplicate(db_session):
    suffix = uuid4().hex[:8]
    floor = make_program(1, threshold=1400).model_copy(
        update={"id": f"floor-{suffix}", "extracted_auto": False}
    )
    await programs_repo.upsert_program(
        db_session,
        floor,
        normalized_url=f"https://floor.test/{suffix}",
        university_slug=f"uni-{suffix}",
        direction_slug="math",
    )
    auto = make_program(2, threshold=1400).model_copy(
        update={"id": f"auto-{suffix}", "extracted_auto": True}
    )
    outcome = await programs_repo.upsert_extracted(
        db_session,
        auto,
        _meta(),
        normalized_url=f"https://auto.test/{suffix}",
        university_slug=f"uni-{suffix}",
        direction_slug="math",
    )
    assert outcome == "skipped_floor"
    assert await programs_repo.get_program(db_session, auto.id) is None


async def test_the_richer_automatic_duplicate_supersedes_the_poorer(db_session):
    suffix = uuid4().hex[:8]
    poor = make_program(1).model_copy(
        update={"id": f"poor-{suffix}", "extracted_auto": True, "deadlines": []}
    )
    await programs_repo.upsert_extracted(
        db_session,
        poor,
        _meta(),
        normalized_url=f"https://poor.test/{suffix}",
        university_slug=f"uni-{suffix}",
        direction_slug="math",
    )
    rich = make_program(2, threshold=1400).model_copy(
        update={
            "id": f"rich-{suffix}",
            "extracted_auto": True,
            "tuition_per_year": 12000,
        }
    )
    outcome = await programs_repo.upsert_extracted(
        db_session,
        rich,
        _meta(),
        normalized_url=f"https://rich.test/{suffix}",
        university_slug=f"uni-{suffix}",
        direction_slug="math",
    )
    assert outcome == "superseded"
    loser = await programs_repo.get_program(db_session, poor.id)
    # Проигравшая не удаляется — на неё мог сослаться сохранённый список.
    assert loser.flagged is True
    assert f"superseded_by:{rich.id}" in loser.extraction.notes


async def test_flagging_hides_a_record_and_refuses_the_floor(db_session):
    from app.errors import Conflict

    suffix = uuid4().hex[:8]
    auto = make_program(1).model_copy(
        update={"id": f"auto-{suffix}", "extracted_auto": True}
    )
    await programs_repo.upsert_program(db_session, auto, extraction=_meta())
    flagged = await programs_repo.flag(db_session, auto.id, "неверные данные")
    assert flagged.flagged is True
    assert auto.id not in {p.id for p in await programs_repo.list_all(db_session)}

    floor = make_program(2).model_copy(
        update={"id": f"floor-{suffix}", "extracted_auto": False}
    )
    await programs_repo.upsert_program(db_session, floor)
    with pytest.raises(Conflict):
        await programs_repo.flag(db_session, floor.id, "неверно")
