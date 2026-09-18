"""Chat entrypoint — dispatches an incoming message to the right agent.

Phase 1 note: every ``kind`` goes through the same echo path below — no
history, no tools, no branching. Phase 2 replaces the body of ``run_chat``
with a dispatch to ``selection.run`` / ``tutor.run``, each fed prior turns
loaded via ``db.repo.messages.list_messages`` instead of a bare two-message
list. Don't lose that when this file is next touched.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from neo4j import AsyncDriver
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.errors import LLMUnavailable
from app.llm.client import LLMLike
from app.llm.prompts import load_prompt
from app.schemas.chat import (
    ChatCtx,
    ChatKind,
    ChatMessageIn,
    Done,
    StreamError,
    StreamEvent,
)
from app.schemas.llm import LLMMessage


@dataclass
class AgentDeps:
    """Dependencies handed to every agent and, through it, every tool call.

    Constructed by B3 in ``api/chat.py`` from ``app.state`` (00-contracts.md
    §7); this is also the concrete type that ``app.llm.tools.ToolCtx.deps``
    refers to through its ``TYPE_CHECKING``-only import of this module — so
    this module must never import from ``app.llm.tools`` or ``app.agents.*``,
    only be imported by them.
    """

    llm: LLMLike
    pg: async_sessionmaker[AsyncSession]
    graph: AsyncDriver
    redis: Redis


_SYSTEM_PROMPT_NAME: dict[ChatKind, str] = {
    "selection": "selection",
    "prep": "tutor",
}


async def run_chat(
    kind: ChatKind,
    ctx: ChatCtx,
    message: ChatMessageIn,
    deps: AgentDeps,
) -> AsyncIterator[StreamEvent]:
    """Stream a reply to one chat message.

    Phase 1 is echo-only: exactly two messages go to the model — the
    ``kind``'s system prompt (``selection_v*`` for ``"selection"``,
    ``tutor_v*`` for ``"prep"``) and the user's text — via
    ``deps.llm.stream(messages, "chat")``, no ``tools``. Every ``TextDelta``
    the model yields is forwarded unchanged; the stream always ends with a
    ``Done`` whose ``event_id`` is a placeholder (the real id is assigned by
    B3's transport when it persists the message) and whose other markup
    fields are empty, since phase 1 has no mode, no issued task, no hint
    level and nothing to reference.

    ``LLMUnavailable`` raised by the model *before* any event has been
    yielded propagates unchanged, so B3's transport can still turn it into a
    503 — no response bytes have gone out yet. Once streaming has started,
    that option is gone (headers are already on the wire), so the same
    error is instead surfaced as a ``StreamError`` — the last event of the
    stream. This is the opposite of ``app.llm.loop.run_tool_loop``, which
    always turns ``LLMUnavailable`` into a ``StreamError`` regardless of
    position; don't carry that rule over here.
    """
    prompt = load_prompt(_SYSTEM_PROMPT_NAME[kind])
    messages = [
        LLMMessage(role="system", content=prompt.text),
        LLMMessage(role="user", content=message.text),
    ]

    yielded_any = False
    try:
        async for event in deps.llm.stream(messages, "chat"):
            yielded_any = True
            yield event
    except LLMUnavailable as exc:
        if not yielded_any:
            raise
        yield StreamError(code="llm_unavailable", message=str(exc))
        return

    yield Done(
        event_id=0,
        mode=None,
        gave_task_instance_id=None,
        hint_level=None,
        referenced_skill_ids=[],
    )
