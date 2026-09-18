"""Authenticated chat transport; agent behavior belongs to B2."""

import inspect
from collections.abc import AsyncIterator
from importlib import import_module
from typing import Annotated, Any
from uuid import UUID, uuid5

from fastapi import APIRouter, Depends, Query, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_student, get_redis, get_session
from app.api.sse import sse_response
from app.db.repo import messages
from app.errors import AppError, LLMUnavailable, ValidationFailed
from app.events import store
from app.events.session import current_session_id
from app.schemas.auth import StudentCtx
from app.schemas.chat import (
    AssistantMarkup,
    ChatCtx,
    ChatKind,
    ChatMessageIn,
    Done,
    MessageOut,
    StreamError,
    StreamEvent,
    TextDelta,
)
from app.schemas.events import EventIn, EventType, MessageAssistantPayload

router = APIRouter(prefix="/chat", tags=["chat"])


def _agent_router() -> Any:
    """Import the agreed B2 interface, without a production fallback agent."""
    try:
        return import_module("app.agents.router")
    except ModuleNotFoundError as exc:
        if exc.name and "app.agents.router".startswith(exc.name):
            raise LLMUnavailable("LLM unavailable") from exc
        raise


def _chat_id(student_id: UUID, kind: ChatKind, body: ChatMessageIn) -> UUID:
    if kind == "selection":
        return uuid5(student_id, "selection")
    if body.set_id is None or not body.topic_skill_id:
        raise ValidationFailed("prep chat requires set_id and topic_skill_id")
    return uuid5(student_id, f"prep:{body.set_id}:{body.topic_skill_id}")


async def _wrap_agent(
    stream: AsyncIterator[StreamEvent],
    first: StreamEvent,
    request: Request,
    ctx: ChatCtx,
    redis: Redis,
) -> AsyncIterator[StreamEvent]:
    text_parts: list[str] = []
    try:

        async def events() -> AsyncIterator[StreamEvent]:
            yield first
            async for event in stream:
                yield event

        async for event in events():
            if isinstance(event, TextDelta):
                text_parts.append(event.text)
                yield event
            elif isinstance(event, Done):
                text = "".join(text_parts)
                markup = AssistantMarkup(
                    mode=event.mode,
                    gave_task_instance_id=event.gave_task_instance_id,
                    hint_level=event.hint_level,
                    referenced_skill_ids=event.referenced_skill_ids,
                )
                payload = MessageAssistantPayload(
                    text=text,
                    mode=event.mode
                    if event.mode in {"explain", "review", "task"}
                    else None,
                    gave_task_instance_id=event.gave_task_instance_id,
                    hint_level=event.hint_level,
                    referenced_skill_ids=event.referenced_skill_ids,
                )
                async with request.app.state.sessionmaker() as session:
                    saved = await store.append(
                        session,
                        redis,
                        EventIn(
                            type=EventType.message_assistant,
                            payload=payload.model_dump(mode="json"),
                            student_id=ctx.student_id,
                            session_id=ctx.session_id,
                            chat_id=ctx.chat_id,
                            set_id=ctx.set_id,
                            topic_skill_id=ctx.topic_skill_id,
                        ),
                    )
                    await messages.append_message(
                        session,
                        ctx.student_id,
                        ctx.chat_id,
                        "assistant",
                        text,
                        markup,
                        saved.id,
                    )
                    await session.commit()
                yield event.model_copy(update={"event_id": saved.id})
                return
            else:
                yield event
                if isinstance(event, StreamError):
                    return
        yield StreamError(
            code="internal", message="Assistant stream ended unexpectedly"
        )
    except Exception as exc:
        code = exc.code if isinstance(exc, AppError) else "internal"
        yield StreamError(code=code, message="Assistant unavailable")
    finally:
        close = getattr(stream, "aclose", None)
        if close is not None:
            await close()


@router.post("/{kind}/messages")
async def post_message(
    kind: ChatKind,
    body: ChatMessageIn,
    request: Request,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    chat_id = _chat_id(student.student_id, kind, body)
    agent_router = _agent_router()
    llm = getattr(request.app.state, "llm", None)
    if llm is None:
        raise LLMUnavailable("LLM unavailable")
    session_id = await current_session_id(redis, student.student_id)
    ctx = ChatCtx(
        student_id=student.student_id,
        kind=kind,
        chat_id=chat_id,
        session_id=session_id,
        request_id=request.state.request_id,
        topic_skill_id=body.topic_skill_id,
        set_id=body.set_id,
    )
    async with request.app.state.sessionmaker() as session:
        saved = await store.append(
            session,
            redis,
            EventIn(
                type=EventType.message_user,
                payload={"text": body.text},
                student_id=student.student_id,
                session_id=session_id,
                chat_id=chat_id,
                set_id=body.set_id,
                topic_skill_id=body.topic_skill_id,
            ),
        )
        await messages.append_message(
            session, student.student_id, chat_id, "user", body.text, None, saved.id
        )
        await session.commit()

    deps = agent_router.AgentDeps(
        llm=llm,
        pg=request.app.state.sessionmaker,
        graph=request.app.state.neo4j,
        redis=redis,
    )
    stream = agent_router.run_chat(kind, ctx, body, deps)
    if inspect.isawaitable(stream):
        stream = await stream
    try:
        first = await anext(stream)
    except LLMUnavailable:
        close = getattr(stream, "aclose", None)
        if close is not None:
            await close()
        raise
    except StopAsyncIteration:
        first = StreamError(code="internal", message="Assistant unavailable")
    except Exception:
        first = StreamError(code="internal", message="Assistant unavailable")
    return sse_response(_wrap_agent(stream, first, request, ctx, redis))


@router.get("/{kind}/messages", response_model=list[MessageOut])
async def get_messages(
    kind: ChatKind,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    set_id: UUID | None = None,
    topic_skill_id: str | None = None,
) -> list[MessageOut]:
    chat_id = _chat_id(
        student.student_id,
        kind,
        ChatMessageIn(text="", set_id=set_id, topic_skill_id=topic_skill_id),
    )
    return await messages.list_messages(session, student.student_id, chat_id, limit)
