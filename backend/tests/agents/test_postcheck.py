"""check_facts against numbers/dates in tool results (docs/tz/30-B2.md §4.4,
§6, tests/agents/test_postcheck.py)."""

from __future__ import annotations

import pytest

from app.agents.postcheck import check_facts
from app.schemas.chat import ToolResult

pytestmark = pytest.mark.phase1


def _result(data: object) -> ToolResult:
    return ToolResult(type="tool_result", tool="t", call_id="c1", data=data)


def test_number_present_in_tool_results_is_ok():
    result = check_facts(
        "Стоимость 1 500 CHF в год", [_result({"tuition_per_year": 1500})]
    )

    assert result.ok
    assert result.mismatches == []


def test_number_absent_from_tool_results_is_a_mismatch():
    result = check_facts("Тариф 1450", [_result({"other": 999})])

    assert not result.ok
    assert result.mismatches == ["1450"]


def test_dates_match_by_value_but_not_when_different():
    matching = check_facts(
        "подача до 15 декабря 2026", [_result({"date": "2026-12-15"})]
    )
    mismatching = check_facts(
        "подача до 15 декабря 2026", [_result({"date": "2026-12-01"})]
    )

    assert matching.ok
    assert not mismatching.ok


def test_bare_year_in_prose_is_not_checked_as_a_number():
    result = check_facts("в 2027 году", [])

    assert result.ok


def test_text_without_numbers_or_dates_is_always_ok():
    result = check_facts("Программа подходит по профилю.", [])

    assert result.ok


def test_number_with_empty_tool_results_is_a_mismatch():
    result = check_facts("Стоимость 1500", [])

    assert not result.ok


# --- phase 3 (docs/tz/phase3-agents.md §3.6, §6.5) ---


@pytest.mark.phase3
def test_extra_values_from_profile_pass():
    assert check_facts("бюджет 5000", [], extra_values=[5000]).ok


@pytest.mark.phase3
def test_history_numbers_not_authoritative():
    assert not check_facts("1 500 CHF", [], extra_values=[3000]).ok


@pytest.mark.phase3
def test_scope_exam_facts_keyword_sentences_only():
    result = check_facts("В секции 22 задания, а x = 3", [], scope="exam_facts")
    assert result.mismatches == ["22"]


@pytest.mark.phase3
def test_scope_exam_facts_dates_and_percents_always():
    assert not check_facts("подача до 15 декабря", [], scope="exam_facts").ok
    assert not check_facts("ты знаешь на 55%", [], scope="exam_facts").ok
    assert check_facts("x = 5 или x = 1", [], scope="exam_facts").ok


@pytest.mark.phase3
def test_max_questions():
    result = check_facts("Что? Где? Когда?", [], max_questions=2)
    assert not result.ok
    assert result.questions == 3
    assert "questions>2" in result.mismatches
    assert check_facts("Что? Где?", [], max_questions=2).ok


@pytest.mark.phase3
def test_percent_matches_fraction():
    assert check_facts("покрытие 85%", [_result({"coverage": 0.85})]).ok


@pytest.mark.phase3
def test_error_results_give_no_values():
    failed = ToolResult(
        type="tool_result", tool="t", call_id="c1", data={"x": 1500}, error="boom"
    )
    assert not check_facts("Стоимость 1500", [failed]).ok
