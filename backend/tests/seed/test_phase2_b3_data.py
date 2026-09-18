"""B3 Phase 2 floor data coverage and cross-file references."""

import json
from collections import Counter
from pathlib import Path

import pytest

from app.schemas.tasks import TaskTemplateSpec
from app.seed.calendars import validate_calendars
from app.seed.programs import validate_programs_floor

pytestmark = pytest.mark.phase2

DATA = Path(__file__).resolve().parents[3] / "data"
EUROPE = {"DE", "NL", "PL", "FR"}
USA_ASIA = {"US", "SG", "JP"}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_program_floor_has_distribution_and_usable_demo_fields():
    programs = validate_programs_floor(DATA / "programs_floor" / "programs.json")
    counts = Counter(program.country for program in programs)
    assert 20 <= len(programs) <= 30
    assert 8 <= counts["KZ"] <= 10
    assert 8 <= sum(counts[country] for country in EUROPE) <= 10
    assert 3 <= sum(counts[country] for country in USA_ASIA) <= 5
    grant_ent = 0
    thresholds = set()
    for program in programs:
        assert program.is_demo
        assert program.source_url.startswith("https://example.invalid/")
        assert program.tuition_per_year is not None
        assert program.living_per_year is not None
        assert len(program.environment_text.split(". ")) >= 2
        assert len(program.requirements) >= 2 and program.deadlines
        assert all(deadline.is_demo for deadline in program.deadlines)
        exam_requirements = [
            requirement
            for requirement in program.requirements
            if requirement.type == "exam_score"
        ]
        assert exam_requirements
        assert all(
            requirement.exam_id is not None and requirement.threshold is not None
            for requirement in exam_requirements
        )
        thresholds.update(
            (requirement.exam_id, requirement.threshold)
            for requirement in exam_requirements
        )
        if program.country == "KZ" and program.scholarships_note:
            assert any(
                requirement.exam_id == "ENT_MATH" for requirement in exam_requirements
            )
            grant_ent += 1
    assert grant_ent >= 4
    assert len(thresholds) >= 8


def test_calendars_cover_both_exams_without_claiming_verification():
    records = validate_calendars(DATA / "knowledge_base" / "calendars.json")
    assert {record.exam_id for record in records} == {"SAT_MATH", "ENT_MATH"}
    assert all(record.is_demo for record in records)
    assert all("example.invalid" in record.source for record in records)
    assert all(record.registration_deadline < record.date for record in records)
    sat = [record for record in records if record.exam_id == "SAT_MATH"]
    assert min(record.date for record in sat).year == 2026
    assert max(record.date for record in sat).year == 2027


def test_owned_sat_template_coverage_and_misconception_references():
    skills_file = _json(DATA / "skills" / "sat_math.json")
    for area in ("psda", "geo"):
        skill_ids = {
            skill["id"]
            for section in skills_file["areas"]
            if section["id"] == f"area.sat.{area}"
            for skill in section["skills"]
        }
        misconception_ids = {
            item["id"] for item in _json(DATA / "misconceptions" / f"{area}.json")
        }
        paths = sorted((DATA / "templates" / "sat" / area).glob("*.json"))
        templates = [TaskTemplateSpec.model_validate(_json(path)) for path in paths]
        counts = Counter(template.skill_id for template in templates)
        assert all(2 <= counts[skill_id] <= 3 for skill_id in skill_ids)
        assert set(counts) == skill_ids
        assert all(template.exam_id == "SAT_MATH" for template in templates)
        assert all(template.type in {"mcq4", "numeric"} for template in templates)
        assert all(1 <= template.difficulty <= 4 for template in templates)
        for template in templates:
            refs = [
                item.misconception_id
                for item in [*template.distractors, *(template.trap_answers or [])]
                if item.misconception_id is not None
            ]
            assert set(refs) <= misconception_ids
    assert (
        sum(
            1
            for area in ("psda", "geo")
            for _ in (DATA / "templates" / "sat" / area).glob("*.json")
        )
        >= 30
    )
