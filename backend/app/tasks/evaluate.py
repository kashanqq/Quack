"""Safe evaluation of template expressions — memory-architecture-quack.md §3.1.

No eval(), no exec(). Only sympy.parse_expr with a whitelist of names
(ALLOWED_NAMES + template params). Any name outside the whitelist → TemplateError.

Source: 20-B1.md §4.1.
"""

from __future__ import annotations

from sympy import (
    Abs,
    E,
    Float,
    Integer,
    Max,
    Min,
    Rational,
    ceiling,
    cos,
    exp,
    factorial,
    floor,
    gcd,
    lcm,
    log,
    nsimplify,
    pi,
    simplify,
    sin,
    sqrt,
    sympify,
    tan,
)
from sympy.parsing.sympy_parser import parse_expr, standard_transformations


class TemplateError(Exception):
    """Raised when a template expression is invalid, unsafe, or yields no value."""


ALLOWED_NAMES: dict[str, object] = {
    # functions
    "sqrt": sqrt,
    "Abs": Abs,
    "Rational": Rational,
    "floor": floor,
    "ceiling": ceiling,
    "sin": sin,
    "cos": cos,
    "tan": tan,
    "log": log,
    "exp": exp,
    "Min": Min,
    "Max": Max,
    "gcd": gcd,
    "lcm": lcm,
    "factorial": factorial,
    # constants
    "pi": pi,
    "E": E,
    # number constructors used by auto_number transformation
    "Integer": Integer,
    "Float": Float,
}


def eval_expr(expr: str, params: dict[str, object]):
    """Parse and evaluate a template expression.

    params are sympified and merged into local_dict alongside ALLOWED_NAMES.
    Raises TemplateError on any unknown name, syntax error, or unsafe construct.
    """
    sympified_params = {k: sympify(v) for k, v in params.items()}
    local_dict: dict[str, object] = {**ALLOWED_NAMES, **sympified_params}
    try:
        return parse_expr(
            expr,
            local_dict=local_dict,
            global_dict={},
            transformations=standard_transformations,
        )
    except Exception as exc:  # noqa: BLE001 — wrap everything as TemplateError
        raise TemplateError(f"cannot evaluate {expr!r}: {exc}") from exc


def check_constraints(constraints: list[str], params: dict[str, object]) -> bool:
    """Evaluate all constraints; True iff every one is truthy.

    Division by zero and other runtime errors → False, not an exception.
    """
    for c in constraints:
        try:
            value = eval_expr(c, params)
            if not bool(value):
                return False
        except (TemplateError, TypeError, ValueError):
            return False
    return True


def to_canonical(value) -> str:
    """Canonical string for comparing answers: nsimplify → str(simplify(...))."""
    return str(simplify(nsimplify(value)))


def equal_values(a, b) -> bool:
    """True iff a and b are mathematically equal."""
    try:
        return bool(simplify(sympify(a) - sympify(b)) == 0)
    except Exception:  # noqa: BLE001
        return False
