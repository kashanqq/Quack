"""gen_templates.py skeleton (30-B2-phase2.md §0.1 п.2, §5)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
from redis.exceptions import RedisError

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

# Passes validate_template (multi_select skips the symbolic mcq check, and
# generate_instance doesn't render option text at all, so it never raises) —
# only the render-time leftover-`{` check (item 3, app.tasks.generate is
# B1's, gen_templates.py owns this guard) catches the unrendered `{a}`.
_LEFTOVER_PLACEHOLDER_TEMPLATE = {
    "id": "tpl.sat.alg.test_leftover",
    "exam_id": "SAT_MATH",
    "type": "multi_select",
    "difficulty": 1,
    "skill_id": "sat.alg.slope_lines",
    "tags": ["test"],
    "time_reference_sec": 30,
    "kind": "template",
    "params": {"a": {"range": [1, 5]}},
    "constraints": [],
    "stem": "Уравнение x = {a}. Выберите верные утверждения.",
    "correct": ["решение равно {a}"],
    "distractors": [{"expr": "решение больше {a}", "misconception_id": None}],
    "solution": ["x = {a}"],
}

# Passes validate_template and the leftover-`{` check (the placeholder is a
# bare param name and does substitute) — only render_stem's parenthesize rule
# fails, because it recognises ASCII +-*/ but not the typographic "·" used
# here, and `a`'s range is all-negative so every seed reproduces it.
_UNPARENTHESIZED_NEGATIVE_TEMPLATE = {
    "id": "tpl.sat.alg.test_unparenthesized",
    "exam_id": "SAT_MATH",
    "type": "numeric",
    "difficulty": 1,
    "skill_id": "sat.alg.slope_lines",
    "tags": ["test"],
    "time_reference_sec": 30,
    "kind": "template",
    "params": {"a": {"range": [-5, -1]}},
    "constraints": [],
    "stem": "Чему равно 4·{a}?",
    "correct": "4*a",
    "distractors": [],
    "solution": ["4·{a} = {answer}"],
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

    # Area-wide sharing (30-B2-phase2.md §3.1): a skill with no
    # misconceptions of its own — math.alg.linear_eq — must still see
    # lib.abs_single_branch, tagged as belonging to a neighbouring skill,
    # not just the skill it's directly attached to (math.alg.abs_value_eq).
    blocks = result.stdout.split("=== навык ")
    linear_eq_block = next(b for b in blocks if b.startswith("math.alg.linear_eq "))
    assert "lib.abs_single_branch" in linear_eq_block
    assert "смежный навык" in linear_eq_block

    assert list(tmp_path.iterdir()) == []


class _FakeRedis:
    @classmethod
    def from_url(cls, url):
        return cls()

    async def ping(self):
        return True

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


async def test_generation_drops_template_with_leftover_placeholder(
    monkeypatch, tmp_path, capsys
):
    gen_templates = _load_module()

    leftover_spec = TaskTemplateSpec.model_validate(_LEFTOVER_PLACEHOLDER_TEMPLATE)
    script = [gen_templates.GeneratedTemplates(templates=[leftover_spec])]
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
    assert list(tmp_path.iterdir()) == []
    out = capsys.readouterr().out
    assert "1 отброшено" in out
    assert "leftover placeholder" in out


async def test_generation_drops_template_with_unparenthesized_negative(
    monkeypatch, tmp_path, capsys
):
    gen_templates = _load_module()

    spec = TaskTemplateSpec.model_validate(_UNPARENTHESIZED_NEGATIVE_TEMPLATE)
    script = [gen_templates.GeneratedTemplates(templates=[spec])]
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
    assert list(tmp_path.iterdir()) == []
    out = capsys.readouterr().out
    assert "1 отброшено" in out
    assert "unparenthesized negative" in out


class _DownRedis:
    @classmethod
    def from_url(cls, url):
        return cls()

    async def ping(self):
        raise RedisError("connection refused")

    async def aclose(self):
        return None


async def test_run_stops_cleanly_when_redis_is_unreachable(monkeypatch, tmp_path):
    gen_templates = _load_module()

    def _fail_if_called(settings, redis):
        raise AssertionError("LLMClient must not be constructed when redis is down")

    monkeypatch.setattr(gen_templates, "LLMClient", _fail_if_called)
    monkeypatch.setattr(gen_templates, "Redis", _DownRedis)

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

    assert exit_code == 1
    assert list(tmp_path.iterdir()) == []
