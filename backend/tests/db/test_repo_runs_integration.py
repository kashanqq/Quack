"""Diagnostic, mock, and milestone repositories on migrated Postgres."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.models import MilestoneMark, TaskInstance
from app.db.repo import diagnostic, milestones, mocks
from app.errors import Conflict, NotFound
from app.schemas.diagnostic import DiagnosticResult, DiagnosticState

pytestmark = [pytest.mark.integration, pytest.mark.phase2]


def state(answered: int = 0) -> DiagnosticState:
    return DiagnosticState(
        exam_id="SAT_MATH",
        budget_left=4,
        reserve_left=2,
        asked=[],
        answered=answered,
        pending_descent=[],
        reask_queue=[],
        roots_found=[],
        trap_hits=[],
        firm=[],
        shaky=[],
        last_grade_correct=None,
    )


@pytest.mark.asyncio
async def test_diagnostic_lifecycle_conflict_and_isolation(db_session):
    student, other = uuid4(), uuid4()
    run = await diagnostic.create_run(db_session, student, "SAT_MATH", state())
    assert run.state["answered"] == 0
    assert (
        await diagnostic.get_active_run(db_session, student, "SAT_MATH")
    ).id == run.id
    assert await diagnostic.get_active_run(db_session, other, "SAT_MATH") is None
    with pytest.raises(Conflict):
        await diagnostic.create_run(db_session, student, "SAT_MATH", state())
    with pytest.raises(NotFound):
        await diagnostic.save_state(db_session, other, run.id, state(1))

    await diagnostic.save_state(db_session, student, run.id, state(1))
    assert run.state["answered"] == 1
    result = DiagnosticResult(
        firm=[], shaky=[], roots=[], suspected=[], start_from=[], words="done"
    )
    with pytest.raises(NotFound):
        await diagnostic.complete_run(db_session, other, run.id, result)
    await diagnostic.complete_run(db_session, student, run.id, result)
    assert run.status == "completed"
    assert run.result["words"] == "done"
    assert run.completed_at is not None
    assert await diagnostic.get_active_run(db_session, student, "SAT_MATH") is None
    with pytest.raises(Conflict):
        await diagnostic.complete_run(db_session, student, run.id, result)
    next_run = await diagnostic.create_run(db_session, student, "SAT_MATH", state())
    assert next_run.id != run.id


def instance(student_id):
    return TaskInstance(
        id=uuid4(),
        student_id=student_id,
        template_id="mock-template",
        seed=uuid4().int % 2**62,
        exam_id="SAT_MATH",
        type="mcq4",
        skill_id="skill-a",
        stem_rendered="question",
        options=[],
        answer="a",
        trap_answers=[],
        solution_rendered=[],
        figure_url=None,
        time_reference_sec=60,
        difficulty=1,
        tags=[],
        mode="mock_set",
    )


@pytest.mark.asyncio
async def test_mock_lifecycle_progress_and_isolation(db_session):
    student, other = uuid4(), uuid4()
    own, foreign = instance(student), instance(other)
    db_session.add_all([own, foreign])
    await db_session.flush()
    with pytest.raises(NotFound):
        await mocks.create_run(
            db_session, student, "SAT_MATH", "mock_set", "section", [foreign.id]
        )
    run = await mocks.create_run(
        db_session,
        student,
        "SAT_MATH",
        "mock_set",
        "section",
        [own.id],
        predicted_before=30.0,
    )
    assert run.status == "active"
    assert (await mocks.get_run(db_session, student, run.id)).id == run.id
    assert await mocks.get_run(db_session, other, run.id) is None
    with pytest.raises(NotFound):
        await mocks.save_progress(db_session, run.id, [foreign.id])
    await mocks.save_progress(db_session, run.id, [own.id])
    await db_session.refresh(own)
    assert own.answered_at is not None
    assert own.correct is None
    await mocks.complete_run(db_session, run.id, 18.0, 550.0)
    assert (run.raw_score, run.scaled_score) == (18.0, 550.0)
    assert run.status == "completed"
    assert run.completed_at is not None
    with pytest.raises(Conflict):
        await mocks.save_progress(db_session, run.id, [own.id])


@pytest.mark.asyncio
async def test_milestone_upsert_remove_and_isolation(db_session):
    student, other = uuid4(), uuid4()
    key = f"registration:SAT_MATH:{uuid4()}"
    assert await milestones.list_marks(db_session, student) == {}
    await milestones.set_mark(db_session, student, key, True)
    first = (await milestones.list_marks(db_session, student))[key]
    assert first.tzinfo is not None
    assert first <= datetime.now(UTC)
    assert await milestones.list_marks(db_session, other) == {}
    await milestones.set_mark(db_session, student, key, True)
    assert (await milestones.list_marks(db_session, student))[key] >= first
    count = await db_session.scalar(
        select(func.count(MilestoneMark.milestone_key)).where(
            MilestoneMark.student_id == student,
            MilestoneMark.milestone_key == key,
        )
    )
    assert count == 1
    await milestones.set_mark(db_session, student, key, False)
    assert key not in await milestones.list_marks(db_session, student)
