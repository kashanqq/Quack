"""B1/B2 skeleton signatures and B3 dependency wiring."""

import importlib
import inspect
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.api.deps import get_rule_deps
from app.apply import (
    diagnostic,
    dispute,
    knowledge,
    mocks,
    profile_updated,
    sets,
    task_answered,
    tasks,
)
from app.config import settings
from app.events import dispatch as dispatcher
from app.schemas.events import EventType


@pytest.mark.parametrize(
    ("module", "signatures"),
    [
        (
            task_answered,
            {
                "apply_task_answered": ["session", "event", "deps"],
                "apply_task_skipped": ["session", "event", "deps"],
            },
        ),
        (profile_updated, {"apply_profile_updated": ["session", "event", "deps"]}),
        (dispute, {"apply_dispute": ["session", "event", "deps"]}),
        (
            sets,
            {
                "rebuild_sets": ["session", "deps", "student_id", "exam_id"],
                "open_set": ["session", "deps", "student_id", "set_id"],
                "on_program_change": ["session", "event", "deps"],
                "on_set_change": ["session", "event", "deps"],
                "on_run_completed": ["session", "event", "deps"],
            },
        ),
        (
            diagnostic,
            {
                "start": ["session", "deps", "student_id", "exam_id", "n_tasks"],
                "answer": ["session", "deps", "student_id", "run_id", "result"],
                "finish": ["session", "deps", "student_id", "run_id"],
            },
        ),
        (
            mocks,
            {
                "start": ["session", "deps", "student_id", "body"],
                "answer": ["session", "deps", "student_id", "run_id", "result"],
                "finish": ["session", "deps", "student_id", "run_id"],
            },
        ),
        # chat_id — необязательный: задачу выдаёт и форма темы, и репетитор
        # в чате, и только во втором случае событие привязано к чату.
        (tasks, {"issue": ["session", "deps", "student_id", "req", "chat_id"]}),
        (
            knowledge,
            {
                "states_view": ["session", "deps", "student_id", "exam_id"],
                "misconceptions_view": ["deps", "student_id", "exam_id"],
                "explain": ["deps", "student_id", "node_id"],
            },
        ),
    ],
)
def test_apply_interfaces_are_async_with_exact_parameters(module, signatures):
    for name, parameters in signatures.items():
        function = getattr(module, name)
        assert inspect.iscoroutinefunction(function)
        assert list(inspect.signature(function).parameters) == parameters
        assert (
            inspect.signature(function).return_annotation is not inspect.Signature.empty
        )


@pytest.mark.parametrize(
    ("module_name", "function_name", "parameters"),
    [
        (
            "app.roadmap.requirements",
            "build_requirements",
            ["saved", "profile", "exam_formats", "test_dates", "forecasts", "params"],
        ),
        (
            "app.roadmap.milestones",
            "build_milestones",
            ["saved", "requirements", "test_dates", "calendars", "marks", "today"],
        ),
        (
            "app.roadmap.conflicts",
            "find_conflicts",
            ["milestones", "saved", "planned_test_dates"],
        ),
        (
            "app.roadmap.progress",
            "exam_progress",
            ["requirement", "states", "forecast", "milestones"],
        ),
    ],
)
def test_roadmap_interfaces_import_without_io(module_name, function_name, parameters):
    module = importlib.import_module(module_name)
    function = getattr(module, function_name)
    assert not inspect.iscoroutinefunction(function)
    assert list(inspect.signature(function).parameters) == parameters
    assert inspect.signature(function).return_annotation is not inspect.Signature.empty


def test_rule_deps_uses_app_connections_and_callable_clock():
    graph = object()
    redis = object()
    # Фаза 4 (§1.4): outbox запроса живёт на `request.state`.
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(neo4j=graph, redis=redis)),
        state=SimpleNamespace(),
    )

    deps = get_rule_deps(request)

    assert deps.graph is graph
    assert deps.redis is redis
    assert deps.jobs is request.state.job_outbox
    assert deps.params is settings.knowledge
    assert callable(deps.now)
    assert isinstance(deps.now(), datetime)
    assert deps.now().tzinfo is not None


def test_handlers_reference_apply_functions(monkeypatch):
    monkeypatch.setattr(dispatcher, "_handlers", {})
    from app.events import handlers

    dispatcher._handlers.clear()
    importlib.reload(handlers)
    assert dispatcher._handlers[EventType.task_answered] == [
        task_answered.apply_task_answered
    ]
    # Фаза 4 добавляет вторым обработчиком постановку срочного батча (§2.2).
    assert dispatcher._handlers[EventType.program_saved][0] is sets.on_program_change
