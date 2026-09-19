"""Postcheck — sweep an assistant reply's numbers and dates against tool
results (docs/tz/30-B2.md §4.4, product-logic §5.0, tech-stack §4.3).

product-logic §5.0's rule is that any number, date or rule in a reply must
come from a tool result, with its source next to it — the model has no
right to state a figure the tools never returned. `check_facts` is the
mechanical half of that: it only compares text against tool output: it
does not know *why* a number is wrong, only that it wasn't returned.

Phase 3 (docs/tz/phase3-agents.md §3.6, F17): both agents call it after the
tool loop and before `done`. `scope="exam_facts"` is the tutor's narrower
sweep (dates, percents, and numbers only in sentences about the exam or
admission — a tutor's own algebra is not a dataset fact); `extra_values`
adds what the student said and what the system prompt showed as
authoritative; `max_questions` is the selection assistant's "≤ 2 questions".

This module must stay free of I/O: no app.db, app.graph, app.llm,
sqlalchemy, neo4j, redis or openai imports — only the standard library,
pydantic, and app.schemas. A separate B3 layering test (00-contracts §4.4)
enforces this by import.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.schemas.chat import ToolResult

# Years that read as a bare number in Russian prose ("в 2027 году") rather
# than a fact anyone would look up — excluded from number-checking entirely
# so that phrase doesn't false-positive as an uncited figure. Only applies
# to a plain, unformatted integer standing alone; a year that is part of a
# recognized date (§_extract_dates) is never treated as a separate number
# in the first place.
_STANDALONE_YEAR_RANGE = range(2024, 2031)

_NUMBER_RE = re.compile(
    r"(?<!\d)(?P<num>\d{1,3}(?:[  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"(?P<pct>\s*%)?(?!\d)"
)

# Russian month names, both the genitive form that follows a day number
# ("12 мая", "15 декабря") and the nominative/title form that can appear
# on its own ("май"). Only used inside the day+month pattern below — a bare
# nominative month name with no day number next to it is not treated as a
# date, since that would false-positive on ordinary prose ("май — тёплый
# месяц") that isn't naming a deadline at all.
_MONTHS: dict[str, int] = {
    "январь": 1, "января": 1,
    "февраль": 2, "февраля": 2,
    "март": 3, "марта": 3,
    "апрель": 4, "апреля": 4,
    "май": 5, "мая": 5,
    "июнь": 6, "июня": 6,
    "июль": 7, "июля": 7,
    "август": 8, "августа": 8,
    "сентябрь": 9, "сентября": 9,
    "октябрь": 10, "октября": 10,
    "ноябрь": 11, "ноября": 11,
    "декабрь": 12, "декабря": 12,
}  # fmt: skip

_MONTH_ALT = "|".join(_MONTHS)
_DATE_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DATE_DOTTED_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
_DATE_RU_YEAR_RE = re.compile(
    rf"\b(\d{{1,2}})\s+\b(?:{_MONTH_ALT})\b\s+(\d{{4}})\b", re.IGNORECASE
)
_DATE_RU_NOYEAR_RE = re.compile(
    rf"\b(\d{{1,2}})\s+\b(?:{_MONTH_ALT})\b(?!\s+\d{{4}})", re.IGNORECASE
)
# Separate capturing-group pattern to recover which month matched, reused
# by both RU regexes above (re can't easily reuse a named alternative
# across two match attempts otherwise).
_MONTH_WORD_RE = re.compile(rf"\b({_MONTH_ALT})\b", re.IGNORECASE)


# A number in the tutor's reply is a *fact* only inside a sentence about the
# exam or admission (§3.6); everywhere else it is the maths of the task.
_EXAM_FACT_MARKERS = re.compile(
    r"балл|заданий|задания|минут|модул|секци|раздел|шкал|максимум|проходн|"
    r"порог|дедлайн|регистрац|подач|стоимост|цена|тенге|доллар|евро|"
    r"CHF|USD|EUR|KZT",
    re.IGNORECASE,
)
_SENTENCE_RE = re.compile(r"[^.!?\n]+(?:[.!?]+|$)")
# Characters that make a number part of an expression rather than a fact:
# "x = 3", "2x − 6", "3/4".
_MATH_NEIGHBOURS = set("=+−-*/^<>≤≥×÷") | set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
)

Scope = Literal["all", "exam_facts"]


class PostcheckResult(BaseModel):
    ok: bool
    mismatches: list[str]
    questions: int = 0


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _month_from_match(match_text: str) -> int | None:
    found = _MONTH_WORD_RE.search(match_text)
    if found is None:
        return None
    return _MONTHS[found.group(1).lower()]


def _extract_dates(
    text: str,
) -> list[tuple[tuple[int, int], date | tuple[int, int]]]:
    """Find dates in `text`. Each result pairs the matched span with either
    a `date` (year known) or a `(month, day)` tuple (year omitted, to be
    compared by day and month only).
    """
    found: list[tuple[tuple[int, int], date | tuple[int, int]]] = []
    spans: list[tuple[int, int]] = []

    for m in _DATE_ISO_RE.finditer(text):
        year, month, day = (int(g) for g in m.groups())
        try:
            value = date(year, month, day)
        except ValueError:
            continue
        spans.append(m.span())
        found.append((m.span(), value))

    for m in _DATE_DOTTED_RE.finditer(text):
        day, month, year = (int(g) for g in m.groups())
        try:
            value = date(year, month, day)
        except ValueError:
            continue
        spans.append(m.span())
        found.append((m.span(), value))

    for m in _DATE_RU_YEAR_RE.finditer(text):
        day = int(m.group(1))
        month = _month_from_match(m.group(0))
        year = int(m.group(2))
        if month is None:
            continue
        try:
            value = date(year, month, day)
        except ValueError:
            continue
        spans.append(m.span())
        found.append((m.span(), value))

    for m in _DATE_RU_NOYEAR_RE.finditer(text):
        span = m.span()
        if any(_overlaps(span, s) for s in spans):
            continue
        day = int(m.group(1))
        month = _month_from_match(m.group(0))
        if month is None:
            continue
        spans.append(span)
        found.append((span, (month, day)))

    return found


def _extract_numbers(
    text: str, exclude_spans: list[tuple[int, int]]
) -> list[tuple[float, bool, tuple[int, int]]]:
    """(value, is_percent, span) of every checkable number in `text`."""
    numbers: list[tuple[float, bool, tuple[int, int]]] = []
    for m in _NUMBER_RE.finditer(text):
        span = m.span()
        if any(_overlaps(span, s) for s in exclude_spans):
            continue
        raw = m.group("num")
        has_group = " " in raw or " " in raw
        has_decimal = "." in raw or "," in raw
        has_percent = m.group("pct") is not None
        value = float(raw.replace(" ", "").replace(" ", "").replace(",", "."))
        if (
            not has_group
            and not has_decimal
            and not has_percent
            and value.is_integer()
            and int(value) in _STANDALONE_YEAR_RANGE
        ):
            continue
        numbers.append((value, has_percent, span))
    return numbers


def _fact_sentence_spans(text: str) -> list[tuple[int, int]]:
    return [
        m.span()
        for m in _SENTENCE_RE.finditer(text)
        if _EXAM_FACT_MARKERS.search(m.group(0))
    ]


def _is_math(text: str, span: tuple[int, int]) -> bool:
    """The number sits in an expression: its nearest non-space neighbour is
    an operator or a variable."""
    before = text[: span[0]].rstrip()
    after = text[span[1] :].lstrip()
    return bool(
        (before and before[-1] in _MATH_NEIGHBOURS)
        or (after and after[0] in _MATH_NEIGHBOURS)
    )


def _walk(value: object) -> list[object]:
    if isinstance(value, dict):
        leaves: list[object] = []
        for v in value.values():
            leaves.extend(_walk(v))
        return leaves
    if isinstance(value, list):
        leaves = []
        for v in value:
            leaves.extend(_walk(v))
        return leaves
    return [value]


def _collect_result_values(
    tool_results: list[ToolResult],
) -> tuple[list[float], set[date]]:
    numbers: list[float] = []
    dates: set[date] = set()
    for result in tool_results:
        for leaf in _walk(result.data):
            if isinstance(leaf, bool):
                continue
            if isinstance(leaf, date):
                dates.add(leaf)
            elif isinstance(leaf, int | float):
                numbers.append(float(leaf))
            elif isinstance(leaf, str):
                try:
                    dates.add(date.fromisoformat(leaf))
                except ValueError:
                    pass
    return numbers, dates


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return str(value)


def _format_date(value: date | tuple[int, int]) -> str:
    if isinstance(value, date):
        return value.isoformat()
    month, day = value
    return f"{month:02d}-{day:02d}"


def check_facts(
    text: str,
    tool_results: list[ToolResult],
    *,
    scope: Scope = "all",
    extra_values: Iterable[float | date] = (),
    max_questions: int | None = None,
) -> PostcheckResult:
    """Check that every number/date in `text` is backed by `tool_results`.

    Numbers: integers and decimals, including space-grouped thousands
    (``1 500``), currency-adjacent (``1 500 CHF``) and percentages — matched
    with formatting stripped, so ``1500`` and ``1 500`` are the same value;
    a percentage also matches its fraction (``85%`` ↔ ``0.85``).
    A bare, unformatted number from 2024-2030 is never checked (a stray
    "в 2027 году" would otherwise false-positive against every tool call).

    Dates: ``12 мая 2027``, ``12.05.2027``, ``2027-05-12``, and ``15
    декабря`` (year omitted — matched against results by day and month
    only, ignoring year).

    `tool_results` values are collected recursively (dicts and lists to any
    depth); string values that parse as ISO dates are normalized to `date`
    before comparison. A result with an `error` contributes nothing.
    `extra_values` are authoritative too (profile fields shown to the model,
    numbers the student typed this turn). Empty `tool_results` with numbers or
    dates in `text` is a mismatch (a figure stated without ever calling a
    tool); text with no numbers or dates is always `ok=True`.

    `scope="exam_facts"` checks every date and every percentage, and other
    numbers only in sentences that talk about the exam or admission, skipping
    numbers inside expressions. `max_questions` fails a reply with more
    question marks than that.
    """
    dates_in_text = _extract_dates(text)
    date_spans = [span for span, _ in dates_in_text]
    numbers_in_text = _extract_numbers(text, date_spans)
    if scope == "exam_facts":
        fact_spans = _fact_sentence_spans(text)
        numbers_in_text = [
            (value, pct, span)
            for value, pct, span in numbers_in_text
            if pct
            or (
                any(_overlaps(span, s) for s in fact_spans) and not _is_math(text, span)
            )
        ]

    result_numbers, result_dates = _collect_result_values(
        [r for r in tool_results if r.error is None]
    )
    for extra in extra_values:
        if isinstance(extra, date):
            result_dates.add(extra)
        elif isinstance(extra, int | float) and not isinstance(extra, bool):
            result_numbers.append(float(extra))

    mismatches: list[str] = []

    for value, is_percent, _span in numbers_in_text:
        candidates = [value, value / 100] if is_percent else [value]
        if not any(
            abs(candidate - rv) < 1e-6
            for candidate in candidates
            for rv in result_numbers
        ):
            mismatches.append(_format_number(value))

    for _span, value in dates_in_text:
        if isinstance(value, date):
            matched = value in result_dates
        else:
            month, day = value
            matched = any(d.month == month and d.day == day for d in result_dates)
        if not matched:
            mismatches.append(_format_date(value))

    questions = text.count("?")
    if max_questions is not None and questions > max_questions:
        mismatches.append(f"questions>{max_questions}")

    return PostcheckResult(
        ok=not mismatches, mismatches=mismatches, questions=questions
    )


def numbers_and_dates(text: str) -> list[float | date]:
    """Every number and full date in free text — what the student said this
    turn, passed back as `extra_values`."""
    dates = _extract_dates(text)
    values: list[float | date] = [
        value for _span, value in dates if isinstance(value, date)
    ]
    values.extend(
        value for value, _pct, _span in _extract_numbers(text, [s for s, _ in dates])
    )
    return values
