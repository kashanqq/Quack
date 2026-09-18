"""Template rendering — 20-B1.md §4.2, §7 (test_render block)."""

from __future__ import annotations

import pytest
from sympy import Integer, Rational

from app.tasks.render import render_stem, render_value


pytestmark = pytest.mark.phase1


def test_render_stem_simple():
    assert render_stem("|{a}x - {b}| = {c}", {"a": 2, "b": 6, "c": 4}) == "|2x - 6| = 4"


def test_render_stem_negative_after_operator_gets_parentheses():
    # x - (-3), not x - -3
    assert render_stem("x - {b}", {"b": -3}) == "x - (-3)"


def test_render_stem_negative_after_plus_gets_parentheses():
    assert render_stem("{a} + {b}", {"a": 5, "b": -2}) == "5 + (-2)"


def test_render_stem_negative_after_open_paren_no_wrap():
    assert render_stem("({b})", {"b": -3}) == "(-3)"


def test_render_value_fraction():
    assert render_value(Rational(5, 2), "fraction") == "5/2"


def test_render_value_decimal():
    assert render_value(Rational(5, 2), "decimal") == "2.5"


def test_render_value_integer():
    assert render_value(Integer(4), "auto") == "4"


def test_render_value_irrational_auto_three_places():
    # sqrt(2) ≈ 1.414
    from sympy import sqrt

    assert render_value(sqrt(2), "auto") == "1.414"