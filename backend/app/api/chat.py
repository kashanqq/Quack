"""Authenticated chat transport; agent behavior belongs to B2.

Phase 3 (docs/tz/phase3-agents.md §3.12): one turn per chat at a time (a
Redis lock, 409 while busy), chat replies stored without dispatch (their
`processed_at` belongs to the observer), the observer queued every
`observer_every_n` unprocessed messages of a prep chat, the «обновить модель
знаний» button and its diff, and the set-level prep chat.
"""

import inspect
from collections.abc import AsyncIterator
from importlib import import_module
from typing import Annotated, Any
from uuid import UUID, uuid5

import structlog
from fastapi import APIRouter, Depends, Query, Request, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app import keys
from app.api.deps import (
    get_arq,
    get_current_student,
    get_redis,
    get_rule_deps,
    get_session,
)
from app.api.sse import sse_response
from app.apply import knowledge as apply_knowledge
from app.config import settings
from app.db.repo import messages
from app.db.repo import sets as sets_repo
from app.errors import (
    AppError,
    Conflict,
    LLMUnavailable,
    NotFound,
    TooManyRequests,
    ValidationFailed,
)
from app.events import store, version
from app.events.dispatch import RuleDeps
from app.events.session import current_session_id
from app.graph.queries import personal
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
from app.schemas.events import (
    EventIn,
    EventType,
    MessageAssistantPayload,
    ObservationExtractedPayload,
    ObserverRequestedPayload,
)
from app.schemas.observer import (
    ObservationsDiffOut,
    ObservationView,
    ObserveRequestedOut,
    ObserveRequestIn,
)
from app.workers.queue import enqueue

router = APIRouter(prefix="/chat", tags=["chat"])
_logger = structlog.get_logger(__name__)

_MESSAGE_TYPES = [EventType.message_user, EventType.message_assistant]
_OBSERVE_RATE_LIMIT_S = 10


def _agent_router() -> Any:
    """Import the agreed B2 interface, without a production fallback agent."""
    try:
        return import_module("app.agents.router")
    except ModuleNotFoundError as exc:
        if exc.name and "app.agents.router".startswith(exc.name):
            raise LLMUnavailable("LLM unavailable") from exc
        raise


def chat_id_for(
    student_id: UUID,
    kind: ChatKind,
    set_id: UUID | None = None,
    topic_skill_id: str | None = None,
) -> UUID:
    """The stable id of one chat — the key the observer window is read by.

    A prep chat without a topic is the set's own chat (phase 3, F20).
    """
    if kind == "selection":
        return uuid5(student_id, "selection")
    if set_id is None:
        raise ValidationFailed("prep chat requires set_id")
    if not topic_skill_id:
        return uuid5(student_id, f"prep:{set_id}")
    return uuid5(student_id, f"prep:{set_id}:{topic_skill_id}")


def _chat_id(student_id: UUID, kind: ChatKind, body: ChatMessageIn) -> UUID:
    return chat_id_for(student_id, kind, body.set_id, body.topic_skill_id)


# --- one turn per chat ---


async def _take_chat_lock(redis: Redis, chat_id: UUID, request_id: str) -> bool:
    """True — the lock is ours; False — Redis is down (the turn is allowed).
    A lock held by another request is a 409."""
    try:
        taken = await redis.set(
            keys.lock(f"chat:{chat_id}"),
            request_id,
            nx=True,
            ex=settings.CHAT_LOCK_TTL_S,
        )
    except Exception:  # noqa: BLE001
        _logger.warning("chat_lock_unavailable", chat_id=str(chat_id))
        return False
    if not taken:
        raise Conflict("assistant is still answering")
    return True


async def _release_chat_lock(redis: Redis, chat_id: UUID, request_id: str) -> None:
    key = keys.lock(f"chat:{chat_id}")
    try:
        current = await redis.get(key)
        if (
            current is not None
            and (current.decode() if isinstance(current, bytes) else current)
            == request_id
        ):
            await redis.delete(key)
    except Exception:  # noqa: BLE001
        _logger.warning("chat_lock_release_failed", chat_id=str(chat_id))


# --- the observer trigger ---


