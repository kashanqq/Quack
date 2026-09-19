"""Tutor — one prep-chat turn and its read-only tool registry.

Source: docs/tz/phase3-agents.md §3.4–§3.5; memory-architecture §9.3–§9.5;
phase-1 registry: docs/tz/30-B2.md §5.3.

The tutor teaches, it doesn't grade, and it never writes to the knowledge
model (memory-architecture §9.4: "репетитор знает, но не охотится" —
misconceptions are for interpreting an error when one happens, never the
subject of the conversation). ``TUTOR_TOOLS`` enforces the "read-only" half
of that mechanically: it is built with ``read_only=True``, so
``ToolRegistry.register`` raises ``ValueError`` on any spec that isn't
itself ``read_only`` — a writing tool (e.g. ``selection.save_program``)
cannot end up in this registry by accident. `get_task` records only the
issued instance and its `task.issued` event — handing out a task, not a
write to the learner model.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

import structlog
from pydantic import BaseModel, Field

from app.agents import postcheck
from app.agents._deps import rule_deps
from app.agents.router import AgentDeps
from app.agents.selection import get_exam_format
from app.apply import context as apply_context
from app.apply import knowledge as apply_knowledge
from app.apply import tasks as apply_tasks
from app.config import KnowledgeParams, settings
from app.db.repo import messages as messages_repo
from app.db.repo import tasks as tasks_repo
from app.errors import ValidationFailed
from app.events import store
from app.events.session import session_minute
from app.graph.context import SLOT_ORDER, TopicContext
from app.llm.loop import LoopEnd, run_tool_loop
from app.llm.prompts import load_prompt
from app.llm.tools import ToolCtx, ToolRegistry, tool
from app.schemas.agents import (
    BeliefItem,
    BeliefMessage,
    BeliefTask,
    ExplainBeliefResult,
    GetTaskResult,
    TurnState,
)
from app.schemas.chat import (
    ChatCtx,
    ChatMessageIn,
    Done,
    MessageOut,
    StreamError,
    StreamEvent,
)
from app.schemas.events import EventType
from app.schemas.llm import LLMMessage
from app.schemas.profile import Profile
from app.schemas.tasks import TaskInstance, TaskRequestIn

_logger = structlog.get_logger(__name__)

Mode = Literal["explain", "review"]
_MAX_STEPS = 4
_BELIEF_ITEMS = 10
_FRAGMENT_CHARS = 300
_POSTCHECK_MESSAGE = (
    "Ответ отозван: в нём есть данные, которых нет в результатах инструментов"
)
_HINT_BASE = {"minimal": 1, "normal": 2, "generous": 3}

# --- explain / review (§3.4 «Режимы») ---

_EQUATION_RE = re.compile(r"\d[^=\n]*=[^=\n]*\d")
_OPERATOR_LINE_RE = re.compile(r"[=+\-−*/^×÷<>≤≥]")
_REVIEW_WORDS_RE = re.compile(
    r"решил|решила|получил|получила|получилось|ответ|проверь|вот мо[её]|"
    r"я думаю что|правильно|верно ли",
    re.IGNORECASE,
)
_TASK_ANSWER_RE = re.compile(r"ответ\s*[:\-—]?\s*[A-EА-Е]\b", re.IGNORECASE)
_EXPLAIN_WORDS_RE = re.compile(r"объясни|почему|как |что такое", re.IGNORECASE)


def classify_mode(text: str) -> Mode:
    """«разбираю» when the message carries a solution, «объясняю» otherwise;
    a tie goes to «объясняю» — misconceptions only come up in review (§9.4)."""
    text = text or ""
    review = 0
    if _EQUATION_RE.search(text):
        review += 1
    if sum(1 for line in text.splitlines() if _OPERATOR_LINE_RE.search(line)) >= 2:
        review += 1
    if _REVIEW_WORDS_RE.search(text):
        review += 1
    if _TASK_ANSWER_RE.search(text):
        review += 1
    explain = 0
    if "?" in text:
        explain += 1
    if _EXPLAIN_WORDS_RE.search(text + " "):
        explain += 1
    return "review" if review > explain else "explain"


def hint_level_for(
    profile: Profile, consecutive_failures: int, params: KnowledgeParams
) -> int:
    """The profile's hint level (1..3, default 2), one step up after
    `tutor_escalate_after_failures` failed chat tasks in a row."""
    value = profile.questionnaire.pace.hint_level.value
    base = _HINT_BASE.get(value, 2) if value else 2
    if consecutive_failures >= params.tutor_escalate_after_failures:
        return min(3, base + 1)
    return base


def render_learner_model(
    context: TopicContext, topic_name: str, set_label: str, as_of: datetime
) -> str:
    """The §9.3 block: fixed slot order, an empty slot printed as `[]`."""
    header = (
        f'<learner_model topic="{topic_name}" set="{set_label}" '
        f'as_of="{as_of.isoformat(timespec="minutes")}">'
    )
    lines = [header]
    for name in SLOT_ORDER:
        lines.append(
            f"{name}: {json.dumps(getattr(context, name), ensure_ascii=False)}"
        )
    lines.append("</learner_model>")
    return "\n".join(lines)


@dataclass
class _Session:
    minute: int = 0
    last_task: Literal["correct", "incorrect", "none"] = "none"
    last_task_skill: str | None = None
    consecutive_failures: int = 0
    issued_in_chat: TaskInstance | None = None


def session_line(info: _Session, mode: Mode, hint_level: int, escalate: bool) -> str:
    issued = str(info.issued_in_chat.id) if info.issued_in_chat else "-"
    return (
        f'<session minute="{info.minute}" mode="{mode}" hint_level="{hint_level}" '
        f'escalate="{"yes" if escalate else "no"}" last_task="{info.last_task}" '
        f'last_task_skill="{info.last_task_skill or "-"}" '
        f'issued_in_chat="{issued}" />'
    )


async def _session_info(deps: AgentDeps, ctx: ChatCtx, now: datetime) -> _Session:
    info = _Session()
    try:
        async with deps.pg() as session:
            info.minute = await session_minute(
                session, ctx.student_id, ctx.session_id, now
            )
            answered = await store.list_by_type(
                session,
                ctx.student_id,
                [EventType.task_answered],
                None,
                200,
                session_id=ctx.session_id,
            )
            if answered:
                last = answered[-1]
                instance_id = UUID(str(last.payload.get("instance_id")))
                correct = await tasks_repo.get_outcome(
                    session, ctx.student_id, instance_id
                )
                if correct is not None:
                    info.last_task = "correct" if correct else "incorrect"
                instance = await tasks_repo.get_instance(
                    session, ctx.student_id, instance_id
                )
                info.last_task_skill = instance.skill_id if instance else None
            outcomes = await tasks_repo.chat_outcomes(
                session, ctx.student_id, ctx.chat_id
            )
            for outcome in reversed(outcomes):
                if outcome:
                    break
                info.consecutive_failures += 1
            open_tasks = await tasks_repo.list_open_chat_instances(
                session, ctx.student_id, ctx.chat_id
            )
            info.issued_in_chat = open_tasks[-1] if open_tasks else None
    except Exception:  # noqa: BLE001 — the line degrades, the turn goes on
        _logger.warning("tutor_session_line_failed", chat_id=str(ctx.chat_id))
        return _Session()
    return info


async def _context(deps: AgentDeps, ctx: ChatCtx) -> TopicContext | None:
    if ctx.set_id is None:
        return None
    try:
        async with deps.pg() as session:
            return await apply_context.get_topic_context(
                session, rule_deps(deps), ctx.student_id, ctx.set_id, ctx.topic_skill_id
            )
    except Exception:  # noqa: BLE001 — no context is better than no answer
        _logger.warning("ctx_topic", error="failed", chat_id=str(ctx.chat_id))
        return None


def _task_values(instance: Any) -> list[Any]:
    """Numbers of a task's stem and options — the maths the tutor may quote."""
    if instance is None:
        return []
    texts = [getattr(instance, "stem_rendered", "") or ""]
    texts.extend(option.text for option in getattr(instance, "options", []) or [])
    values: list[Any] = []
    for text in texts:
        values.extend(postcheck.numbers_and_dates(text))
    return values


