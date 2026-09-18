"""Синонимы направлений — «информатика» и «Computer Science» одно и то же."""

from __future__ import annotations

import pytest

from app.matching.directions import canonical_direction, direction_matches

pytestmark = pytest.mark.phase1


@pytest.mark.parametrize(
    ("wanted", "program"),
    [
        ("информатика", "Computer Science"),
        ("Информатика", "BSc Computer Science and Engineering"),
        ("ИТ", "Information Technology"),
        ("computer science", "компьютерные науки"),
        ("анализ данных", "Data Science"),
        ("экономика", "Economics and Finance"),
    ],
)
def test_synonyms_match(wanted, program):
    assert direction_matches(wanted, program)


@pytest.mark.parametrize(
    ("wanted", "program"),
    [
        ("информатика", "Mathematics"),
        ("медицина", "Law"),
        ("физика", "Business Administration"),
    ],
)
def test_different_directions_do_not_match(wanted, program):
    assert not direction_matches(wanted, program)


def test_empty_wanted_matches_everything():
    assert direction_matches(None, "Computer Science")
    assert direction_matches("", "Computer Science")


def test_unknown_direction_falls_back_to_substring():
    assert direction_matches("astrobiology", "MSc Astrobiology")
    assert not direction_matches("astrobiology", "MSc Oceanography")
    assert canonical_direction("astrobiology") is None
