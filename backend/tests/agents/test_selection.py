"""Selection assistant: stages, tool policy, prompt, tools, postcheck
(docs/tz/phase3-agents.md §3.2–§3.3, §6.3)."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app import keys
from app.agents import selection
from app.errors import Conflict, NotFound
from app.llm.fake import FakeLLMClient
from app.llm.tools import ToolCtx
from app.schemas.agents import MatchingSnapshot, SnapshotItem, TurnState
from app.schemas.chat import (
    ChatMessageIn,
    Done,
    StreamError,
    TextDelta,
    ToolCall,
    ToolResult,
)
from app.schemas.events import EventType
from app.schemas.matching import CompareOut
from app.schemas.programs import Requirement
from tests.agents._scripts import (
    NOW,
    TC,
    TXT,
    calls_turn,
    collect,
    matching_out,
    patch_selection_io,
    program,
)

pytestmark = pytest.mark.phase3

ALL_TOOLS = {
    "update_profile",
    "run_matching",
    "compare",
    "save_program",
    "get_program_facts",
    "get_admission_route",
    "get_exam_format",
    "query_dataset",
}


def _tool_names(call) -> set[str]:
    return {tool["function"]["name"] for tool in (call.tools or [])}


async def _snapshot(redis, student_id, *items):
    snapshot = MatchingSnapshot(
        items=[
            SnapshotItem(
                program_id=pid,
                university="u",
                direction="d",
                realism=realism,
                score=1.0,
                factors=[],
            )
            for pid, realism in items
        ],
        as_of=NOW,
    )
    await redis.set(keys.matching_snapshot(str(student_id)), snapshot.model_dump_json())


def _tool_ctx(agent_deps, student_id=None) -> ToolCtx:
    return ToolCtx(
        student_id=str(student_id or uuid4()),
        deps=agent_deps,
        request_id="r",
        turn=TurnState(),
    )


# --- stages ---


def test_stage_opening_when_no_assistant_messages(profile_factory):
    assert selection._stage([], profile_factory(), None, "привет") == "opening"


async def test_opening_turn_prompt_and_tools(
    monkeypatch, agent_deps, chat_ctx, profile_factory
):
    profile = profile_factory()
    patch_selection_io(monkeypatch, profile=profile)
    agent_deps.llm = FakeLLMClient([TXT("Помогу подобрать программу. Что ищешь?")])

    events = await collect(
        selection.run(chat_ctx(), ChatMessageIn(text="привет"), [], profile, agent_deps)
    )

    call = agent_deps.llm.calls[0]
    assert "Стадия разговора сейчас: opening" in call.messages[0].content
    assert "run_matching" not in _tool_names(call)
    assert isinstance(events[-1], Done) and events[-1].mode == "opening"


def test_stage_intake_and_missing_fields_order(history_factory, profile_factory):
    profile = profile_factory(**{"level.grade": 11})
    history = history_factory([("user", "hi"), ("assistant", "hello", "opening")])

    assert profile.readiness < 0.6
    assert selection._stage(history, profile, None, "да") == "intake"
    rendered = selection.render_profile(profile)
    missing = next(
        line for line in rendered.splitlines() if line.startswith("missing:")
    )
    assert missing.startswith("missing: direction.field, preferences.budget_per_year")


def test_stage_summary_at_threshold(history_factory, profile_factory):
    profile = profile_factory(
        **{
            "direction.field": "CS",
            "preferences.budget_per_year": 5000,
            "preferences.grant_need": "preferred",
            "preferences.countries": ["DE"],
            "academics.sat_score": 1300,
        }
    )
    history = history_factory([("user", "hi"), ("assistant", "hello", "intake")])

    assert profile.readiness >= 0.6
    stage = selection._stage(history, profile, None, "ок")
    assert stage == "summary"
    names = set(selection._tool_policy(stage, "ок", None).names())
    assert "run_matching" in names
    assert not names & {"compare", "save_program"}


def test_stage_matching_after_summary(history_factory, profile_factory):
    profile = profile_factory(
        **{
            "direction.field": "CS",
            "preferences.budget_per_year": 5000,
            "preferences.grant_need": "preferred",
            "preferences.countries": ["DE"],
            "academics.sat_score": 1300,
        }
    )
    history = history_factory([("user", "hi"), ("assistant", "резюме", "summary")])

    stage = selection._stage(history, profile, None, "да, всё так")
    assert stage == "matching"
    assert set(selection._tool_policy(stage, "да", None).names()) == ALL_TOOLS


def test_stage_refine_when_snapshot_exists(history_factory, profile_factory):
    history = history_factory([("user", "hi"), ("assistant", "ok", "matching")])
    snapshot = MatchingSnapshot(items=[], as_of=NOW)

    assert selection._stage(history, profile_factory(), snapshot, "ок") == "refine"


def test_wants_matching_regex_allows_run_matching_in_intake():
    names = selection._tool_policy("intake", "просто покажи варианты", None).names()
    assert "run_matching" in names
    assert "run_matching" not in selection._tool_policy("intake", "ок", None).names()


async def test_known_fields_are_in_prompt_not_reasked(
    monkeypatch, agent_deps, chat_ctx, history_factory, profile_factory
):
    profile = profile_factory(**{"preferences.budget_per_year": 5000})
    patch_selection_io(monkeypatch, profile=profile)
    agent_deps.llm = FakeLLMClient([TXT("Понял.")])
    history = history_factory([("user", "hi"), ("assistant", "hello", "opening")])

    await collect(
        selection.run(
            chat_ctx(), ChatMessageIn(text="ок"), history, profile, agent_deps
        )
    )

    system = agent_deps.llm.calls[0].messages[0].content
    assert "preferences.budget_per_year: 5000 (сказал)" in system
    missing = next(line for line in system.splitlines() if line.startswith("missing:"))
    assert "preferences.budget_per_year" not in missing


# --- tool order and results ---


async def test_tool_call_order_update_then_matching(
    monkeypatch, agent_deps, chat_ctx, history_factory, profile_factory
):
    profile = profile_factory()
    patch_selection_io(monkeypatch, profile=profile)
    update = AsyncMock(return_value={"path": "preferences.budget_per_year"})
    run_matching = AsyncMock(return_value={"count": 5})
    monkeypatch.setattr(selection.update_profile, "fn", update)
    monkeypatch.setattr(selection.run_matching, "fn", run_matching)
    agent_deps.llm = FakeLLMClient(
        [
            TC(
                "update_profile", {"path": "preferences.budget_per_year", "value": 5000}
            ),
            TC("run_matching", {"limit": 5}, call_id="call_2"),
            TXT("Вот пять программ"),
        ]
    )
    history = history_factory([("user", "hi"), ("assistant", "резюме", "summary")])

    events = await collect(
        selection.run(
            chat_ctx(), ChatMessageIn(text="да, покажи"), history, profile, agent_deps
        )
    )

    assert [type(e) for e in events] == [
        ToolCall,
        ToolResult,
        ToolCall,
        ToolResult,
        TextDelta,
        Done,
    ]
    assert events[-1].mode == "matching"
    last = agent_deps.llm.calls[-1].messages
    assert [m.tool_call_id for m in last if m.role == "tool"] == ["call_1", "call_2"]


def _patch_profile_tool(monkeypatch, profile):
    monkeypatch.setattr(
        selection.profiles_repo, "get_profile", AsyncMock(return_value=profile)
    )
    apply = AsyncMock(return_value=profile)
    monkeypatch.setattr(selection.profiles_repo, "apply_profile_update", apply)
    append = AsyncMock()
    monkeypatch.setattr(selection.store, "append", append)
    return apply, append


async def test_update_profile_forces_by_assistant(
    monkeypatch, agent_deps, profile_factory
):
    profile = profile_factory()
    apply, append = _patch_profile_tool(monkeypatch, profile)

    await selection.SELECTION_TOOLS.call(
        "update_profile",
        {"path": "preferences.budget_per_year", "value": 5000, "by": "user"},
        _tool_ctx(agent_deps, profile.student_id),
    )

    assert apply.call_args.args[2].by == "assistant"
    event = append.call_args.args[2]
    assert event.type == EventType.profile_updated
    assert event.payload["by"] == "assistant"
    assert append.call_args.kwargs["dispatch_event"] is True


async def test_update_profile_unchanged_writes_no_event(
    monkeypatch, agent_deps, profile_factory
):
    profile = profile_factory(**{"preferences.budget_per_year": 5000})
    apply, append = _patch_profile_tool(monkeypatch, profile)

    result = await selection.SELECTION_TOOLS.call(
        "update_profile",
        {"path": "preferences.budget_per_year", "value": "5000"},
        _tool_ctx(agent_deps, profile.student_id),
    )

    assert result["unchanged"] is True
    apply.assert_not_called()
    append.assert_not_called()


async def test_update_profile_returns_shift(
    monkeypatch, agent_deps, redis, profile_factory
):
    profile = profile_factory()
    _patch_profile_tool(monkeypatch, profile)
    await _snapshot(redis, profile.student_id, ("A", "try"))
    monkeypatch.setattr(
        selection.apply_matching,
        "run_matching",
        AsyncMock(return_value=matching_out(("A", "possible"))),
    )

    result = await selection.SELECTION_TOOLS.call(
        "update_profile",
        {"path": "preferences.budget_per_year", "value": 5000},
        _tool_ctx(agent_deps, profile.student_id),
    )

    assert len(result["shift"]) == 1
    shift = result["shift"][0]
    assert (shift["program_id"], shift["from_realism"], shift["to_realism"]) == (
        "A",
        "try",
        "possible",
    )


async def test_run_matching_writes_snapshot_and_count(monkeypatch, agent_deps, redis):
    student_id = uuid4()
    out = matching_out(("A", "possible"), ("B", "try"), ("C", "impossible"))
    out.total = 7
    monkeypatch.setattr(
        selection.apply_matching, "run_matching", AsyncMock(return_value=out)
    )

    result = await selection.SELECTION_TOOLS.call(
        "run_matching", {"limit": 5}, _tool_ctx(agent_deps, student_id)
    )

    assert result["count"] == len(result["items"]) == 3
    assert result["total"] == 7
    stored = await redis.get(keys.matching_snapshot(str(student_id)))
    snapshot = MatchingSnapshot.model_validate_json(stored)
    assert [i.program_id for i in snapshot.items] == ["A", "B", "C"]


async def test_save_program_twice_conflict(monkeypatch, agent_deps):
    append = AsyncMock()
    monkeypatch.setattr(selection.store, "append", append)
    saved: set[str] = set()

    async def save(_session, _sid, program_id):
        if program_id in saved:
            raise Conflict("program already saved")
        saved.add(program_id)

    monkeypatch.setattr(selection.programs_repo, "save_program", save)
    monkeypatch.setattr(
        selection.programs_repo, "list_saved_programs", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(selection.profiles_repo, "get_profile", AsyncMock())
    monkeypatch.setattr(selection.forecast_repo, "get", AsyncMock(return_value=None))
    monkeypatch.setattr(selection, "build_requirements", lambda *a: [])
    ctx = _tool_ctx(agent_deps)
    agent_deps.llm = FakeLLMClient(
        [
            calls_turn(("save_program", {"program_id": "A"})),
            calls_turn(("save_program", {"program_id": "A"})),
            TXT("Сохранил."),
        ]
    )
    from app.llm.loop import run_tool_loop

    events = [
        e
        async for e in run_tool_loop(
            agent_deps.llm, selection.SELECTION_TOOLS, [], "chat", ctx
        )
        if isinstance(e, ToolResult)
    ]

    assert events[0].error is None
    assert "already saved" in events[1].error
    assert append.await_count == 1


async def test_save_program_dispatches_rebuild(monkeypatch, agent_deps):
    append = AsyncMock()
    monkeypatch.setattr(selection.store, "append", append)
    monkeypatch.setattr(selection.programs_repo, "save_program", AsyncMock())
    monkeypatch.setattr(
        selection.programs_repo,
        "list_saved_programs",
        AsyncMock(return_value=[program("A")]),
    )
    monkeypatch.setattr(selection.profiles_repo, "get_profile", AsyncMock())
    monkeypatch.setattr(selection.forecast_repo, "get", AsyncMock(return_value=None))
    monkeypatch.setattr(selection, "build_requirements", lambda *a: [])

    result = await selection.SELECTION_TOOLS.call(
        "save_program", {"program_id": "A"}, _tool_ctx(agent_deps)
    )

    event = append.call_args.args[2]
    assert event.type == EventType.program_saved
    # the rule deps are passed and dispatch is on — `on_program_change` runs
    assert append.call_args.args[3] is not None
    assert append.call_args.kwargs["dispatch_event"] is True
    assert result["saved_count"] == 1


def test_query_dataset_aggregates():
    programs = [
        program("a", country="DE", tuition_per_year=0, scholarships_note="yes"),
        program("b", country="DE", tuition_per_year=1500),
        program(
            "c",
            country="DE",
            tuition_per_year=3000,
            requirements=[
                Requirement(
                    type="exam_score",
                    exam_id="SAT_MATH",
                    threshold=650,
                    comparator=">=",
                    description="SAT",
                )
            ],
        ),
        program("d", country="NL", tuition_per_year=9000),
        program("e", country="KZ", tuition_per_year=None, currency="KZT"),
    ]

    out = selection.aggregate_dataset(
        programs, "сколько стоит в Германии", "de", None, []
    )

    assert out.count == 3
    assert (out.tuition.min, out.tuition.median, out.tuition.max) == (0, 1500, 3000)
    assert out.free_count == 1
    assert out.with_scholarship_note == 1
    assert out.exam_thresholds["SAT_MATH"].min == 650
    assert len(out.sources) <= 15
    assert out.question == "сколько стоит в Германии"
    assert out.profile_filtered is False

    by_profile = selection.aggregate_dataset(programs, "q", None, None, ["NL"])
    assert by_profile.count == 1 and by_profile.profile_filtered is True


async def test_get_admission_route_graph_down(agent_deps):
    result = [
        e
        async for e in __import__("app.llm.loop", fromlist=["x"]).run_tool_loop(
            FakeLLMClient(
                [TC("get_admission_route", {"country_id": "DE"}), TXT("нет данных")]
            ),
            selection.SELECTION_TOOLS,
            [],
            "chat",
            _tool_ctx(agent_deps),
        )
        if isinstance(e, ToolResult)
    ]
    assert result[0].error == "knowledge base unavailable"


async def test_get_program_facts_flagged_is_not_found(monkeypatch, agent_deps):
    monkeypatch.setattr(
        selection.programs_repo,
        "get_program",
        AsyncMock(return_value=program("A", flagged=True)),
    )
    with pytest.raises(NotFound):
        await selection.SELECTION_TOOLS.call(
            "get_program_facts", {"program_id": "A"}, _tool_ctx(agent_deps)
        )


async def test_compare_uses_shared_apply(monkeypatch, agent_deps):
    compare = AsyncMock(
        return_value=CompareOut(
            program_ids=["A", "B"], rows=[], collapsed_same=[], conclusion=None
        )
    )
    monkeypatch.setattr(selection.apply_matching, "compare_programs", compare)

    result = await selection.SELECTION_TOOLS.call(
        "compare", {"program_ids": ["A", "B"]}, _tool_ctx(agent_deps)
    )

    assert result["program_ids"] == ["A", "B"]
    assert compare.call_args.args[3] == ["A", "B"]


async def test_tool_denied_unknown_name(
    monkeypatch, agent_deps, chat_ctx, profile_factory
):
    profile = profile_factory()
    patch_selection_io(monkeypatch, profile=profile)
    agent_deps.llm = FakeLLMClient([TC("delete_everything"), TXT("Не могу.")])

    events = await collect(
        selection.run(chat_ctx(), ChatMessageIn(text="удали"), [], profile, agent_deps)
    )

    result = next(e for e in events if isinstance(e, ToolResult))
    assert result.error and "unknown tool" in result.error
    assert isinstance(events[-2], TextDelta)
    assert isinstance(events[-1], Done)


async def test_tool_validation_error_is_result_not_exception(
    monkeypatch, agent_deps, chat_ctx, redis, history_factory, profile_factory
):
    profile = profile_factory()
    patch_selection_io(monkeypatch, profile=profile)
    await _snapshot(redis, profile.student_id, ("A", "try"))
    monkeypatch.setattr(
        selection.apply_matching,
        "run_matching",
        AsyncMock(return_value=matching_out(("A", "try"))),
    )
    monkeypatch.setattr(
        selection.apply_matching,
        "compare_programs",
        __import__("app.apply.matching", fromlist=["x"]).compare_programs,
    )
    agent_deps.llm = FakeLLMClient(
        [TC("compare", {"program_ids": ["only-one"]}), TXT("Нужно две.")]
    )
    history = history_factory([("user", "hi"), ("assistant", "ok", "summary")])

    events = await collect(
        selection.run(
            chat_ctx(student_id=profile.student_id),
            ChatMessageIn(text="сравни"),
            history,
            profile,
            agent_deps,
        )
    )

    result = next(e for e in events if isinstance(e, ToolResult))
    assert "2 to 4" in result.error


async def test_assistant_markup_mode_is_stage(
    monkeypatch, agent_deps, chat_ctx, redis, history_factory, profile_factory
):
    profile = profile_factory()
    patch_selection_io(monkeypatch, profile=profile)
    monkeypatch.setattr(
        selection.apply_matching,
        "run_matching",
        AsyncMock(return_value=matching_out(("A", "try"))),
    )
    ctx = chat_ctx(student_id=profile.student_id)
    await _snapshot(redis, profile.student_id, ("A", "try"))
    agent_deps.llm = FakeLLMClient([TXT("Сравним?")])
    history = history_factory([("user", "hi"), ("assistant", "ok", "matching")])

    events = await collect(
        selection.run(ctx, ChatMessageIn(text="ок"), history, profile, agent_deps)
    )

    done = events[-1]
    assert isinstance(done, Done)
    assert done.mode == "refine"
    assert done.gave_task_instance_id is None


# --- postcheck in the chain ---


async def test_postcheck_revokes_number_without_source(
    monkeypatch, agent_deps, chat_ctx, profile_factory
):
    profile = profile_factory()
    patch_selection_io(monkeypatch, profile=profile)
    agent_deps.llm = FakeLLMClient([TXT("Обучение стоит 1 500 EUR в год.")])

    events = await collect(
        selection.run(
            chat_ctx(), ChatMessageIn(text="сколько?"), [], profile, agent_deps
        )
    )

    assert isinstance(events[-1], StreamError)
    assert events[-1].code == "postcheck_failed"


async def test_postcheck_allows_the_students_own_numbers(
    monkeypatch, agent_deps, chat_ctx, profile_factory
):
    profile = profile_factory(**{"academics.sat_score": 1300})
    patch_selection_io(monkeypatch, profile=profile)
    agent_deps.llm = FakeLLMClient([TXT("Записал бюджет 5000, SAT 1300.")])

    events = await collect(
        selection.run(
            chat_ctx(), ChatMessageIn(text="бюджет 5000"), [], profile, agent_deps
        )
    )

    assert isinstance(events[-1], Done)


async def test_more_than_two_questions_is_revoked(
    monkeypatch, agent_deps, chat_ctx, profile_factory
):
    profile = profile_factory()
    patch_selection_io(monkeypatch, profile=profile)
    agent_deps.llm = FakeLLMClient([TXT("Куда? Когда? Зачем?")])

    events = await collect(
        selection.run(chat_ctx(), ChatMessageIn(text="привет"), [], profile, agent_deps)
    )

    assert isinstance(events[-1], StreamError)
    assert events[-1].code == "postcheck_failed"