async def run(
    ctx: ChatCtx,
    message: ChatMessageIn,
    history: list[MessageOut],
    profile: Profile,
    deps: AgentDeps,
) -> AsyncIterator[StreamEvent]:
    """Drive one turn of the prep chat (memory-architecture §9.4)."""
    params = settings.knowledge
    now = datetime.now(UTC)
    context = await _context(deps, ctx)
    info = await _session_info(deps, ctx, now)
    mode = classify_mode(message.text)
    hint_level = hint_level_for(profile, info.consecutive_failures, params)
    escalate = info.consecutive_failures >= params.tutor_escalate_after_failures

    block = (
        render_learner_model(
            context,
            context.topic_name or (ctx.topic_skill_id or ""),
            context.set_label,
            context.as_of or now,
        )
        if context is not None
        else ""
    )
    system = load_prompt("tutor").render(
        learner_model=block, session=session_line(info, mode, hint_level, escalate)
    )
    messages = [
        LLMMessage(role="system", content=system),
        *(LLMMessage(role=m.role, content=m.text) for m in history),
        LLMMessage(role="user", content=message.text),
    ]
    _logger.info(
        "chat_turn_started",
        kind="prep",
        chat_id=str(ctx.chat_id),
        mode=mode,
        hint_level=hint_level,
        ctx=context.cache if context is not None else "none",
    )

    turn = TurnState()
    turn["hint_level"] = hint_level
    turn["topic_skill_ids"] = (
        list(context.skill_ids)
        if context is not None and context.skill_ids
        else ([ctx.topic_skill_id] if ctx.topic_skill_id else [])
    )
    tool_ctx = ToolCtx(
        student_id=str(ctx.student_id),
        deps=deps,
        request_id=ctx.request_id,
        chat=ctx,
        turn=turn,
    )
    end: LoopEnd | None = None
    async for event in run_tool_loop(
        deps.llm, TUTOR_TOOLS, messages, "chat", tool_ctx, max_steps=_MAX_STEPS
    ):
        if isinstance(event, LoopEnd):
            end = event
            continue
        yield event
        if isinstance(event, StreamError):
            _logger.info("chat_turn_done", kind="prep", error=event.code)
            return
    assert end is not None

    issued_now = turn.get("issued_task")
    check = postcheck.check_facts(
        end.text_full,
        end.tool_results,
        scope="exam_facts",
        extra_values=[
            *postcheck.numbers_and_dates(message.text),
            *_task_values(issued_now),
            *_task_values(info.issued_in_chat),
        ],
    )
    _logger.info(
        "postcheck",
        kind="prep",
        scope="exam_facts",
        ok=check.ok,
        mismatches=check.mismatches,
        questions=check.questions,
        text_len=len(end.text_full),
        tools=[r.tool for r in end.tool_results],
    )
    if not check.ok:
        yield StreamError(code="postcheck_failed", message=_POSTCHECK_MESSAGE)
        return

    ok_calls = {r.call_id for r in end.tool_results if r.error is None}
    referenced: list[str] = [ctx.topic_skill_id] if ctx.topic_skill_id else []
    for call in end.tool_calls:
        if call.call_id in ok_calls and call.tool in ("get_task", "explain_belief"):
            skill_id = call.args.get("skill_id")
            if isinstance(skill_id, str) and skill_id not in referenced:
                referenced.append(skill_id)
    gave = turn.get("gave_task_instance_id")
    _logger.info(
        "chat_turn_done",
        kind="prep",
        steps=end.steps,
        text_len=len(end.text_full),
        tools=[r.tool for r in end.tool_results],
    )
    yield Done(
        event_id=0,
        mode="task" if gave is not None else mode,
        gave_task_instance_id=gave,
        hint_level=hint_level,
        referenced_skill_ids=referenced,
    )


