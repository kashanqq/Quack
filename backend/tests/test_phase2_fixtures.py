"""Phase 2 fixture data and dependency setup without external services."""

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.apply import task_answered as apply_task_answered
from app.apply import tasks as apply_tasks
from app.db.repo.programs import list_saved_programs
from app.db.repo.tasks import list_templates_for_skills
from app.events import dispatch as dispatcher
from app.schemas.events import EventType
from app.seed.skills import SkillsFile
from app.seed.templates import validate_templates

DATA = Path(__file__).resolve().parent / "fixtures" / "data"


def test_frozen_now_and_rule_deps(frozen_now, rule_deps, redis):
    assert frozen_now == datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    assert rule_deps.now() == frozen_now
    assert rule_deps.graph is None
    assert rule_deps.redis is redis
    assert rule_deps.params.check_size == 3


def test_phase2_minimap_has_exact_contract_counts():
    skills = SkillsFile.model_validate(
        json.loads((DATA / "skills" / "sat_math.json").read_text(encoding="utf-8"))
    )
    misconceptions = json.loads(
        (DATA / "misconceptions" / "library.json").read_text(encoding="utf-8")
    )
    assert skills.exam.id == "SAT_MATH"
    assert len(skills.areas) == 2
    assert len(skills.skills) == 5
    assert len(misconceptions) == 2
    assert len(list((DATA / "templates").glob("*.json"))) == 2
    validate_templates(DATA / "templates")


async def test_fake_apply_patches_only_test_target(fake_apply):
    response = object()
    mock = fake_apply("app.apply.tasks.issue", response)
    assert await apply_tasks.issue(None, None, None, None) is response
    mock.assert_awaited_once()
    with pytest.raises(ValueError):
        fake_apply("app.db.repo.tasks.get_template", response)


def test_fake_apply_replaces_registered_handler(fake_apply, monkeypatch):
    monkeypatch.setattr(dispatcher, "_handlers", {})
    from app.events import handlers

    dispatcher._handlers.clear()
    importlib.reload(handlers)
    assert dispatcher._handlers[EventType.task_answered] == [
        apply_task_answered.apply_task_answered
    ]
    mock = fake_apply("app.apply.task_answered.apply_task_answered", "grade")
    assert dispatcher._handlers[EventType.task_answered] == [mock]


@pytest.mark.integration
async def test_student_with_saved_fixture(student_with_saved, db_session):
    programs = await list_saved_programs(db_session, student_with_saved.student_id)
    assert [program.id for program in programs] == [
        program.id for program in student_with_saved.programs
    ]


@pytest.mark.integration
async def test_templates_db_fixture(templates_db, db_session):
    grouped = await list_templates_for_skills(
        db_session, [template.skill_id for template in templates_db]
    )
    assert {template.id for group in grouped.values() for template in group} == {
        template.id for template in templates_db
    }


@pytest.mark.integration
async def test_seeded_graph_fixture(seeded_graph):
    assert seeded_graph is not None
