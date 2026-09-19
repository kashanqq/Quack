"""assemble_sets — memory-architecture §10.1.

Numbers from 20-B1-phase2.md §8 (tests/sets/test_assemble.py).
"""

from __future__ import annotations

from datetime import date

import pytest

from app.config import KnowledgeParams
from app.schemas.sets import SetOut, SetProgress
from app.sets.assemble import SetPlan, assemble_sets
from app.sets.queue import QueueItem

pytestmark = pytest.mark.phase1

PARAMS = KnowledgeParams()
TODAY = date(2026, 9, 18)


def _item(
    skill_id: str,
    *,
    need: float = 1.0,
    gap: float = 0.5,
    is_check: bool = False,
    exam_id: str = "SAT_MATH",
) -> QueueItem:
    return QueueItem(
        skill_id=skill_id,
        exam_id=exam_id,  # type: ignore[arg-type]
        need=need,
        urgency=1.5,
        gap=gap,
        is_root=False,
        is_check=is_check,
    )


# --- basic partitioning ---


def test_seven_skills_set_size_three_gives_three_sets():
    queue = [_item(f"skill{i}", need=10 - i) for i in range(7)]
    plans = assemble_sets(
        queue,
        effort={},
        hours_per_week=10,
        next_test_date=None,
        misc_states=[],
        current=None,
        done_skill_ids=set(),
        params=PARAMS,
        today=TODAY,
    )
    assert len(plans) == 3
    assert len(plans[0].skill_ids) == 3
    assert len(plans[1].skill_ids) == 3
    assert len(plans[2].skill_ids) == 1


def test_small_queue_single_set():
    queue = [_item("a")]
    plans = assemble_sets(
        queue,
        effort={},
        hours_per_week=10,
        next_test_date=None,
        misc_states=[],
        current=None,
        done_skill_ids=set(),
        params=PARAMS,
        today=TODAY,
    )
    assert len(plans) == 1
    assert plans[0].skill_ids == ["a"]


# --- checks don't count as topics ---


def test_unchecked_skills_follow_known_topics():
    queue = [
        _item("a", is_check=False),
        _item("b", is_check=True),  # проверка
        _item("c", is_check=False),
        _item("d", is_check=False),
    ]
    plans = assemble_sets(
        queue,
        effort={},
        hours_per_week=10,
        next_test_date=None,
        misc_states=[],
        current=None,
        done_skill_ids=set(),
        params=PARAMS,
        today=TODAY,
    )
    # set_size=3: известные темы a, c, d — первым сетом; непроверенный b не
    # теряется, а уходит следующим сетом (у нового ученика иначе нет сетов)
    assert [p.skill_ids for p in plans] == [["a", "c", "d"], ["b"]]
    assert all(p.checks == [] for p in plans)


# --- deadlines ---


def test_deadline_from_effort_and_hours():
    # gap=0.5, effort=4 → часы 2.0; hours_per_week=10 → 0.2 недели → 1.4 дня → ceil 2
    queue = [_item("a", gap=0.5)]
    plans = assemble_sets(
        queue,
        effort={"a": 4.0},
        hours_per_week=10,
        next_test_date=None,
        misc_states=[],
        current=None,
        done_skill_ids=set(),
        params=PARAMS,
        today=TODAY,
    )
    assert len(plans) == 1
    from datetime import timedelta

    assert plans[0].deadline == TODAY + timedelta(days=2)


def test_deadline_not_after_test_minus_consolidation():
    # hours_per_week маленький, а тест близко — дедлайн упрётся в потолок
    queue = [_item("a", gap=0.9)]
    test_date = TODAY + __import__("datetime").timedelta(days=30)
    plans = assemble_sets(
        queue,
        effort={"a": 100.0},
        hours_per_week=1,
        next_test_date=test_date,
        misc_states=[],
        current=None,
        done_skill_ids=set(),
        params=PARAMS,
        today=TODAY,
    )
    # не позже test_date − consolidation_days (7)
    from datetime import timedelta

    limit = test_date - timedelta(days=PARAMS.consolidation_days)
    # regular-сеты не позже лимита
    regular = [p for p in plans if p.kind != "consolidation"]
    if regular:
        assert regular[-1].deadline <= limit


# --- consolidation ---


def test_consolidation_last_when_test_present():
    queue = [_item(f"s{i}") for i in range(4)]
    test_date = TODAY + __import__("datetime").timedelta(days=60)
    plans = assemble_sets(
        queue,
        effort={},
        hours_per_week=10,
        next_test_date=test_date,
        misc_states=[],
        current=None,
        done_skill_ids=set(),
        params=PARAMS,
        today=TODAY,
    )
    assert plans[-1].kind == "consolidation"


def test_no_consolidation_without_test():
    queue = [_item("a"), _item("b"), _item("c")]
    plans = assemble_sets(
        queue,
        effort={},
        hours_per_week=10,
        next_test_date=None,
        misc_states=[],
        current=None,
        done_skill_ids=set(),
        params=PARAMS,
        today=TODAY,
    )
    assert all(p.kind != "consolidation" for p in plans)


# --- current is respected ---


def test_current_skills_excluded_from_new_plans():
    current = SetOut(
        id=__import__("uuid").uuid4(),
        exam_id="SAT_MATH",
        area_ids=["area.sat.algebra"],
        status="current",
        kind="regular",
        position=0,
        deadline=TODAY,
        reason="...",
        topics=[
            __import__("app.schemas.sets", fromlist=["TopicOut"]).TopicOut(
                skill_id="a",
                name="a",
                kind="topic",
                position=0,
                status="open",
                level="weak",
                is_root=False,
                misconception_labels=[],
                subtitle=None,
            )
        ],
        progress=SetProgress(
            topics_closed=0, topics_total=1, tasks_answered=0, tasks_correct=0
        ),
    )
    queue = [_item("a"), _item("b"), _item("c")]
    plans = assemble_sets(
        queue,
        effort={},
        hours_per_week=10,
        next_test_date=None,
        misc_states=[],
        current=current,
        done_skill_ids=set(),
        params=PARAMS,
        today=TODAY,
    )
    for p in plans:
        assert "a" not in p.skill_ids  # current исключён


# --- return type ---


def test_returns_list_of_set_plans():
    queue = [_item("a")]
    plans = assemble_sets(
        queue,
        effort={},
        hours_per_week=10,
        next_test_date=None,
        misc_states=[],
        current=None,
        done_skill_ids=set(),
        params=PARAMS,
        today=TODAY,
    )
    assert isinstance(plans, list)
    assert isinstance(plans[0], SetPlan)


def test_empty_queue_returns_empty():
    plans = assemble_sets(
        [],
        effort={},
        hours_per_week=10,
        next_test_date=None,
        misc_states=[],
        current=None,
        done_skill_ids=set(),
        params=PARAMS,
        today=TODAY,
    )
    assert plans == []
