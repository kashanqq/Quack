"""Prompt loader: version selection, rendering, missing files
(docs/tz/30-B2.md §4.2, §6, tests/llm/test_prompts.py)."""

from __future__ import annotations

import pytest

from app.llm import prompts as prompts_module
from app.llm.prompts import Prompt, load_prompt

pytestmark = pytest.mark.phase1


def test_load_prompt_picks_highest_version(tmp_path, monkeypatch):
    monkeypatch.setattr(prompts_module, "_PROMPTS_DIR", tmp_path)
    (tmp_path / "x_v1.md").write_text("old", encoding="utf-8")
    (tmp_path / "x_v2.md").write_text("new", encoding="utf-8")

    prompt = load_prompt("x")

    assert prompt.version == 2
    assert prompt.text == "new"


def test_render_substitutes_and_raises_key_error_for_missing_variable():
    prompt = Prompt(name="y", version=1, text="value is {{a}}")

    assert prompt.render(a=1) == "value is 1"

    with pytest.raises(KeyError):
        prompt.render()


def test_load_prompt_missing_file_raises_file_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(prompts_module, "_PROMPTS_DIR", tmp_path)

    with pytest.raises(FileNotFoundError):
        load_prompt("does_not_exist")
