"""Misconception statuses and triggers — memory-architecture-quack.md §5.1–§5.3.

Numbers come from 20-B1-phase2.md §8 (test_misconceptions block).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.config import KnowledgeParams
from app.knowledge.misconceptions import (
    next_status,
    trigger_words,
    update_triggers,
    visible_label,
    visible_to,
)
from app.schemas.knowledge import EvidenceContext, EvidenceIn, MisconceptionStateOut

pytestmark = pytest.mark.phase1

PARAMS = KnowledgeParams()
NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


# --- next_status: §5.1 transitions ---


def test_next_status_none_to_suspected():
    s = next_status(
        None,
        event="hit",
        strong=False,
        occurrence_count=1,
        strong_count=0,
        consecutive_avoided=0,
        strong_at_dispute=0,
        disputed_at=None,
        previous_status=None,
        params=PARAMS,
    )
    assert s == "suspected"


def test_next_status_suspected_to_confirmed():
    s = next_status(
        "suspected",
        event="hit",
        strong=True,
        occurrence_count=2,
        strong_count=1,
        consecutive_avoided=0,
        strong_at_dispute=0,
        disputed_at=None,
        previous_status=None,
        params=PARAMS,
    )
    assert s == "confirmed"


def test_next_status_suspected_stays_if_not_enough_occurrences():
    s = next_status(
        "suspected",
        event="hit",
        strong=True,
        occurrence_count=1,
        strong_count=1,
        consecutive_avoided=0,
        strong_at_dispute=0,
        disputed_at=None,
        previous_status=None,
        params=PARAMS,
    )
    assert s == "suspected"


def test_next_status_suspected_stays_if_no_strong():
    s = next_status(
        "suspected",
        event="hit",
        strong=False,
        occurrence_count=3,
        strong_count=0,
        consecutive_avoided=0,
        strong_at_dispute=0,
        disputed_at=None,
        previous_status=None,
        params=PARAMS,
    )
    assert s == "suspected"


def test_next_status_confirmed_to_resolved_by_avoided():
    s = next_status(
        "confirmed",
        event="avoided",
        strong=False,
        occurrence_count=3,
        strong_count=1,
        consecutive_avoided=PARAMS.misc_resolve_avoided,
        strong_at_dispute=0,
        disputed_at=None,
        previous_status=None,
        params=PARAMS,
    )
    assert s == "resolved"


def test_next_status_resolved_relapse_on_hit():
    s = next_status(
        "resolved",
        event="hit",
        strong=False,
        occurrence_count=4,
        strong_count=1,
        consecutive_avoided=0,
        strong_at_dispute=0,
        disputed_at=None,
        previous_status=None,
        params=PARAMS,
    )
    assert s == "confirmed"


def test_next_status_any_to_disputed():
    s = next_status(
        "confirmed",
        event="dispute",
        strong=False,
        occurrence_count=3,
        strong_count=1,
        consecutive_avoided=0,
        strong_at_dispute=1,
        disputed_at=NOW,
        previous_status="confirmed",
        params=PARAMS,
    )
    assert s == "disputed"


def test_next_status_disputed_to_confirmed_after_two_strong():
    s = next_status(
        "disputed",
        event="hit",
        strong=True,
        occurrence_count=5,
        strong_count=3,
        consecutive_avoided=0,
        strong_at_dispute=1,  # +2 strong после dispute → confirmed
        disputed_at=NOW - timedelta(days=1),
        previous_status="confirmed",
        params=PARAMS,
    )
    assert s == "confirmed"


def test_next_status_disputed_undispute_to_previous():
    s = next_status(
        "disputed",
        event="undispute",
        strong=False,
        occurrence_count=3,
        strong_count=1,
        consecutive_avoided=0,
        strong_at_dispute=1,
        disputed_at=NOW,
        previous_status="confirmed",
        params=PARAMS,
    )
    assert s == "confirmed"


# --- update_triggers: §5.3 ---


def _ev(
    *,
    kind: str = "task",
    direction: int = -1,
    task_type: str | None = "mcq4",
    difficulty: int | None = 3,
    tags: list[str] | None = None,
    time_ratio: float | None = None,
    session_minute: int | None = None,
    after_guideline: bool | None = None,
) -> EvidenceIn:
    ctx = EvidenceContext(
        task_type=task_type,  # type: ignore[arg-type]
        difficulty=difficulty,
        tags=tags,
        mode=None,
        time_ratio=time_ratio,
        session_minute=session_minute,
        after_guideline=after_guideline,
        hint_level_before=None,
        topic_skill_id=None,
        session_id=None,
    )
    return EvidenceIn(
        event_id=1,
        skill_id="math.alg.abs_value_eq",
        exam_id="SAT_MATH",
        kind=kind,
        tier=2,  # type: ignore[arg-type]
        source="task",
        weight=0.8,
        direction=direction,  # type: ignore[arg-type]
        share=None,
        difficulty_factor=1.0,
        summary=None,
        context=ctx,
        observed_at=NOW,
        extractor_version=None,
    )


def test_update_triggers_hurried_three_of_four():
    evidences = [
        _ev(time_ratio=0.5),  # hurried
        _ev(time_ratio=0.6),  # hurried
        _ev(time_ratio=0.4),  # hurried
        _ev(time_ratio=0.95),  # not hurried
    ]
    triggers = update_triggers(evidences, params=PARAMS)
    assert triggers["n"] == 4
    assert triggers["hurried"] == (3, 4)


def test_update_triggers_by_task_type():
    evidences = [
        _ev(task_type="mcq4"),
        _ev(task_type="mcq4"),
        _ev(task_type="numeric"),
    ]
    triggers = update_triggers(evidences, params=PARAMS)
    assert triggers["by_task_type"]["mcq4"] == (2, 3)
    assert triggers["by_task_type"]["numeric"] == (1, 3)


def test_update_triggers_by_difficulty_high_bucket():
    evidences = [
        _ev(difficulty=4),
        _ev(difficulty=5),
        _ev(difficulty=2),
    ]
    triggers = update_triggers(evidences, params=PARAMS)
    assert triggers["by_difficulty"]["≥4"] == (2, 3)


def test_update_triggers_by_tag():
    evidences = [
        _ev(tags=["negative_branch", "sum_of_roots"]),
        _ev(tags=["negative_branch"]),
        _ev(tags=["other"]),
    ]
    triggers = update_triggers(evidences, params=PARAMS)
    assert triggers["by_tag"]["negative_branch"] == (2, 3)


# --- trigger_words ---


def test_trigger_words_below_min_n_returns_none():
    triggers = {"n": 2, "hurried": (2, 2)}
    assert trigger_words(triggers, params=PARAMS) is None


def test_trigger_words_below_min_share_returns_none():
    triggers = {"n": 4, "hurried": (2, 4)}
    assert trigger_words(triggers, params=PARAMS) is None


def test_trigger_words_returns_phrase_at_min_n_and_share():
    triggers = {"n": 4, "hurried": (3, 4), "by_tag": {"negative_branch": (4, 4)}}
    words = trigger_words(triggers, params=PARAMS)
    assert isinstance(words, str)
    assert words  # непустая фраза


# --- visible_label ---


def _misc(**kwargs) -> MisconceptionStateOut:
    base = dict(
        misconception_id="lib.abs_single_branch",
        name="Раскрытие модуля только в одной ветви",
        status="suspected",
        occurrence_count=1,
        strong_count=0,
        consecutive_avoided=0,
        triggers={},
        first_seen_at=NOW - timedelta(days=1),
        updated_at=NOW,
        skill_ids=["math.alg.abs_value_eq"],
    )
    base.update(kwargs)
    return MisconceptionStateOut(**base)  # type: ignore[arg-type]


def test_visible_label_suspected():
    s = _misc(status="suspected", occurrence_count=1)
    label = visible_label(s, params=PARAMS, now=NOW)
    assert "подозрение" in label.lower()


def test_visible_label_confirmed():
    s = _misc(status="confirmed", occurrence_count=3, strong_count=1)
    label = visible_label(s, params=PARAMS, now=NOW)
    assert "подтверждено" in label.lower()


def test_visible_label_resolved_fresh():
    s = _misc(
        status="resolved",
        updated_at=NOW - timedelta(days=2),
    )
    label = visible_label(s, params=PARAMS, now=NOW)
    assert "исправлено" in label.lower()


def test_visible_label_resolved_old_is_empty():
    s = _misc(
        status="resolved",
        updated_at=NOW - timedelta(days=PARAMS.under_watch_days + 1),
    )
    assert visible_label(s, params=PARAMS, now=NOW) == ""


def test_visible_label_disputed():
    s = _misc(status="disputed")
    label = visible_label(s, params=PARAMS, now=NOW)
    assert "оспорено" in label.lower()


# --- visible_to ---


def test_visible_to_student_sees_suspected():
    s = _misc(status="suspected")
    assert visible_to(s, audience="student", params=PARAMS, now=NOW) is True


def test_visible_to_tutor_does_not_see_suspected():
    s = _misc(status="suspected")
    assert visible_to(s, audience="tutor", params=PARAMS, now=NOW) is False


def test_visible_to_tutor_sees_confirmed():
    s = _misc(status="confirmed")
    assert visible_to(s, audience="tutor", params=PARAMS, now=NOW) is True


def test_visible_to_tutor_sees_fresh_resolved():
    s = _misc(status="resolved", updated_at=NOW - timedelta(days=2))
    assert visible_to(s, audience="tutor", params=PARAMS, now=NOW) is True


def test_visible_to_tutor_does_not_see_old_resolved():
    s = _misc(status="resolved", updated_at=NOW - timedelta(days=15))
    assert visible_to(s, audience="tutor", params=PARAMS, now=NOW) is False


def test_visible_to_sets_sees_confirmed():
    s = _misc(status="confirmed")
    assert visible_to(s, audience="sets", params=PARAMS, now=NOW) is True


def test_visible_to_sets_does_not_see_suspected():
    s = _misc(status="suspected")
    assert visible_to(s, audience="sets", params=PARAMS, now=NOW) is False