async def _trigger_observer(request: Request, ctx: ChatCtx) -> None:
    """Queue the observer once the chat has `observer_every_n` unprocessed
    messages. A failure here never breaks the student's answer."""
    try:
        async with request.app.state.sessionmaker() as session:
            count = await store.count_unprocessed(session, ctx.chat_id, _MESSAGE_TYPES)
        if count < settings.knowledge.observer_every_n:
            return
        arq = getattr(request.app.state, "arq", None)
        if arq is None:
            _logger.warning("observer_not_enqueued", reason="queue_unavailable")
            return
        job_id = await enqueue(
            arq,
            "interactive",
            "observe_chat",
            _job_id=f"observe:{ctx.chat_id}",
            chat_id=ctx.chat_id,
            student_id=ctx.student_id,
            trigger="every_n",
        )
        _logger.info(
            "observer_enqueued",
            chat_id=str(ctx.chat_id),
            trigger="every_n",
            job_id=job_id,
        )
    except Exception:  # noqa: BLE001
        _logger.warning("observer_trigger_failed", chat_id=str(ctx.chat_id))


async def _wrap_agent(
    stream: AsyncIterator[StreamEvent],
    first: StreamEvent,
    request: Request,
    ctx: ChatCtx,
    redis: Redis,
    locked: bool = False,
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
                        # Реплики чата не имеют правил и намеренно остаются
                        # без processed_at: это окно наблюдателя (§8.1),
                        # которое закрывает он сам. Явный флаг, а не побочный
                        # эффект `deps=None`.
                        dispatch_event=False,
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
                # До последнего кадра: SSE закрывает поток на `done`, и код
                # после этого yield уже не выполнился бы.
                if ctx.kind == "prep":
                    await _trigger_observer(request, ctx)
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
        if locked:
            await _release_chat_lock(redis, ctx.chat_id, ctx.request_id)


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
    request_id = request.state.request_id
    locked = await _take_chat_lock(redis, chat_id, request_id)
    try:
        session_id = await current_session_id(redis, student.student_id)
        ctx = ChatCtx(
            student_id=student.student_id,
            kind=kind,
            chat_id=chat_id,
            session_id=session_id,
            request_id=request_id,
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
                dispatch_event=False,  # окно наблюдателя, см. message.assistant
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
    except BaseException:
        if locked:
            await _release_chat_lock(redis, chat_id, request_id)
        raise
    return sse_response(_wrap_agent(stream, first, request, ctx, redis, locked))


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


# --- «обновить модель знаний» (§3.12, п. 5–6) ---


async def _owned_set(session: AsyncSession, student_id: UUID, set_id: UUID) -> Any:
    item = await sets_repo.get_set(session, student_id, set_id)
    if item is None:
        raise NotFound("set not found")
    return item


@router.post("/prep/observe", status_code=202, response_model=ObserveRequestedOut)
async def request_observation(
    body: ObserveRequestIn,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
    arq: Annotated[Any, Depends(get_arq)],
) -> ObserveRequestedOut:
    """Queue the observer on this chat now; poll `GET /chat/prep/observations`
    with the returned `since_event_id` for the result."""
    await _owned_set(session, student.student_id, body.set_id)
    chat_id = chat_id_for(student.student_id, "prep", body.set_id, body.topic_skill_id)
    try:
        allowed = await deps.redis.set(
            keys.lock(f"observe_rl:{chat_id}"),
            "1",
            nx=True,
            ex=_OBSERVE_RATE_LIMIT_S,
        )
    except Exception:  # noqa: BLE001 — no Redis, no rate limit
        allowed = True
    if not allowed:
        raise TooManyRequests("observer was requested less than 10 s ago")

    event = await store.append(
        session,
        deps.redis,
        EventIn(
            type=EventType.observer_requested,
            payload=ObserverRequestedPayload(reason="button").model_dump(mode="json"),
            student_id=student.student_id,
            chat_id=chat_id,
            set_id=body.set_id,
            topic_skill_id=body.topic_skill_id,
        ),
        dispatch_event=False,
    )
    # Событие должно быть видно job'у до постановки в очередь.
    await session.commit()
    job_id = None
    if arq is not None:
        try:
            job_id = await enqueue(
                arq,
                "interactive",
                "observe_chat",
                _job_id=f"observe:{chat_id}",
                chat_id=chat_id,
                student_id=student.student_id,
                trigger="requested",
            )
        except Exception:  # noqa: BLE001
            _logger.warning("observer_not_enqueued", chat_id=str(chat_id))
    _logger.info(
        "observer_enqueued", chat_id=str(chat_id), trigger="requested", job_id=job_id
    )
    return ObserveRequestedOut(
        job_id=job_id,
        since_event_id=event.id,
        knowledge_version=await version.get(deps.redis, student.student_id),
    )


@router.get("/prep/observations", response_model=ObservationsDiffOut)
async def observations_diff(
    set_id: UUID,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
    since_event_id: int = 0,
    topic_skill_id: str | None = None,
) -> ObservationsDiffOut:
    """What the observer found after `since_event_id` in this chat."""
    set_out = await _owned_set(session, student.student_id, set_id)
    chat_id = chat_id_for(student.student_id, "prep", set_id, topic_skill_id)
    extracted = await store.list_by_type(
        session,
        student.student_id,
        [EventType.observation_extracted],
        None,
        100,
        chat_id=chat_id,
        after_id=since_event_id,
    )
    failures = [
        e
        for e in await store.list_by_type(
            session,
            student.student_id,
            [EventType.job_failed],
            None,
            100,
            chat_id=chat_id,
            after_id=since_event_id,
        )
        if (e.payload or {}).get("job") == "observe_chat"
    ]
    answered = await store.list_by_type(
        session,
        student.student_id,
        [EventType.task_answered],
        None,
        200,
        chat_id=chat_id,
        after_id=since_event_id,
    )
    answered_sources = {
        source for e in answered for source in (e.source_event_ids or [])
    }

    skills = await apply_knowledge.states_view(
        session, deps, student.student_id, set_out.exam_id
    )
    skill_names = {s.skill_id: s.name for s in skills}
    views: list[ObservationView] = []
    for event in extracted:
        payload = ObservationExtractedPayload.model_validate(event.payload)
        keys_done: set[tuple[str, int]] = set()
        if deps.graph is not None:
            try:
                keys_done = await personal.list_evidence_keys_for_event(
                    deps.graph, student.student_id, event.id
                )
            except Exception:  # noqa: BLE001 — graph down: nothing shown as applied
                keys_done = set()
        message_ids = await messages.list_by_event_ids(
            session,
            student.student_id,
            sorted({i for o in payload.observations for i in o.event_ids}),
        )
        for ordinal, obs in enumerate(payload.observations):
            applied = (obs.skill_id, ordinal) in keys_done or (
                obs.kind == "task_in_chat" and event.id in answered_sources
            )
            views.append(
                ObservationView(
                    event_id=event.id,
                    ordinal=ordinal,
                    kind=obs.kind,
                    skill_id=obs.skill_id,
                    skill_name=skill_names.get(obs.skill_id or ""),
                    misconception_id=obs.misconception_id,
                    summary=obs.summary,
                    confidence=obs.confidence,
                    applied=applied,
                    message_ids=[
                        message_ids[i] for i in obs.event_ids if i in message_ids
                    ],
                )
            )

    mentioned_skills = {v.skill_id for v in views if v.skill_id}
    mentioned_misc = {v.misconception_id for v in views if v.misconception_id}
    misconceptions = [
        m
        for m in await apply_knowledge.misconceptions_view(
            deps, student.student_id, set_out.exam_id
        )
        if m.misconception_id in mentioned_misc
    ]
    if extracted:
        status, failed_reason = "done", None
    elif failures:
        status = "failed"
        failed_reason = str((failures[-1].payload or {}).get("reason") or "")
    else:
        status, failed_reason = "pending", None
    current = await version.get(deps.redis, student.student_id)
    response.headers["X-Knowledge-Version"] = str(current)
    return ObservationsDiffOut(
        status=status,
        observations=views,
        skills=[s for s in skills if s.skill_id in mentioned_skills],
        misconceptions=misconceptions,
        knowledge_version=current,
        failed_reason=failed_reason,
    )
