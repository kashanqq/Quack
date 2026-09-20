"""The end-of-set statistics — §13.1 `test_report.py`."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.config import KnowledgeParams
from app.schemas.knowledge import MisconceptionStateOut
from app.sets.report import ReportInputs, SkillHistory, set_stats, stats_words
from tests.quack.conftest import make_state

pytestmark = pytest.mark.phase4

PARAMS = KnowledgeParams()
OPENED = datetime(2026, 9, 1, 10, tzinfo=UTC)
CLOSED = datetime(2026, 9, 10, 18, tzinfo=UTC)
NOW = datetime(2026, 9, 10, 19, tzinfo=UTC)


def _misconception(misconception_id: str, status: str, updated: datetime, first=None):
    return MisconceptionStateOut(
        misconception_id=misconception_id,
        name=f"заблуждение {misconception_id}",
        status=status,
        occurrence_count=2,
        strong_count=1,
        consecutive_avoided=0,
        triggers={},
        first_seen_at=first or OPENED,
        updated_at=updated,
        skill_ids=["a"],
    )


def _inputs(**overrides) -> ReportInputs:
    base = {
        "set_id": uuid4(),
        "exam_id": "SAT_MATH",
        "kind": "regular",
        "opened_at": OPENED,
        "completed_at": CLOSED,
        "deadline": date(2026, 9, 12),
        "tasks_answered": 5,
        "tasks_correct": 4,
        "mocks_completed": 1,
        "skills": [
            SkillHistory(
                skill_id="a",
                name="Линейные уравнения",
                before=make_state("a", 0.4),
                after=make_state("a", 0.8),
                closed=True,
            ),
            SkillHistory(
                skill_id="b",
                name="Проценты",
                before=make_state("b", 0.6),
                after=make_state("b", 0.65),
                closed=False,
            ),
        ],
        "misconceptions": [],
        "p_target": 0.9,
    }
    return ReportInputs(**{**base, **overrides})


def test_days_vs_deadline_is_positive_when_finished_early():
    stats = set_stats(_inputs(), PARAMS, NOW)
    assert stats.days_in_set == 9
    assert stats.days_vs_deadline == 2
    late = set_stats(_inputs(deadline=date(2026, 9, 7)), PARAMS, NOW)
    assert late.days_vs_deadline == -3


def test_top_growth_is_ordered_by_delta_and_skips_flat_skills():
    stats = set_stats(_inputs(), PARAMS, NOW)
    assert stats.top_growth[0] == "a"
    assert stats.skills[0].delta_p == pytest.approx(0.4)
    assert stats.skills[0].level_before == "weak"
    assert stats.skills[0].level_after == "shaky"
    assert stats.skills_closed == 1 and stats.skills_total == 2


def test_top_growth_is_capped_by_the_parameter():
    params = KnowledgeParams(summary_top_growth=1)
    stats = set_stats(_inputs(), params, NOW)
    assert stats.top_growth == ["a"]


def test_misconceptions_are_split_by_status_and_window():
    inside = _misconception("m1", "resolved", datetime(2026, 9, 5, tzinfo=UTC))
    outside = _misconception("m2", "resolved", datetime(2026, 8, 1, tzinfo=UTC))
    watching = _misconception("m3", "confirmed", CLOSED, first=OPENED)
    older = _misconception(
        "m4", "confirmed", CLOSED, first=datetime(2026, 7, 1, tzinfo=UTC)
    )
    disputed = _misconception("m5", "disputed", CLOSED)
    stats = set_stats(
        _inputs(misconceptions=[inside, outside, watching, older, disputed]),
        PARAMS,
        NOW,
    )
    assert [item.id for item in stats.misconceptions_resolved] == ["m1"]
    assert [item.id for item in stats.misconceptions_new_confirmed] == ["m3"]
    assert {item.id for item in stats.misconceptions_still_watching} == {"m3", "m4"}


def test_forecast_shift_is_measured_in_days():
    from tests.quack.conftest import make_forecast

    stats = set_stats(
        _inputs(
            forecast_before=make_forecast(ready_by=date(2026, 11, 20)),
            forecast_after=make_forecast(ready_by=date(2026, 11, 1), on_track=True),
        ),
        PARAMS,
        NOW,
    )
    assert stats.ready_by_shift_days == 19
    assert stats.on_track_after is True


def test_stats_words_use_only_numbers_from_the_stats():
    from app.agents.texts import _allowed_numbers, numbers_in

    stats = set_stats(_inputs(), PARAMS, NOW)
    text = stats_words(stats)
    assert "закрыто тем" in text
    assert not numbers_in(text) - _allowed_numbers(stats)


def test_stats_words_never_return_an_empty_string():
    empty = _inputs(
        tasks_answered=0,
        tasks_correct=0,
        mocks_completed=0,
        skills=[],
        misconceptions=[],
    )
    assert stats_words(set_stats(empty, PARAMS, NOW))
