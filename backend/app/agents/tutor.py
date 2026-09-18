"""Tutor — stub run() and its read-only tool registry (docs/tz/30-B2.md §5.3).

The tutor teaches, it doesn't grade, and it never writes to the knowledge
model (memory-architecture §9.4: "репетитор знает, но не охотится" —
misconceptions are for interpreting an error when one happens, never the
subject of the conversation). ``TUTOR_TOOLS`` enforces the "read-only" half
of that mechanically: it is built with ``read_only=True``, so
``ToolRegistry.register`` raises ``ValueError`` on any spec that isn't
itself ``read_only`` — a writing tool (e.g. ``selection.save_program``)
cannot end up in this registry by accident.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel, Field

from app.agents.router import AgentDeps
from app.agents.selection import get_exam_format
from app.llm.tools import ToolCtx, ToolRegistry, tool
from app.schemas.chat import ChatCtx, ChatMessageIn, MessageOut, StreamEvent
from app.schemas.profile import Profile


async def run(
    ctx: ChatCtx,
    message: ChatMessageIn,
    history: list[MessageOut],
    profile: Profile,
    deps: AgentDeps,
) -> AsyncIterator[StreamEvent]:
    """Drive one turn of the prep chat (memory-architecture §9.4).

    Stub for phase 1: the real implementation picks "explain" vs. "review"
    mode from the student's last message, injects the learner context
    (``<learner_model>``, memory-architecture §9.3 — assembled by the
    framework via ``get_learner_context``, never exposed to the model as a
    callable tool) and runs the tool-calling loop over ``TUTOR_TOOLS``,
    landing in phase 2. Also still missing at this point: the topic context
    B1 builds (``TopicContext``) — this signature does not carry it yet
    since B1 hasn't published the type; phase 2 threads it in once it
    exists. ``history`` and ``profile`` are typed the same way as in
    ``selection.run`` — both already have real contracts.
    """
    raise NotImplementedError("phase 2")


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
async def explain_belief(args: ExplainBeliefArgs, ctx: ToolCtx) -> Any:
    raise NotImplementedError("phase 2")


class GetTaskArgs(BaseModel):
    skill_id: str = Field(description="Canonical or personal skill to pull a task for.")
    difficulty: int | None = Field(
        default=None,
        description=(
            "Target difficulty on the exam's own scale. Leave unset to let "
            "the pool pick a difficulty appropriate to the student's "
            "current level."
        ),
    )


@tool(
    name="get_task",
    description=(
        "Pulls one task instance for the given skill from the practice "
        "pool into the conversation, preferring tasks the student hasn't "
        "seen yet, and records that it was issued. Use it to hand over a "
        "concrete problem when that's the natural next step in the "
        "conversation — not to turn the chat into a quiz (at most one task "
        "per exchange)."
    ),
    read_only=True,
)
async def get_task(args: GetTaskArgs, ctx: ToolCtx) -> Any:
    raise NotImplementedError("phase 2")


TUTOR_TOOLS = ToolRegistry(read_only=True)
for _spec in (explain_belief, get_task, get_exam_format):
    TUTOR_TOOLS.register(_spec)
del _spec
