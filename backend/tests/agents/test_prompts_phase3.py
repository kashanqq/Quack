"""Phase-3 prompts load, carry their version and expose exactly the
placeholders the agents fill (docs/tz/phase3-agents.md §5.2 F22)."""

from __future__ import annotations

import re

import pytest

from app.llm.prompts import load_prompt

pytestmark = pytest.mark.phase3


def _placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{\{(\w+)\}\}", text))


def test_selection_v4_is_the_loaded_selection_prompt():
    prompt = load_prompt("selection")

    assert prompt.version == 4
    assert prompt.extractor_version == "selection_v4"
    assert _placeholders(prompt.text) == {
        "profile",
        "stage",
        "stage_rules",
        "snapshot",
        "knowledge",
        "today",
    }
    assert "этом же ходе" in prompt.text


def test_tutor_v3_is_the_loaded_tutor_prompt():
    prompt = load_prompt("tutor")

    assert prompt.version == 3
    assert prompt.extractor_version == "tutor_v3"
    assert _placeholders(prompt.text) == {"learner_model", "session"}
    assert "даты и требования не называю" in prompt.text.lower()


def test_canon_v1_has_two_sides():
    prompt = load_prompt("canon")

    assert prompt.extractor_version == "canon_v1"
    assert _placeholders(prompt.text) == {"a", "b"}


def test_observer_prompt_is_unchanged_v1():
    assert load_prompt("observer").extractor_version == "observer_v1"
