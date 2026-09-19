"""Chat entrypoint — dispatches an incoming message to the right agent.

Phase 3 (docs/tz/phase3-agents.md §3.1): load the chat's recent history and
the student's profile, hand the turn to `selection.run` (kind="selection") or
`tutor.run` (kind="prep"), and pass the agent's stream through unchanged.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import structlog
from neo4j import AsyncDriver
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.db.repo import messages as messages_repo
from app.db.repo import profiles as profiles_repo
from app.errors import LLMUnavailable
from app.llm.client import LLMLike
from app.schemas.chat import (
    ChatCtx,
    ChatKind,
    ChatMessageIn,
    MessageOut,
    StreamError,
    StreamEvent,
)

_logger = structlog.get_logger(__name__)


@dataclass
class AgentDeps:
    """Dependencies handed to every agent and, through it, every tool call.

    Constructed by B3 in ``api/chat.py`` from ``app.state`` (00-contracts.md
    §7); this is also the concrete type that ``app.llm.tools.ToolCtx.deps``
    refers to through its ``TYPE_CHECKING``-only import of this module — so
    this module must never import from ``app.llm.tools`` or ``app.agents.*``
    at import time, only be imported by them (the agents are imported lazily
    inside ``run_chat``).
    """

    llm: LLMLike
    pg: async_sessionmaker[AsyncSession]
    graph: AsyncDriver
    redis: Redis


def drop_current(history: list[MessageOut], text: str) -> list[MessageOut]:
    """The transport has already stored the current message; the agent adds
    it itself as the last one, so a trailing copy in the history goes."""
    if history and history[-1].role == "user" and history[-1].text == text:
        return history[:-1]
    return history


async def run_chat(
    kind: ChatKind,
    ctx: ChatCtx,
    message: ChatMessageIn,
    deps: AgentDeps,
) -> AsyncIterator[StreamEvent]:
    """Stream a reply to one chat message.

    ``LLMUnavailable`` before any event has been yielded propagates, so B3's
    transport can still turn it into a 503 — no response bytes have gone out
    yet. An agent reports an unavailable model as
    ``StreamError(code="llm_unavailable")``; when that is its very first
    event, it is raised here as ``LLMUnavailable`` for the same reason. Any
    later ``StreamError`` is passed through and ends the stream.
    """
    from app.agents import selection, tutor

    window = settings.knowledge.chat_window
    async with deps.pg() as session:
        history = await messages_repo.list_messages(
            session, ctx.student_id, ctx.chat_id, limit=window + 1
        )
        profile = await profiles_repo.get_profile(session, ctx.student_id)
    history = drop_current(history, message.text)[-window:]
    _logger.info(
        "chat_turn_started",
        kind=kind,
        chat_id=str(ctx.chat_id),
        history_len=len(history),
    )

    agent = selection.run if kind == "selection" else tutor.run
    stream = agent(ctx, message, history, profile, deps)
    first = True
    try:
        async for event in stream:
            if (
                first
                and isinstance(event, StreamError)
                and event.code == "llm_unavailable"
            ):
                raise LLMUnavailable(event.message)
            first = False
            yield event
            if isinstance(event, StreamError):
                return
    finally:
        await stream.aclose()
