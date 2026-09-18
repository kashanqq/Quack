"""gen_templates.py skeleton (30-B2-phase2.md §0.1 п.2, §5)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from app.llm.fake import FakeLLMClient
from app.schemas.tasks import TaskTemplateSpec

pytestmark = pytest.mark.phase2

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "gen_templates.py"

_VALID_TEMPLATE = {
    "id": "tpl.sat.alg.test_valid",
    "exam_id": "SAT_MATH",
    "type": "numeric",
    "difficulty": 1,
    "skill_id": "sat.alg.slope_lines",
    "tags": ["test"],
    "time_reference_sec": 30,
    "kind": "template",
    "params": {"a": {"range": [1, 5]}},
    "constraints": [],
    "stem": "Чему равно {a} + 1?",
    "correct": "a + 1",
    "distractors": [],
    "solution": ["{a} + 1 = {answer}"],
}

# Invalid by construction: the first distractor is the same expression as
# `correct`, so validate_template's symbolic check ("distractors collapse")
# rejects it deterministically, with no dependence on seeded randomness.
_INVALID_TEMPLATE = {
    "id": "tpl.sat.alg.test_invalid",
    "exam_id": "SAT_MATH",
    "type": "mcq4",
    "difficulty": 1,
    "skill_id": "sat.alg.slope_lines",
    "tags": ["test"],
    "time_reference_sec": 30,
    "kind": "template",
    "params": {"a": {"range": [1, 5]}},
    "constraints": [],
    "stem": "Чему равно {a}?",
    "correct": "a",
    "distractors": [
        {"expr": "a", "misconception_id": None},
        {"expr": "a+1", "misconception_id": None},
        {"expr": "a+2", "misconception_id": None},
    ],
    "solution": ["Ответ — {a}."],
}


def _load_module():
    spec = importlib.util.spec_from_file_location("gen_templates", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dry_run_prints_prompt_with_skill_and_misconception_and_writes_nothing(
    tmp_path,
):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--exam",
            "SAT_MATH",
            "--area",
            "alg",
            "--out",
            str(tmp_path),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stderr
    assert "math.alg.abs_value_eq" in result.stdout
    assert "lib.abs_single_branch" in result.stdout
    assert list(tmp_path.iterdir()) == []


class _FakeRedis:
    @classmethod
    def from_url(cls, url):
        return cls()

    async def aclose(self):
        return None


async def test_generation_drops_invalid_template_and_writes_only_the_valid_one(
    monkeypatch, tmp_path, capsys
):
    gen_templates = _load_module()

    valid_spec = TaskTemplateSpec.model_validate(_VALID_TEMPLATE)
    invalid_spec = TaskTemplateSpec.model_validate(_INVALID_TEMPLATE)
    script = [gen_templates.GeneratedTemplates(templates=[valid_spec, invalid_spec])]
    fake_llm = FakeLLMClient(script)

    monkeypatch.setattr(gen_templates, "LLMClient", lambda settings, redis: fake_llm)
    monkeypatch.setattr(gen_templates, "Redis", _FakeRedis)

    exit_code = await gen_templates.run(
        [
            "--exam",
            "SAT_MATH",
            "--area",
            "alg",
            "--skill",
            "sat.alg.slope_lines",
            "--n",
            "1",
            "--out",
            str(tmp_path),
            "--no-seed-validate",
        ]
    )

    assert exit_code == 0
    written = list(tmp_path.iterdir())
    assert [p.name for p in written] == ["tpl.sat.alg.test_valid.json"]

    out = capsys.readouterr().out
    assert "1 отброшено" in out
    assert "distractors collapse" in out
