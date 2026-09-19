"""Tutor: modes, hints, learner-model block, tools, postcheck
(docs/tz/phase3-agents.md §3.4–§3.5, §6.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agents import tutor
from app.agents.selection import save_program
from app.config import KnowledgeParams
from app.graph.context import TopicContext
from app.llm.fake import FakeLLMClient
from app.llm.tools import ToolCtx
from app.schemas.agents import TurnState
from app.schemas.chat import ChatMessageIn, Done, StreamError, ToolResult
from app.schemas.knowledge import EvidenceOut, ExamFormat, Section
from app.schemas.tasks import Option, OptionOut, TaskInstance, TaskInstanceOut
from tests.agents._scripts import TC, TXT, calls_turn, collect

pytestmark = pytest.mark.phase3

TOPIC = "math.alg.abs_value_eq"
PREREQ = "math.alg.linear_eq"


def _task_out(skill_id=TOPIC) -> TaskInstanceOut:
    return TaskInstanceOut(
        id=uuid4(),
        template_id="tpl",
        exam_id="SAT_MATH",
        type="mcq4",
        skill_id=skill_id,
        stem_rendered="Решите |x − 3| = 2",
        options=[
            OptionOut(key=k, text=t)
            for k, t in zip("ABCD", ["1", "5", "1 и 5", "−1"], strict=True)
        ],
        figure_url=None,
        time_reference_sec=60,
        difficulty=3,
        tags=[],
        mode="chat",
        provenance="template",
    )


def _context() -> TopicContext:
    return TopicContext(
        topic=["модуль — p=0.55 conf=0.80 trend=flat"],
        strengths=["линейные уравнения: p=0.88 conf=0.90"],
        skill_ids=[TOPIC, PREREQ],
        topic_name="модуль",
        set_label="сет 1 до 5 окт",
        as_of=datetime(2026, 9, 18, 12, tzinfo=UTC),
        cache="miss",
    )


@pytest.fixture
def prep(monkeypatch, agent_deps, chat_ctx, profile_factory):
    """A prep turn with context and session line faked."""
    ctx = chat_ctx("prep", set_id=uuid4(), topic_skill_id=TOPIC)
    context = AsyncMock(return_value=_context())
    monkeypatch.setattr(tutor.apply_context, "get_topic_context", context)
    info = tutor._Session(minute=12)
    monkeypatch.setattr(tutor, "_session_info", AsyncMock(return_value=info))
    issue = AsyncMock(side_effect=lambda *a, **k: _task_out(a[3].skill_id))
    monkeypatch.setattr(tutor.apply_tasks, "issue", issue)

    async def run(script, text="объясни", profile=None):
        agent_deps.llm = FakeLLMClient(script)
        return await collect(
            tutor.run(
                ctx,
                ChatMessageIn(text=text),
                [],
                profile or profile_factory(),
                agent_deps,
            )
        )

    return type(
        "Prep",
        (),
        {
            "ctx": ctx,
            "run": staticmethod(run),
            "issue": issue,
            "context": context,
            "deps": agent_deps,
        },
    )


def test_classify_mode_review_on_solution():
    assert tutor.classify_mode("2x−6=4, x=5") == "review"
    assert tutor.classify_mode("почему модуль раскрывается на две ветви?") == "explain"
    assert tutor.classify_mode("") == "explain"
    assert tutor.classify_mode("ответ: B") == "review"


def test_hint_level_base_from_profile(profile_factory):
    params = KnowledgeParams()
    assert (
        tutor.hint_level_for(
            profile_factory(**{"pace.hint_level": "minimal"}), 0, params
        )
        == 1
    )
    assert (
        tutor.hint_level_for(
            profile_factory(**{"pace.hint_level": "generous"}), 0, params
        )
        == 3
    )
    assert tutor.hint_level_for(profile_factory(), 0, params) == 2


def test_hint_level_escalates_after_two_failures(profile_factory):
    params = KnowledgeParams()
    assert tutor.hint_level_for(profile_factory(), 2, params) == 3
    assert tutor.hint_level_for(profile_factory(), 1, params) == 2
    assert (
        tutor.hint_level_for(
            profile_factory(**{"pace.hint_level": "generous"}), 5, params
        )
        == 3
    )


def test_render_learner_model_order_and_empty_slots():
    block = tutor.render_learner_model(
        TopicContext(strengths=["a"]),
        "модуль",
        "сет 1",
        datetime(2026, 9, 18, tzinfo=UTC),
    )
    lines = block.splitlines()
    assert (
        'topic="модуль"' in lines[0]
        and 'set="сет 1"' in lines[0]
        and "as_of=" in lines[0]
    )
    slots = [line.split(":")[0] for line in lines[1:-1]]
    assert slots == [
        "topic",
        "strengths",
        "prerequisite_gaps",
        "active_misconceptions",
        "under_watch",
        "low_data",
        "deadline",
        "profile",
        "previous_set",
    ]
    assert lines[1] == "topic: []"
    assert lines[2] == 'strengths: ["a"]'


async def test_system_prompt_contains_context_and_session(prep):
    await prep.run([TXT("Посмотрим.")], text="2x−6=4, x=5")

    system = prep.deps.llm.calls[0].messages[0].content
    assert "<learner_model" in system
    assert '<session minute="12" mode="review" hint_level="2"' in system


async def test_context_none_gives_empty_block(prep):
    prep.context.return_value = None

    events = await prep.run([TXT("Объясню по теме.")])

    system = prep.deps.llm.calls[0].messages[0].content
    assert "<learner_model" not in system
    assert "{{learner_model}}" not in system
    assert isinstance(events[-1], Done)


async def test_get_task_writes_task_issued_with_chat_id(prep):
    events = await prep.run([TC("get_task", {"skill_id": TOPIC}), TXT("Реши задачу.")])

    request = prep.issue.call_args.args[3]
    assert prep.issue.call_args.kwargs["chat_id"] == prep.ctx.chat_id
    assert request.mode == "chat"
    done = events[-1]
    assert done.mode == "task"
    result = next(e for e in events if isinstance(e, ToolResult))
    assert str(done.gave_task_instance_id) == result.data["task"]["id"]
    assert done.referenced_skill_ids == [TOPIC]


async def test_get_task_result_has_no_answer(prep):
    events = await prep.run([TC("get_task", {"skill_id": TOPIC}), TXT("Реши.")])

    data = next(e for e in events if isinstance(e, ToolResult)).data
    for option in data["task"]["options"]:
        assert set(option) == {"key", "text"}
    assert "answer" not in data["task"]
    assert "correct" not in str(data)
    assert "misconception_id" not in str(data)


async def test_get_task_second_call_denied(prep):
    events = await prep.run(
        [
            calls_turn(
                ("get_task", {"skill_id": TOPIC}), ("get_task", {"skill_id": TOPIC})
            ),
            TXT("Одна задача."),
        ]
    )

    results = [e for e in events if isinstance(e, ToolResult)]
    assert results[0].error is None
    assert results[1].error == "one task per turn"
    assert prep.issue.await_count == 1


async def test_get_task_outside_topic_denied(prep):
    events = await prep.run(
        [TC("get_task", {"skill_id": "math.geo.circle"}), TXT("Нет.")]
    )

    result = next(e for e in events if isinstance(e, ToolResult))
    assert result.error == "skill outside topic"
    prep.issue.assert_not_called()


async def test_explain_belief_maps_evidence_to_task_and_message(
    monkeypatch, agent_deps
):
    agent_deps.graph = object()
    instance_id, message_id, student_id = uuid4(), uuid4(), uuid4()
    now = datetime(2026, 9, 18, 12, tzinfo=UTC)
    evidence = [
        EvidenceOut(
            evidence_id="10:s:0",
            event_id=10,
            skill_id="s",
            kind="task",
            tier=2,
            source="task",
            weight=0.8,
            direction=-1,
            observed_at=now,
            summary=None,
            instance_id=instance_id,
            message_id=None,
        ),
        EvidenceOut(
            evidence_id="11:s:0",
            event_id=11,
            skill_id="s",
            kind="confusion",
            tier=3,
            source="chat",
            weight=0.6,
            direction=-1,
            observed_at=now.replace(hour=11),
            summary="не понял ветви",
            instance_id=None,
            message_id=message_id,
        ),
    ]
    monkeypatch.setattr(
        tutor.apply_knowledge, "explain", AsyncMock(return_value=evidence)
    )
    instance = TaskInstance(
        id=instance_id,
        template_id="t",
        seed=1,
        exam_id="SAT_MATH",
        type="mcq4",
        skill_id="s",
        stem_rendered="Условие",
        options=[Option(key="A", text="1", correct=True)],
        answer="A",
        trap_answers=[],
        solution_rendered=[],
        time_reference_sec=60,
        difficulty=3,
        tags=[],
    )
    monkeypatch.setattr(
        tutor.tasks_repo, "list_instances", AsyncMock(return_value=[instance])
    )
    monkeypatch.setattr(tutor.tasks_repo, "get_outcome", AsyncMock(return_value=False))
    answered = type(
        "E", (), {"payload": {"answer": "B"}, "type": tutor.EventType.task_answered}
    )
    monkeypatch.setattr(tutor.store, "get_event", AsyncMock(return_value=answered))
    message = type(
        "M",
        (),
        {"id": message_id, "text": "я не понял ветви модуля", "created_at": now},
    )
    monkeypatch.setattr(
        tutor.messages_repo, "get_message", AsyncMock(return_value=message)
    )
    ctx = ToolCtx(
        student_id=str(student_id), deps=agent_deps, request_id="r", turn=TurnState()
    )

    result = await tutor.TUTOR_TOOLS.call("explain_belief", {"skill_id": "s"}, ctx)

    assert result["node_kind"] == "skill"
    assert result["items"][0]["task"]["stem"] == "Условие"
    assert result["items"][0]["task"]["student_answer"] == "B"
    assert result["items"][0]["task"]["correct"] is False
    assert "не понял ветви" in result["items"][1]["message"]["text_fragment"]


async def test_explain_belief_graph_down(agent_deps):
    ctx = ToolCtx(student_id=str(uuid4()), deps=agent_deps, request_id="r")
    with pytest.raises(Exception, match="knowledge model unavailable"):
        await tutor.TUTOR_TOOLS.call("explain_belief", {"skill_id": "s"}, ctx)


def test_tutor_registry_stays_read_only():
    with pytest.raises(ValueError):
        tutor.TUTOR_TOOLS.register(save_program)


async def test_referenced_skill_ids_from_tool_calls(prep, monkeypatch):
    monkeypatch.setattr(tutor.apply_knowledge, "explain", AsyncMock(return_value=[]))
    prep.deps.graph = object()

    events = await prep.run(
        [TC("explain_belief", {"skill_id": PREREQ}), TXT("Вот почему.")],
        text="почему ты так думаешь?",
    )

    assert events[-1].referenced_skill_ids == [TOPIC, PREREQ]


async def test_postcheck_exam_facts_in_tutor(prep, monkeypatch):
    events = await prep.run([TXT("В модуле 22 задания")])
    assert isinstance(events[-1], StreamError)
    assert events[-1].code == "postcheck_failed"

    fmt = ExamFormat(
        exam_id="SAT_MATH",
        name="SAT",
        max_raw_score=44,
        sections=[
            Section(
                name="M1",
                n_items=22,
                minutes=35,
                item_types={},
                scoring_rule="",
                calculator=True,
                adaptive=True,
                area_shares={},
                difficulty_shares={},
                answer_forms=[],
            )
        ],
        source="cb",
        checked_at=datetime(2026, 9, 1).date(),
        is_demo=True,
    )
    from app.agents import selection

    prep.deps.graph = object()
    monkeypatch.setattr(
        selection.canonical_q, "get_exam_format", AsyncMock(return_value=fmt)
    )
    monkeypatch.setattr(selection.kb_q, "list_test_dates", AsyncMock(return_value=[]))
    monkeypatch.setattr(selection.kb_q, "list_facts_about", AsyncMock(return_value=[]))
    events = await prep.run(
        [TC("get_exam_format", {"exam_id": "SAT_MATH"}), TXT("В модуле 22 задания")]
    )
    assert isinstance(events[-1], Done)


async def test_math_numbers_pass_in_tutor(prep):
    events = await prep.run([TXT("x = 5 или x = 1")], text="2x−6=4, x=5")
    assert isinstance(events[-1], Done)
    assert events[-1].mode == "review"


async def test_tutor_may_quote_the_task_it_issued(prep):
    events = await prep.run(
        [
            TC("get_task", {"skill_id": TOPIC}),
            TXT("Реши |x − 3| = 2: ответы 1 и 5 проверь."),
        ]
    )
    assert isinstance(events[-1], Done)
