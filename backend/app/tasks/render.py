"""Render template strings — memory-architecture-quack.md §3.1.

- render_stem: substitute {name} from params. If the substituted value is
  negative and preceded by + - * /, wrap in parentheses to avoid `x - -3`.
- render_value: format a sympy value as integer / fraction / decimal.

Source: 20-B1.md §4.2.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from sympy import Integer, Rational, nsimplify, simplify

_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def render_stem(stem: str, params: dict[str, Any], answer: Any = None) -> str:
    """Substitute {name} placeholders.

    Rule for parentheses: if a substituted value is negative and the character
    immediately before '{' is one of + - * /, wrap the value in parentheses.
    answer (if given) is available as {answer}.
    """
    values: dict[str, Any] = dict(params)
    if answer is not None:
        values["answer"] = answer

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            raise KeyError(f"missing param {name!r} in {stem!r}")
        raw = values[name]
        text = _format_raw(raw)
        if text.startswith("-"):
            prefix = stem[: match.start()].rstrip()
            before = prefix[-1] if prefix else ""
            if before in "+-*/":
                return f"({text})"
        return text

    return _PLACEHOLDER.sub(replace, stem)


def render_value(
    value: Any, form: Literal["auto", "fraction", "decimal", "integer"]
) -> str:
    """Format a sympy value.

    Non-sympy values (str, tuple, list) are returned as their str() — they
    cover textual answers from templates like "(3, 2)" or "Infinitely many".
    """
    if isinstance(value, str):
        return value
    if isinstance(value, (tuple, list)):
        return str(value)

    value = simplify(nsimplify(value))

    if form == "integer":
        return str(int(value))
    if form == "fraction":
        return str(value)
    if form == "decimal":
        return _to_decimal(value)
    # auto
    if value.is_Integer:
        return str(value)
    if value.is_Rational:
        return str(value)
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def _format_raw(raw: Any) -> str:
    """Render a raw param for embedding into a stem string."""
    if isinstance(raw, bool):
        return str(raw)
    if isinstance(raw, int):
        return str(raw)
    if isinstance(raw, float):
        return _to_decimal(Rational(str(raw)))
    try:
        if isinstance(raw, Integer):
            return str(raw)
        if isinstance(raw, Rational):
            return str(raw)
        return str(raw)
    except Exception:  # noqa: BLE001
        return str(raw)


def _to_decimal(value: Any) -> str:
    """Rational → decimal string without trailing zeros."""
    if value.is_Integer:
        return str(value)
    if value.is_Rational:
        text = f"{float(value):.10f}".rstrip("0").rstrip(".")
        return text
    return str(value)
