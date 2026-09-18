"""Validate data/*.json against the Pydantic schemas and cross-file rules.

No database — pure file validation.
Source: 20-B1.md §7 (tests/seed/test_data_schemas.py).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.schemas.knowledge import ExamFormat
from app.schemas.tasks import TaskTemplateSpec
from app.seed.skills import SkillsFile
from app.tasks.generate import validate_template


pytestmark = pytest.mark.phase1

DATA = Path(__file__).resolve().parents[3] / "data"


# --- helpers ---


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _all_skill_files() -> list[Path]:
    return sorted((DATA / "skills").glob("*.json"))


def _all_exam_format_files() -> list[Path]:
    return sorted((DATA / "exam_formats").glob("*.json"))


def _all_template_files() -> list[Path]:
    return sorted((DATA / "templates").rglob("*.json"))


# --- skills ---


def test_every_skills_file_parses():
    files = _all_skill_files()
    assert files, "no skill files found"
    for f in files:
        SkillsFile.model_validate(_load(f))


def test_weights_sum_to_max_raw_score():
    for f in _all_skill_files():
        data = SkillsFile.model_validate(_load(f))
        total = sum(s.weight for a in data.areas for s in a.skills)
        assert total == pytest.approx(data.exam.max_raw_score), (
            f"{f.name}: Σ weight {total} != {data.exam.max_raw_score}"
        )


def test_requires_is_dag():
    for f in _all_skill_files():
        data = SkillsFile.model_validate(_load(f))
        graph: dict[str, list[str]] = {s.id: [] for s in data.skills}
        for s in data.skills:
            for r in s.requires:
                graph.setdefault(s.id, []).append(r.skill_id)
                graph.setdefault(r.skill_id, [])

        # simple DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n: WHITE for n in graph}

        def dfs(n: str) -> bool:
            color[n] = GRAY
            for m in graph.get(n, []):
                if color.get(m) == GRAY:
                    return False
                if color.get(m) == WHITE and not dfs(m):
                    return False
            color[n] = BLACK
            return True

        for n in graph:
            if color[n] == WHITE:
                assert dfs(n), f"{f.name}: cycle in REQUIRES at {n}"


def test_area_skills_are_defined_somewhere():
    """Every skill_id referenced in areas[].skills must be defined in one of the skill files."""
    all_defined: set[str] = set()
    for f in _all_skill_files():
        data = SkillsFile.model_validate(_load(f))
        for s in data.skills:
            all_defined.add(s.id)

    for f in _all_skill_files():
        data = SkillsFile.model_validate(_load(f))
        for area in data.areas:
            for aref in area.skills:
                assert aref.id in all_defined, (
                    f"{f.name}: area {area.id} references undefined skill {aref.id}"
                )


# --- exam formats ---


def test_every_exam_format_parses():
    files = _all_exam_format_files()
    assert files, "no exam format files found"
    for f in files:
        ExamFormat.model_validate(_load(f))


def test_exam_format_area_shares_sum_to_one():
    for f in _all_exam_format_files():
        fmt = ExamFormat.model_validate(_load(f))
        for sec in fmt.sections:
            total = sum(sec.area_shares.values())
            assert total == pytest.approx(1.0), (
                f"{f.name}/{sec.name}: area_shares Σ {total} != 1.0"
            )


# --- misconceptions ---


def test_library_parses_and_skills_exist():
    path = DATA / "misconceptions" / "library.json"
    entries = _load(path)
    assert entries, "library is empty"

    all_defined: set[str] = set()
    for f in _all_skill_files():
        data = SkillsFile.model_validate(_load(f))
        for s in data.skills:
            all_defined.add(s.id)

    for e in entries:
        for sid in e["skill_ids"]:
            assert sid in all_defined, (
                f"{e['id']}: skill {sid} not defined anywhere"
            )


# --- templates ---


def test_every_template_parses_and_validates():
    files = _all_template_files()
    assert files, "no template files found"

    all_skills: set[str] = set()
    for f in _all_skill_files():
        data = SkillsFile.model_validate(_load(f))
        for s in data.skills:
            all_skills.add(s.id)

    misc_ids: set[str] = {
        e["id"] for e in _load(DATA / "misconceptions" / "library.json")
    }

    for f in files:
        spec = TaskTemplateSpec.model_validate(_load(f))
        assert spec.skill_id in all_skills, (
            f"{f.name}: skill {spec.skill_id} not defined"
        )
        for d in spec.distractors:
            if d.misconception_id:
                assert d.misconception_id in misc_ids, (
                    f"{f.name}: misconception {d.misconception_id} not in library"
                )
        for t in spec.trap_answers or []:
            if t.misconception_id:
                assert t.misconception_id in misc_ids, (
                    f"{f.name}: trap misconception {t.misconception_id} not in library"
                )
        for o in spec.omission_traps or []:
            if o.misconception_id:
                assert o.misconception_id in misc_ids, (
                    f"{f.name}: omission misconception {o.misconception_id} not in library"
                )
        errors = validate_template(spec)
        assert errors == [], f"{f.name}: {errors}"


def test_at_least_one_template_of_each_type():
    files = _all_template_files()
    types_seen: set[str] = set()
    for f in files:
        spec = TaskTemplateSpec.model_validate(_load(f))
        types_seen.add(spec.type)
    expected = {"mcq4", "mcq5", "multi_select", "numeric"}
    missing = expected - types_seen
    assert not missing, f"missing template types: {missing}"