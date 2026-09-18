"""Import and frozen signature checks for Phase 2 repositories."""

import inspect
from uuid import uuid4

import pytest

from app.db.repo import diagnostic, forecast, milestones, mocks, programs, sets, tasks


@pytest.mark.parametrize(
    ("module", "names"),
    [
        (
            sets,
            (
                "list_sets",
                "get_set",
                "replace_plan",
                "set_status",
                "set_topic_status",
                "update_set",
                "count_progress",
            ),
        ),
        (diagnostic, ("create_run", "get_active_run", "save_state", "complete_run")),
        (mocks, ("create_run", "get_run", "save_progress", "complete_run")),
        (milestones, ("list_marks", "set_mark")),
        (forecast, ("get", "put")),
        (
            tasks,
            (
                "list_templates_for_skills",
                "get_seen_many",
                "mark_answered",
                "list_instances",
            ),
        ),
        (programs, ("list_all", "list_saved_programs")),
    ],
)
def test_phase2_repo_interfaces_are_async_and_session_first(module, names):
    for name in names:
        function = getattr(module, name)
        assert inspect.iscoroutinefunction(function)
        assert next(iter(inspect.signature(function).parameters)) == "session"


def test_frozen_mark_answered_signature():
    assert list(inspect.signature(tasks.mark_answered).parameters) == [
        "session",
        "instance_id",
        "answered_at",
        "correct",
    ]


def test_frozen_set_signatures():
    assert list(inspect.signature(sets.replace_plan).parameters) == [
        "session",
        "student_id",
        "exam_id",
        "plans",
        "keep_current",
    ]
    assert list(inspect.signature(sets.update_set).parameters) == [
        "session",
        "student_id",
        "set_id",
        "skill_ids",
        "deadline",
    ]


class QuerySession:
    def __init__(self):
        self.query = None

    async def scalars(self, query):
        self.query = query
        return self

    async def execute(self, query):
        self.query = query
        return self

    def all(self):
        return []


@pytest.mark.asyncio
async def test_personal_bulk_queries_filter_student_id():
    student_id = uuid4()
    session = QuerySession()

    assert await tasks.get_seen_many(session, student_id, ["skill-a"]) == {}
    assert student_id in session.query.compile().params.values()

    assert await tasks.list_instances(session, student_id, [uuid4()]) == []
    assert student_id in session.query.compile().params.values()

    assert await programs.list_saved_programs(session, student_id) == []
    assert student_id in session.query.compile().params.values()


@pytest.mark.asyncio
async def test_list_all_excludes_flagged_programs():
    session = QuerySession()
    assert await programs.list_all(session) == []
    assert "programs_cache.flagged IS false" in str(session.query.compile())
