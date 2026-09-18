"""Phase 2 repository behavior against a migrated quack_test Postgres database."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models import ForecastCache, TaskInstance
from app.db.repo import forecast, sets, tasks
from app.errors import NotFound
from app.schemas.knowledge import ForecastOut
from app.sets.assemble import SetPlan

pytestmark = [pytest.mark.integration, pytest.mark.phase2]


def plan(*skills: str, reason: str = "plan") -> SetPlan:
    return SetPlan(
        kind="regular",
        skill_ids=list(skills),
        deadline=date(2026, 10, 1),
        reason=reason,
    )


@pytest.mark.asyncio
async def test_replace_plan_preserves_done_current_and_closed_topics(db_session):
    student = uuid4()
    initial = await sets.replace_plan(
        db_session,
        student,
        "SAT_MATH",
        [plan("done"), plan("current", "closed"), plan("old-upcoming")],
        keep_current=False,
    )
    done, current, old_upcoming = initial
    await sets.set_status(db_session, student, done.id, "done")
    await sets.set_status(db_session, student, current.id, "current")
    await sets.set_topic_status(db_session, current.id, "closed", "closed")
    opened_at = (await sets.get_set(db_session, student, current.id)).opened_at

    rebuilt = await sets.replace_plan(
        db_session,
        student,
        "SAT_MATH",
        [plan("current", "closed", "new", reason="updated"), plan("next")],
        keep_current=True,
    )
    by_id = {item.id: item for item in rebuilt}
    assert by_id[done.id].status == "done"
    assert [topic.skill_id for topic in by_id[done.id].topics] == ["done"]
    assert by_id[current.id].status == "current"
    assert by_id[current.id].opened_at == opened_at
    assert by_id[current.id].reason == "updated"
    assert {topic.skill_id: topic.status for topic in by_id[current.id].topics} == {
        "current": "open",
        "closed": "closed",
        "new": "open",
    }
    assert old_upcoming.id not in by_id
    assert len([item for item in rebuilt if item.status == "upcoming"]) == 1
    assert (await sets.get_set(db_session, uuid4(), current.id)) is None
    with pytest.raises(NotFound):
        await sets.update_set(db_session, uuid4(), current.id, [], None)


@pytest.mark.asyncio
async def test_count_progress_filters_student_mode_skill_and_answered(db_session):
    student, other = uuid4(), uuid4()
    (set_out,) = await sets.replace_plan(
        db_session, student, "SAT_MATH", [plan("skill-a", "skill-b")], False
    )
    await sets.set_topic_status(db_session, set_out.id, "skill-a", "closed")
    now = datetime.now(UTC)

    def instance(owner, skill, mode, correct, answered=True):
        return TaskInstance(
            id=uuid4(),
            student_id=owner,
            template_id="template",
            seed=uuid4().int % 2**62,
            exam_id="SAT_MATH",
            type="mcq4",
            skill_id=skill,
            stem_rendered="question",
            options=[],
            answer="a",
            trap_answers=[],
            solution_rendered=[],
            figure_url=None,
            time_reference_sec=60,
            difficulty=1,
            tags=[],
            mode=mode,
            answered_at=now if answered else None,
            correct=correct,
        )

    db_session.add_all(
        [
            instance(student, "skill-a", "topic", True),
            instance(student, "skill-b", "mock_topic", False),
            instance(student, "skill-a", "mock_set", True),
            instance(student, "skill-a", "diagnostic", True),
            instance(student, "other-skill", "topic", True),
            instance(other, "skill-a", "topic", True),
            instance(student, "skill-b", "topic", None, answered=False),
        ]
    )
    await db_session.flush()
    progress = await sets.count_progress(db_session, student, set_out.id)
    assert progress.model_dump() == {
        "topics_closed": 1,
        "topics_total": 2,
        "tasks_answered": 3,
        "tasks_correct": 2,
    }
    with pytest.raises(NotFound):
        await sets.count_progress(db_session, other, set_out.id)


@pytest.mark.asyncio
async def test_set_mutations_are_student_scoped(db_session):
    owner, other = uuid4(), uuid4()
    (set_out,) = await sets.replace_plan(
        db_session, owner, "ENT_MATH", [plan("skill-a")], False
    )
    with pytest.raises(NotFound):
        await sets.set_status(db_session, other, set_out.id, "done")
    assert (await sets.list_sets(db_session, other, "ENT_MATH")) == []
    await sets.update_set(db_session, owner, set_out.id, ["skill-b"], date(2026, 11, 1))
    updated = await sets.get_set(db_session, owner, set_out.id)
    assert updated.deadline == date(2026, 11, 1)
    assert [topic.skill_id for topic in updated.topics] == ["skill-b"]


@pytest.mark.asyncio
async def test_replace_plan_keeps_current_when_plans_exclude_its_skills(db_session):
    student = uuid4()
    (current,) = await sets.replace_plan(
        db_session, student, "SAT_MATH", [plan("current-skill")], False
    )
    await sets.set_status(db_session, student, current.id, "current")
    rebuilt = await sets.replace_plan(
        db_session, student, "SAT_MATH", [plan("next-skill")], True
    )
    assert [(item.status, item.position) for item in rebuilt] == [
        ("current", 0),
        ("upcoming", 1),
    ]
    assert rebuilt[0].id == current.id
    assert [topic.skill_id for topic in rebuilt[0].topics] == ["current-skill"]


@pytest.mark.asyncio
async def test_tasks_bulk_queries_mark_answered_and_isolation(db_session, templates_db):
    student, other = uuid4(), uuid4()
    skill_ids = list({template.skill_id for template in templates_db})
    grouped = await tasks.list_templates_for_skills(db_session, skill_ids)
    assert {item.id for items in grouped.values() for item in items} == {
        item.id for item in templates_db
    }
    template = templates_db[0]
    await tasks.bump_seen(db_session, student, template.id)
    assert (await tasks.get_seen_many(db_session, student, [template.skill_id]))[
        template.id
    ] == 1
    assert await tasks.get_seen_many(db_session, other, [template.skill_id]) == {}

    row = TaskInstance(
        id=uuid4(),
        student_id=student,
        template_id=template.id,
        seed=uuid4().int % 2**62,
        exam_id=template.exam_id,
        type=template.type,
        skill_id=template.skill_id,
        stem_rendered="question",
        options=[],
        answer="a",
        trap_answers=[],
        solution_rendered=[],
        figure_url=None,
        time_reference_sec=60,
        difficulty=1,
        tags=[],
        mode="topic",
    )
    db_session.add(row)
    await db_session.flush()
    assert [
        item.id for item in await tasks.list_instances(db_session, student, [row.id])
    ] == [row.id]
    assert await tasks.list_instances(db_session, other, [row.id]) == []
    now = datetime.now(UTC)
    await tasks.mark_answered(db_session, row.id, now, True)
    await db_session.refresh(row)
    assert row.answered_at == now
    assert row.correct is True


@pytest.mark.asyncio
async def test_forecast_upsert_and_student_isolation(db_session):
    student, other = uuid4(), uuid4()
    value = ForecastOut(
        exam_id="SAT_MATH",
        predicted_raw=30,
        predicted_scaled=None,
        coverage=0.4,
        hours_needed=20,
        ready_by=None,
        test_date=None,
        on_track=None,
        as_of_event_id=1,
        note="estimate",
    )
    await forecast.put(db_session, student, "SAT_MATH", value, 1)
    assert (await forecast.get(db_session, student, "SAT_MATH")).predicted_raw == 30
    assert await forecast.get(db_session, other, "SAT_MATH") is None
    await forecast.put(
        db_session,
        student,
        "SAT_MATH",
        value.model_copy(update={"predicted_raw": 35}),
        2,
    )
    actual = await forecast.get(db_session, student, "SAT_MATH")
    assert (actual.predicted_raw, actual.as_of_event_id) == (35, 2)
    row = await db_session.scalar(
        select(ForecastCache).where(
            ForecastCache.student_id == student, ForecastCache.exam_id == "SAT_MATH"
        )
    )
    assert row.as_of_event_id == 2
    assert row.updated_at is not None
