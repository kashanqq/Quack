"""Weights and tiers from memory-architecture-quack.md §4.3, §8.1.

Numbers come from 20-B1.md §7 (test_weights.py block).
"""

from __future__ import annotations

import pytest

from app.knowledge.weights import base_weight, evidence_weight, is_strong, tier_for

pytestmark = pytest.mark.phase1


# --- tier_for ---


def test_tier_for_mock_is_1():
    assert tier_for("mock", "mock_set") == 1


def test_tier_for_diagnostic_is_1():
    assert tier_for("diagnostic", "diagnostic") == 1


def test_tier_for_task_in_topic_is_2():
    assert tier_for("task", "topic") == 2


def test_tier_for_chat_solution_step_is_2():
    assert tier_for("chat", "chat", kind="solution_step") == 2


def test_tier_for_chat_applied_is_3():
    assert tier_for("chat", "chat", kind="applied") == 3


def test_tier_for_self_report_is_3():
    assert tier_for("self_report", None) == 3


# --- base_weight — every row from §4.3 ---


@pytest.mark.parametrize(
    ("source", "mode", "kind", "expected"),
    [
        ("mock", "mock_set", None, 1.0),
        ("mock", "mock_topic", None, 1.0),
        ("mock", "mock_misconception", None, 1.0),
        ("diagnostic", "diagnostic", None, 1.0),
        ("task", "topic", None, 0.8),
        ("chat", "chat", "task_in_chat", 0.8),
        ("chat", "chat", "solution_step", 0.7),
        ("chat", "chat", "avoided_trap", 0.7),
        ("chat", "chat", "confusion", 0.6),
        ("chat", "chat", "applied", 0.5),
        ("chat", "chat", "question", 0.2),
        ("self_report", None, None, 0.1),
    ],
)
def test_base_weight_table(source, mode, kind, expected):
    assert base_weight(source, mode, kind) == pytest.approx(expected)


# --- evidence_weight modifiers ---


def test_evidence_weight_seen_template_multiplier():
    # task in topic, base 0.8, seen_before=True → *0.8 = 0.64
    w = evidence_weight("task", "topic", None, seen_before=True, matched=True)
    assert w == pytest.approx(0.64)


def test_evidence_weight_unmatched_multiplier():
    # 0.8 * 0.7 = 0.56
    w = evidence_weight("task", "topic", None, seen_before=False, matched=False)
    assert w == pytest.approx(0.56)


def test_evidence_weight_both_multipliers():
    # 0.8 * 0.8 * 0.7 = 0.448
    w = evidence_weight("task", "topic", None, seen_before=True, matched=False)
    assert w == pytest.approx(0.448)


# --- is_strong ---


def test_is_strong_tier_1_and_2():
    assert is_strong(1) is True
    assert is_strong(2) is True
    assert is_strong(3) is False
