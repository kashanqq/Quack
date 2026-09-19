"""ObservationOut schema (docs/tz/30-B2.md §5.4, memory-architecture §8.1,
tests/agents/test_observer_schema.py)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.agents.observer import Observation, ObservationOut

pytestmark = pytest.mark.phase1

# The ten-observation example from memory-architecture-quack.md §8.1,
# with its "…" placeholders filled with plausible ids/text.
_EXAMPLE_OBSERVATIONS = [
    {
        "kind": "solution_step",
        "outcome": "incorrect",
        "skill_id": "sat.alg.abs_value_eq",
        "misconception_id": "lib.abs_single_branch",
        "summary": "рассмотрел только ветвь 2x-6=4, второй ветви не увидел",
        "event_ids": [4420],
        "confidence": 0.9,
    },
    {
        "kind": "solution_step",
        "outcome": "correct",
        "skill_id": "sat.alg.linear_eq",
        "summary": "верно решил 2x-6=4",
        "event_ids": [4420],
        "confidence": 0.95,
    },
    {
        "kind": "task_in_chat",
        "outcome": "incorrect",
        "instance_id": "ti_88123",
        "answer": "A",
        "event_ids": [4426],
        "confidence": 1.0,
    },
    {
        "kind": "applied",
        "skill_id": "sat.alg.linear_eq",
        "summary": "применил перенос слагаемых верно",
        "event_ids": [4422],
        "confidence": 0.8,
    },
    {
        "kind": "confusion",
        "skill_id": "sat.alg.abs_value_eq",
        "summary": "не понимает, зачем два случая",
        "event_ids": [4420],
        "confidence": 0.85,
    },
    {
        "kind": "question",
        "skill_id": "sat.alg.abs_value_eq",
        "summary": "спросил, почему модуль даёт два корня",
        "event_ids": [4420],
        "confidence": 0.8,
    },
    {
        "kind": "avoided_trap",
        "skill_id": "sat.alg.abs_value_eq",
        "misconception_id": "lib.abs_single_branch",
        "summary": "раскрыл обе ветви модуля",
        "event_ids": [4430],
        "confidence": 0.85,
    },
    {
        "kind": "root_hint",
        "skill_id": "sat.alg.abs_value_eq",
        "root_skill_id": "sat.alg.linear_ineq",
        "summary": "репетитор указал на неравенство, ученик согласился",
        "event_ids": [4421, 4422],
        "confidence": 0.7,
    },
    {
        "kind": "proposed_misconception",
        "skill_id": "sat.alg.abs_value_eq",
        "name": "abs_ignores_negative_branch",
        "description": "решает |x|=a как x=a, не рассматривая x=-a",
        "error_class": "conceptual",
        "event_ids": [4420],
        "confidence": 0.7,
    },
    {
        "kind": "pace_signal",
        "signal": "asked_to_slow_down",
        "event_ids": [4423],
    },
]


def test_memory_architecture_example_validates_whole():
    result = ObservationOut(observations=_EXAMPLE_OBSERVATIONS)

    assert len(result.observations) == 10


@pytest.mark.parametrize(
    "kind,missing_field",
    [
        ("solution_step", "skill_id"),
        ("task_in_chat", "instance_id"),
        ("root_hint", "root_skill_id"),
        ("proposed_misconception", "error_class"),
    ],
)
def test_kind_specific_required_fields_are_enforced(kind, missing_field):
    base = next(o for o in _EXAMPLE_OBSERVATIONS if o["kind"] == kind)
    incomplete = {k: v for k, v in base.items() if k != missing_field}

    with pytest.raises(ValidationError):
        Observation(**incomplete)


def test_confidence_out_of_range_and_overlong_summary_are_rejected():
    base = next(o for o in _EXAMPLE_OBSERVATIONS if o["kind"] == "solution_step")

    with pytest.raises(ValidationError):
        Observation(**{**base, "confidence": 1.2})

    with pytest.raises(ValidationError):
        Observation(**{**base, "summary": "x" * 301})
