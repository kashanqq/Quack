"""T18: the canonical map without Neo4j, and what it refuses to invent (D05)."""

import json
from pathlib import Path

import pytest

from app.sets import static_snapshot
from app.sets.static_snapshot import SnapshotUnavailable

pytestmark = pytest.mark.phase5

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def test_the_checked_in_seed_data_is_a_usable_snapshot():
    exams = static_snapshot.load(DATA_DIR)
    assert set(exams) == {"SAT_MATH", "ENT_MATH"}
    for exam in exams.values():
        assert exam.skills
        assert len(set(exam.order)) == len(exam.order)


def test_prerequisites_always_come_before_what_needs_them():
    for exam in static_snapshot.load(DATA_DIR).values():
        seen: set[str] = set()
        known = set(exam.order)
        for skill in exam.skills:
            for required in skill.requires:
                if required in known:
                    assert required in seen, (
                        f"{skill.skill_id} стоит раньше своей предпосылки {required}"
                    )
            seen.add(skill.skill_id)


def test_the_order_is_the_same_on_every_run():
    first = static_snapshot.load(DATA_DIR)["SAT_MATH"].order
    second = static_snapshot.load(DATA_DIR)["SAT_MATH"].order
    assert first == second


def test_a_missing_snapshot_says_so_instead_of_returning_half_a_map(tmp_path):
    with pytest.raises(SnapshotUnavailable):
        static_snapshot.load(tmp_path)


def test_a_prerequisite_cycle_is_a_data_error_not_a_stable_looking_guess(tmp_path):
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "broken.json").write_text(
        json.dumps(
            {
                "exam": {"id": "X"},
                "areas": [],
                "skills": [
                    {"id": "a", "requires": [{"skill_id": "b"}]},
                    {"id": "b", "requires": [{"skill_id": "a"}]},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SnapshotUnavailable, match="cycle"):
        static_snapshot.load(tmp_path)


def test_sorting_topics_never_adds_or_drops_one():
    class _Topic:
        def __init__(self, skill_id: str) -> None:
            self.skill_id = skill_id

    order = static_snapshot.order_for("SAT_MATH")
    assert order
    topics = [_Topic(order[3]), _Topic(order[0]), _Topic("unknown.skill")]
    sorted_topics = static_snapshot.sort_topics(
        "SAT_MATH", topics, lambda topic: topic.skill_id
    )
    assert [topic.skill_id for topic in sorted_topics] == [
        order[0],
        order[3],
        "unknown.skill",
    ]


def test_an_unknown_exam_leaves_the_order_alone():
    assert static_snapshot.order_for("NOT_AN_EXAM") == ()