# --- tools ---


class ExplainBeliefArgs(BaseModel):
    skill_id: str = Field(
        description=(
            "Id of the skill or misconception the tutor should justify its "
            "belief about (memory-architecture §9.5: 'Skill / "
            "Misconception'). Use only when the student explicitly asks "
            "why the tutor thinks something about them ('why do you think "
            "that') — never to bring up a misconception on your own."
        )
    )


class KnowledgeModelUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("knowledge model unavailable")


def _fragment(text: str, summary: str | None) -> str:
    """≤ 300 characters of the message around the observer's summary."""
    if summary:
        at = text.lower().find(summary.lower())
        if at >= 0:
            start = max(0, at - (_FRAGMENT_CHARS - len(summary)) // 2)
            return text[start : start + _FRAGMENT_CHARS]
    return text[:_FRAGMENT_CHARS]


@tool(
    name="explain_belief",
    description=(
        "Expands the tutor's current belief about one skill or "
        "misconception into the evidence behind it — past observations "
        "with their event id, the task text and the student's answer, or "
        "the relevant snippet of what they said. Call it only in response "
        "to the student directly asking why the tutor believes something "
        "about their knowledge; it is not a way to introduce a "
        "misconception into the conversation yourself."
    ),
    read_only=True,
)
async def explain_belief(args: ExplainBeliefArgs, ctx: ToolCtx) -> ExplainBeliefResult:
    if ctx.deps.graph is None:
        raise KnowledgeModelUnavailable()
    student_id = UUID(str(ctx.student_id))
    node_id = args.skill_id
    evidence = await apply_knowledge.explain(rule_deps(ctx.deps), student_id, node_id)
    evidence = sorted(evidence, key=lambda e: (e.observed_at, e.event_id), reverse=True)
    evidence = evidence[:_BELIEF_ITEMS]

    items: list[BeliefItem] = []
    async with ctx.deps.pg() as session:
        instance_ids = [e.instance_id for e in evidence if e.instance_id is not None]
        instances = {
            i.id: i
            for i in await tasks_repo.list_instances(session, student_id, instance_ids)
        }
        for e in evidence:
            task = None
            if e.instance_id is not None and e.instance_id in instances:
                answered = await store.get_event(session, student_id, e.event_id)
                answer = (
                    answered.payload.get("answer")
                    if answered is not None and answered.type == EventType.task_answered
                    else None
                )
                task = BeliefTask(
                    instance_id=e.instance_id,
                    stem=instances[e.instance_id].stem_rendered,
                    student_answer=answer,
                    correct=await tasks_repo.get_outcome(
                        session, student_id, e.instance_id
                    ),
                )
            message = None
            if e.message_id is not None:
                found = await messages_repo.get_message(
                    session, student_id, e.message_id
                )
                if found is not None:
                    message = BeliefMessage(
                        message_id=found.id,
                        text_fragment=_fragment(found.text, e.summary),
                        created_at=found.created_at,
                    )
            items.append(
                BeliefItem(
                    evidence_id=e.evidence_id,
                    event_id=e.event_id,
                    kind=e.kind,
                    source=e.source,
                    tier=e.tier,
                    direction=e.direction,
                    weight=e.weight,
                    observed_at=e.observed_at,
                    summary=e.summary,
                    task=task,
                    message=message,
                )
            )
    return ExplainBeliefResult(
        node_id=node_id,
        node_kind="misconception" if node_id.startswith(("lib.", "pers.")) else "skill",
        items=items,
    )


class GetTaskArgs(BaseModel):
    skill_id: str = Field(description="Canonical or personal skill to pull a task for.")
    difficulty: int | None = Field(
        default=None,
        description=(
            "Target difficulty on the exam's own scale (1–5). Leave unset to "
            "let the pool pick a difficulty appropriate to the student's "
            "recent answers."
        ),
    )
    with_trap: str | None = Field(
        default=None,
        description=(
            "Misconception id the task should set a trap for (a distractor "
            "built on it). Only in review mode, for a misconception already "
            "seen in this conversation; leave unset otherwise."
        ),
    )
    exclude_seen: bool = Field(
        default=True,
        description="Prefer templates the student has not seen yet.",
    )


class OneTaskPerTurn(ValidationFailed):
    def __init__(self) -> None:
        super().__init__("one task per turn")


@tool(
    name="get_task",
    description=(
        "Pulls one task instance for the given skill from the practice "
        "pool into the conversation, preferring tasks the student hasn't "
        "seen yet, and records that it was issued. Use it to hand over a "
        "concrete problem when that's the natural next step in the "
        "conversation — not to turn the chat into a quiz (at most one task "
        "per exchange). The skill must be the topic or one of its "
        "prerequisites."
    ),
    read_only=True,
)
async def get_task(args: GetTaskArgs, ctx: ToolCtx) -> GetTaskResult:
    turn = ctx.turn
    if turn.get("task_issued", 0) >= 1:
        raise OneTaskPerTurn()
    allowed = turn.get("topic_skill_ids") or []
    if allowed and args.skill_id not in allowed:
        raise ValidationFailed("skill outside topic")
    chat = ctx.chat
    student_id = UUID(str(ctx.student_id))
    async with ctx.deps.pg() as session:
        out = await apply_tasks.issue(
            session,
            rule_deps(ctx.deps),
            student_id,
            TaskRequestIn(
                skill_id=args.skill_id,
                set_id=chat.set_id if chat else None,
                mode="chat",
                with_trap=args.with_trap,
                exclude_seen=args.exclude_seen,
                difficulty=args.difficulty,
            ),
            chat_id=chat.chat_id if chat else None,
        )
        await session.commit()
    turn["task_issued"] = 1
    turn["gave_task_instance_id"] = out.id
    turn["issued_task"] = out
    return GetTaskResult(task=out, hint_level=int(turn.get("hint_level", 2)))


TUTOR_TOOLS = ToolRegistry(read_only=True)
for _spec in (explain_belief, get_task, get_exam_format):
    TUTOR_TOOLS.register(_spec)
del _spec
