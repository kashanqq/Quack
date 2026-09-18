"""Phase-3 prompt drafts load and carry the version from their filename
(30-B2-phase2.md §4, §7)."""

from __future__ import annotations

import pytest

from app.llm.prompts import load_prompt

pytestmark = pytest.mark.phase2


def test_selection_v3_is_the_loaded_selection_prompt():
    prompt = load_prompt("selection")

    assert prompt.version == 3
    assert prompt.extractor_version == "selection_v3"
    assert "<learner_model>" not in prompt.text


def test_tutor_v2_is_the_loaded_tutor_prompt():
    prompt = load_prompt("tutor")

    assert prompt.version == 2
    assert prompt.extractor_version == "tutor_v2"
    assert "{{learner_model}}" in prompt.text
