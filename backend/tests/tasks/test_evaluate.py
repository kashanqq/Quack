"""Safe expression evaluation — 20-B1.md §4.1, §7.

No eval. Whitelist of names only. Any name outside the dictionary → TemplateError.
"""

from __future__ import annotations

import pytest
from sympy import Integer, Rational

from app.tasks.evaluate import (
    TemplateError,
    check_constraints,
    equal_values,
    eval_expr,
    to_canonical,
)

pytestmark = pytest.mark.phase1


def test_eval_expr_simple_fraction():
    assert eval_expr("2*b/a", {"a": 2, "b": 5}) == Rational(5)


def test_eval_expr_parentheses():
    assert eval_expr("(b+c)/a", {"a": 3, "b": 7, "c": 2}) == Rational(3)


def test_eval_expr_rejects_dunder_import():
    with pytest.raises(TemplateError):
        eval_expr("__import__('os')", {})


def test_eval_expr_rejects_open():
    with pytest.raises(TemplateError):
        eval_expr("open('x')", {})


def test_eval_expr_rejects_unknown_name():
    with pytest.raises(TemplateError):
        eval_expr("foo+1", {})


def test_eval_expr_symbolic_sqrt():
    out = eval_expr("sqrt(2)", {})
    assert equal_values(out**2, 2)


def test_check_constraints_true():
    assert check_constraints(["(b + c) % a == 0", "b > c"], {"a": 2, "b": 5, "c": 1})


def test_check_constraints_false():
    assert not check_constraints(["(b + c) % a == 0"], {"a": 2, "b": 5, "c": 2})


def test_check_constraints_division_by_zero_returns_false():
    # a=0 → 1/a → ошибка вычисления, должна вернуть False, не исключение
    assert not check_constraints(["1/a > 0"], {"a": 0})


def test_to_canonical_rational():
    assert to_canonical(Rational(1, 2)) == "1/2"


def test_to_canonical_integer():
    assert to_canonical(Integer(4)) == "4"


def test_equal_values_rational_and_float():
    assert equal_values(Rational(1, 2), 0.5)


def test_equal_values_different():
    assert not equal_values(Rational(1, 2), 0.6)
