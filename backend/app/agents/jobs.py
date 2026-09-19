"""ARQ jobs of the agents layer.

Signatures: an ARQ worker context first, then ``request_id``, then the task's
own named parameters. ``ctx`` comes from ``app.workers.main.startup``:
``sessionmaker``, ``neo4j``, ``redis`` (``ArqRedis``), ``llm``, ``embedder``
(interactive worker only), plus ARQ's own ``job_id`` and ``job_try``.

Phase 3 (docs/tz/phase3-agents.md §3.9, §3.11): ``observe_chat`` and
``canonize_misconception``. The rest are phase-4/6 stubs.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

import httpx
import openai
import structlog
from arq import Retry
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.exc import DBAPIError, OperationalError

from app import keys
from app.agents import observer
from app.config import settings
from app.db.repo import messages as messages_repo
from app.db.repo import sets as sets_repo
from app.db.repo import summaries as summaries_repo
from app.db.repo import tasks as tasks_repo
from app.errors import LLMUnavailable
from app.events import dispatch, handlers, store  # noqa: F401 (rule table)
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical as canonical_q
from app.graph.queries import personal as personal_q
from app.knowledge import words
from app.llm.prompts import load_prompt
from app.schemas.chat import AssistantMarkup
from app.schemas.events import (
    Event,
    EventIn,
    EventType,
    JobFailedPayload,
    MisconceptionCanonizedPayload,
    MisconceptionPersonalCreatedPayload,
    ObservationExtractedPayload,
)
from app.schemas.llm import LLMMessage
from app.schemas.observer import (
    CanonDecision,
    MisconceptionForObserver,
    ObservationApplyResult,
    ObserverContext,
    ObserverWindow,
    SkillForObserver,
    WindowMessage,
    WindowTask,
)
from app.schemas.tasks import OptionOut
from app.workers import queue

_logger = structlog.get_logger(__name__)

Trigger = Literal["every_n", "topic_completed", "set_completed", "requested"]
_MESSAGE_TYPES = [EventType.message_user, EventType.message_assistant]
_WINDOW_TYPES = [*_MESSAGE_TYPES, EventType.task_issued]
_TASK_LOOKBACK = 20
_MAX_TRIES = 3
_CANON_SEARCH_K = 5


class _GraphDown(Exception):
    """The graph driver is missing — the slice of the knowledge model can't
    be read, so an observation would be meaningless."""


class _Failed(Exception):
    """A final failure with a machine-readable reason, no retry."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _classify(exc: BaseException) -> tuple[bool, str]:
    """(transient, reason) of one job error (§3.9 «Ошибки и ретраи»)."""
    if isinstance(exc, _Failed):
        return False, exc.reason
    if isinstance(exc, LLMUnavailable):
        message = str(exc)
        if "structured output failed" in message:
            return False, "invalid_structured_output"
        if "rate limit" in message:
            return True, "rate_limit"
        # breaker `down` or LLM_FORCE_DOWN — recovery is phase 5, not a retry
        return False, "llm_down"
    if isinstance(exc, openai.APIStatusError):
        return exc.status_code >= 500, f"llm_http_{exc.status_code}"
    if isinstance(
        exc,
        openai.APITimeoutError
        | openai.APIConnectionError
        | openai.RateLimitError
        | httpx.HTTPError,
    ):
        return True, "llm_unavailable"
    if isinstance(exc, _GraphDown | ServiceUnavailable | SessionExpired):
        return True, "graph_unavailable"
    if isinstance(exc, OperationalError | DBAPIError) and getattr(
        exc, "connection_invalidated", True
    ):
        return True, "db_unavailable"
    return False, type(exc).__name__


async def _job_failed(
    ctx: dict,
    job: str,
    reason: str,
    student_id: UUID,
    args: dict[str, Any],
    chat_id: UUID | None = None,
) -> None:
    """`job.failed` in its own session — the job's own transaction may have
    been rolled back."""
    try:
        async with ctx["sessionmaker"]() as session:
            await store.append(
                session,
                ctx["redis"],
                EventIn(
                    type=EventType.job_failed,
                    payload=JobFailedPayload(
                        job=job,
                        job_id=ctx.get("job_id"),
                        reason=reason,
                        args=args,
                    ).model_dump(mode="json"),
                    student_id=student_id,
                    chat_id=chat_id,
                ),
                dispatch_event=False,
            )
            await session.commit()
    except Exception:  # noqa: BLE001 — nothing else left to report to
        _logger.exception("job_failed_not_recorded", job=job, reason=reason)
    _logger.warning(
        "job_failed", job=job, job_id=ctx.get("job_id"), reason=reason, **args
    )


async def _guarded(
    ctx: dict,
    job: str,
    timeout_s: float,
    student_id: UUID,
    args: dict[str, Any],
    body: Callable[[], Awaitable[Any]],
    chat_id: UUID | None = None,
) -> Any:
    """Run a job body with the §3.9 error policy.

    The internal timeout is a few seconds shorter than ARQ's, so the job can
    still write `job.failed` before ARQ cancels it. Transient errors raise
    `arq.Retry` while tries remain; the last try, and every non-transient
    error, ends in `job.failed`.
    """
    try:
        async with asyncio.timeout(max(1.0, timeout_s - 5)):
            return await body()
    except Retry:
        raise
    except TimeoutError:
        await _job_failed(ctx, job, "timeout", student_id, args, chat_id)
        return None
    except Exception as exc:  # noqa: BLE001 — classified below
        transient, reason = _classify(exc)
        job_try = int(ctx.get("job_try", 1) or 1)
        if transient and job_try < _MAX_TRIES:
            _logger.info("job_retry", job=job, reason=reason, job_try=job_try)
            raise Retry(defer=10 * job_try) from exc
        await _job_failed(ctx, job, reason, student_id, args, chat_id)
        return None


def _rule_deps(ctx: dict) -> RuleDeps:
    return RuleDeps(
        graph=ctx.get("neo4j"),
        redis=ctx["redis"],
        params=settings.knowledge,
        now=lambda: datetime.now(UTC),
    )


def _uuid(value: Any) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


# --- observe_chat (§3.9) ---


async def observe_chat(
    ctx: dict,
    request_id: str,
    chat_id: UUID,
    student_id: UUID,
    trigger: Trigger = "every_n",
) -> None:
    """Extract observations from a chat window and hand them to the rule
    (memory-architecture §8.1).

    Queue: `interactive`. Trigger: every N chat messages, a topic/set being
    completed, or the «обновить модель знаний» button.
    """
    structlog.contextvars.bind_contextvars(request_id=request_id)
    chat_id, student_id = _uuid(chat_id), _uuid(student_id)
    redis = ctx["redis"]
    lock = keys.lock(f"observe:{chat_id}")
    token = uuid4().hex
    if not await redis.set(lock, token, nx=True, ex=settings.OBSERVER_JOB_TIMEOUT_S):
        _logger.info("observer_job", chat_id=str(chat_id), skipped="locked")
        return
    args = {"chat_id": str(chat_id), "trigger": trigger}
    try:
        requeue = await _guarded(
            ctx,
            "observe_chat",
            settings.OBSERVER_JOB_TIMEOUT_S,
            student_id,
            args,
            lambda: _observe(ctx, chat_id, student_id, trigger),
            chat_id=chat_id,
        )
    finally:
        current = await redis.get(lock)
        if (
            current is not None
            and (current.decode() if isinstance(current, bytes) else current) == token
        ):
            await redis.delete(lock)
    if requeue:
        next_trigger, marker = requeue
        # Своего `job_id` занятая job переиспользовать не может (ARQ хранит
        # ключ, пока она идёт), поэтому дозапуск — с суффиксом окна.
        job_id = await queue.enqueue(
            redis,
            "interactive",
            "observe_chat",
            _job_id=f"observe:{chat_id}:{marker}",
            chat_id=chat_id,
            student_id=student_id,
            trigger=next_trigger,
        )
        _logger.info(
            "observer_enqueued",
            chat_id=str(chat_id),
            trigger=next_trigger,
            job_id=job_id,
        )


async def _observe(
    ctx: dict, chat_id: UUID, student_id: UUID, trigger: Trigger
) -> tuple[Trigger, int] | None:
    started = time.perf_counter()
    params = settings.knowledge
    redis = ctx["redis"]
    async with ctx["sessionmaker"]() as session:
        pending = await store.list_unprocessed(
            session, chat_id, limit=params.observer_window_max + 10, types=_WINDOW_TYPES
        )
        markers = await store.list_unprocessed(
            session, chat_id, limit=50, types=[EventType.observer_requested]
        )
        requested = trigger == "requested" or bool(markers)
        messages = [e for e in pending if e.type in _MESSAGE_TYPES][
            : params.observer_window_max
        ]
        anchor = messages[0] if messages else (markers[0] if markers else None)
        set_id = next((e.set_id for e in [*messages, *markers] if e.set_id), None)
        topic_skill_id = next(
            (e.topic_skill_id for e in [*messages, *markers] if e.topic_skill_id),
            None,
        )
        if anchor is None or (not messages and not requested):
            _logger.info("observer_job", chat_id=str(chat_id), window=0)
            return None
        if set_id is None:
            _logger.info("observer_job", chat_id=str(chat_id), skipped="not_prep")
            return None
        set_out = await sets_repo.get_set(session, student_id, set_id)
        if set_out is None:
            _logger.info("observer_job", chat_id=str(chat_id), skipped="no_set")
            return None
        exam_id = set_out.exam_id

        window_ids: list[int] = []
        tasks: list[WindowTask] = []
        result_observations: list[Any] = []
        extractor_version = load_prompt("observer").extractor_version
        model = (
            settings.MODEL_BULK
            if settings.OBSERVER_SLOT == "bulk"
            else (settings.MODEL_CHAT)
        )
        raw_count = 0
        if messages:
            first_id, last_id = messages[0].id, messages[-1].id
            issued = _window_tasks(pending, first_id, last_id)
            window_ids = sorted({*(m.id for m in messages), *(e.id for e in issued)})
            tasks = await _tasks(session, student_id, chat_id, issued)
            window = ObserverWindow(
                chat_id=chat_id,
                student_id=student_id,
                exam_id=exam_id,
                set_id=set_id,
                topic_skill_id=topic_skill_id,
                messages=await _window_messages(session, student_id, messages),
                tasks=tasks,
            )
            if ctx.get("neo4j") is None:
                raise _GraphDown()
            context = await _observer_context(
                ctx, session, student_id, exam_id, set_out, topic_skill_id, set_id
            )
            result = await observer.run(
                ctx["llm"], window, context, slot=settings.OBSERVER_SLOT
            )
            result_observations = result.out.observations
            extractor_version = result.extractor_version
            model = result.model
            raw_count = result.raw_count

        last_session = next(
            (e.session_id for e in reversed(messages) if e.session_id), None
        )
        payload = ObservationExtractedPayload(
            observations=result_observations,
            window_from_event_id=messages[0].id if messages else None,
            window_to_event_id=messages[-1].id if messages else None,
            topic_skill_id=topic_skill_id,
            set_id=set_id,
            exam_id=exam_id,
            model=model,
            raw_count=raw_count,
        )
        event = await store.append(
            session,
            redis,
            EventIn(
                type=EventType.observation_extracted,
                payload=payload.model_dump(mode="json"),
                student_id=student_id,
                session_id=last_session or anchor.session_id,
                exam_id=exam_id,
                set_id=set_id,
                topic_skill_id=topic_skill_id,
                chat_id=chat_id,
                extractor_version=extractor_version,
                source_event_ids=window_ids,
            ),
            dispatch_event=False,
        )
        results = await dispatch.dispatch(session, event, _rule_deps(ctx))
        # Окно закрывается в любом случае: работа модели сохранена событием,
        # применение — забота правила (при упавшем графе — фаза 5).
        await store.mark_processed(session, [*window_ids, *(m.id for m in markers)])
        await session.commit()

        applied = results.get("apply_observation_extracted")
        apply_result = applied if isinstance(applied, ObservationApplyResult) else None
        for ordinal in apply_result.pending_canonizations if apply_result else []:
            await queue.enqueue(
                redis,
                "interactive",
                "canonize_misconception",
                _job_id=f"canon:{event.id}:{ordinal}",
                student_id=student_id,
                observation_event_id=event.id,
                ordinal=ordinal,
            )

        remaining = await store.count_unprocessed(session, chat_id, _MESSAGE_TYPES)
        new_markers = await store.list_unprocessed(
            session, chat_id, limit=1, types=[EventType.observer_requested]
        )

    _logger.info(
        "observer_job",
        chat_id=str(chat_id),
        trigger=trigger,
        window=len(messages),
        observations=raw_count,
        applied=apply_result.applied if apply_result else 0,
        skipped=len(apply_result.skipped) if apply_result else 0,
        ms=round((time.perf_counter() - started) * 1000, 1),
    )
    if new_markers:
        return "requested", new_markers[0].id
    if remaining >= params.observer_every_n:
        return "every_n", event.id
    return None


def _window_tasks(pending: list[Event], first_id: int, last_id: int) -> list[Event]:
    """`task.issued` inside the window, or shortly before it (the task was
    handed out, the answer is in the window)."""
    issued = [e for e in pending if e.type == EventType.task_issued]
    inside = [e for e in issued if first_id <= e.id <= last_id]
    before = [e for e in issued if e.id < first_id][-_TASK_LOOKBACK:]
    return sorted([*before, *inside], key=lambda e: e.id)


async def _window_messages(
    session: Any, student_id: UUID, events: list[Event]
) -> list[WindowMessage]:
    ids = await messages_repo.list_by_event_ids(
        session, student_id, [e.id for e in events]
    )
    out: list[WindowMessage] = []
    for event in events:
        payload = event.payload or {}
        role = "user" if event.type == EventType.message_user else "assistant"
        markup = None
        if role == "assistant":
            markup = AssistantMarkup(
                mode=payload.get("mode"),
                gave_task_instance_id=payload.get("gave_task_instance_id"),
                hint_level=payload.get("hint_level"),
                referenced_skill_ids=payload.get("referenced_skill_ids") or [],
            )
        out.append(
            WindowMessage(
                event_id=event.id,
                message_id=ids.get(event.id),
                role=role,
                text=str(payload.get("text", "")),
                markup=markup,
                occurred_at=event.occurred_at,
                session_id=event.session_id,
            )
        )
    return out


async def _tasks(
    session: Any, student_id: UUID, chat_id: UUID, issued: list[Event]
) -> list[WindowTask]:
    """Tasks of the window: issued in it, plus this chat's still open ones
    (issued in an earlier window, answered in this one)."""
    ids: list[UUID] = []
    for event in issued:
        instance_id = (event.payload or {}).get("instance_id")
        if instance_id:
            ids.append(_uuid(instance_id))
    open_instances = await tasks_repo.list_open_chat_instances(
        session, student_id, chat_id
    )
    ids.extend(i.id for i in open_instances if i.id not in ids)
    instances = await tasks_repo.list_instances(session, student_id, ids)
    issued_ids = await tasks_repo.issued_event_ids(
        session, student_id, [i.id for i in instances]
    )
    return [
        WindowTask(
            instance_id=instance.id,
            issued_event_id=issued_ids.get(instance.id, 0),
            skill_id=instance.skill_id,
            stem=instance.stem_rendered,
            options=[OptionOut(key=o.key, text=o.text) for o in instance.options],
            type=instance.type,
        )
        for instance in instances
    ]


async def _observer_context(
    ctx: dict,
    session: Any,
    student_id: UUID,
    exam_id: Any,
    set_out: Any,
    topic_skill_id: str | None,
    set_id: UUID,
) -> ObserverContext:
    driver = ctx["neo4j"]
    params = settings.knowledge
    roots = (
        [topic_skill_id]
        if topic_skill_id
        else [topic.skill_id for topic in set_out.topics]
    )
    skill_ids: list[str] = list(roots)
    for root in roots:
        for prerequisite in await canonical_q.get_prerequisites(driver, root, depth=2):
            if prerequisite.skill_id not in skill_ids:
                skill_ids.append(prerequisite.skill_id)

    exam_skills = {
        sw.skill.id: sw.skill
        for sw in await canonical_q.list_exam_skills(driver, exam_id)
    }
    states = {
        s.skill_id: s for s in await personal_q.get_states(driver, student_id, exam_id)
    }
    skills: list[SkillForObserver] = []
    for skill_id in skill_ids:
        ref = exam_skills.get(skill_id) or await canonical_q.get_skill(driver, skill_id)
        if ref is None:
            continue
        skills.append(
            SkillForObserver(
                id=skill_id,
                name=ref.name,
                description=ref.description,
                level=words.skill_level(
                    states.get(skill_id), params.p_target_max, params
                ),
            )
        )

    misc_states = {
        m.misconception_id: m
        for m in await personal_q.get_misc_states(driver, student_id, skill_ids)
    }
    misconceptions: list[MisconceptionForObserver] = []
    seen: set[str] = set()
    for skill_id in skill_ids:
        for ref in await canonical_q.list_misconceptions_for_skill(driver, skill_id):
            if ref.id in seen:
                continue
            seen.add(ref.id)
            state = misc_states.get(ref.id)
            misconceptions.append(
                MisconceptionForObserver(
                    id=ref.id,
                    name=ref.name,
                    description=ref.description,
                    status=state.status if state else None,
                    scope="library",
                )
            )
    for misconception_id, state in misc_states.items():
        if misconception_id in seen:
            continue
        ref = await canonical_q.get_misconception(driver, misconception_id)
        misconceptions.append(
            MisconceptionForObserver(
                id=misconception_id,
                name=state.name,
                description=ref.description if ref else state.name,
                status=state.status,
                scope="personal" if misconception_id.startswith("pers.") else "library",
            )
        )
    previous = await summaries_repo.get_latest_text(
        session, student_id, before_set_id=set_id
    )
    return ObserverContext(
        skills=skills, misconceptions=misconceptions, previous_summary=previous
    )


# --- canonize_misconception (§3.11) ---

_TRANSLIT = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
        "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
)  # fmt: skip


def slug(text: str) -> str:
    """Latin, lowercase, dash-separated — the tail of a personal id."""
    value = (text or "").lower().translate(_TRANSLIT)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "misc"


async def canonize_misconception(
    ctx: dict,
    request_id: str,
    student_id: UUID,
    observation_event_id: int,
    ordinal: int,
) -> None:
    """Merge a proposed misconception into a known one, or create a personal
    one (memory-architecture §5.4). The decision is an event; the node and
    the evidence are written by the rule."""
    structlog.contextvars.bind_contextvars(request_id=request_id)
    student_id = _uuid(student_id)
    args = {"observation_event_id": observation_event_id, "ordinal": ordinal}
    await _guarded(
        ctx,
        "canonize_misconception",
        settings.CANON_JOB_TIMEOUT_S,
        student_id,
        args,
        lambda: _canonize(ctx, student_id, observation_event_id, ordinal),
    )


async def _canonize(
    ctx: dict, student_id: UUID, observation_event_id: int, ordinal: int
) -> None:
    params = settings.knowledge
    async with ctx["sessionmaker"]() as session:
        event = await store.get_event(session, student_id, observation_event_id)
        if event is None or event.type != EventType.observation_extracted:
            _logger.info("canonize", event_id=observation_event_id, skipped="no_event")
            return
        payload = ObservationExtractedPayload.model_validate(event.payload)
        if not 0 <= ordinal < len(payload.observations):
            _logger.info("canonize", event_id=event.id, skipped="no_observation")
            return
        obs = payload.observations[ordinal]
        if obs.kind != "proposed_misconception":
            _logger.info("canonize", event_id=event.id, skipped="not_proposed")
            return

        prior = await store.list_by_type(
            session,
            student_id,
            [
                EventType.misconception_canonized,
                EventType.misconception_personal_created,
            ],
            None,
            500,
            after_id=observation_event_id,
        )
        if any(
            p.payload.get("source_event_id") == observation_event_id
            and p.payload.get("ordinal") == ordinal
            for p in prior
        ):
            _logger.info("canonize", event_id=event.id, skipped="already_done")
            return

        embedder = ctx.get("embedder")
        if embedder is None:
            raise _Failed("embedder_unavailable")
        name = obs.name or ""
        description = obs.description or ""
        try:
            vectors = await asyncio.to_thread(
                embedder.embed, [f"{name}. {description}"]
            )
        except ValueError as exc:
            raise _Failed("embedding_dim") from exc
        vector = vectors[0]

        graph = ctx.get("neo4j")
        if graph is None:
            raise _GraphDown()
        skill_id = obs.skill_id or payload.topic_skill_id
        if skill_id is None:
            raise _Failed("no_skill")
        candidates = await canonical_q.search_misconceptions(
            graph, vector, skill_id, student_id, k=_CANON_SEARCH_K
        )
        best, similarity = candidates[0] if candidates else (None, None)

        canonical_id: str | None = None
        decided_by: Literal["threshold", "model"] = "threshold"
        if best is not None and similarity is not None:
            if similarity > params.canon_merge:
                canonical_id = best.id
            elif similarity >= params.canon_adjudicate:
                decision = await _adjudicate(ctx, name, description, best)
                if decision.same:
                    canonical_id, decided_by = best.id, "model"

        error_class = obs.error_class or "conceptual"
        if canonical_id is not None:
            new = EventIn(
                type=EventType.misconception_canonized,
                payload=MisconceptionCanonizedPayload(
                    source_event_id=observation_event_id,
                    ordinal=ordinal,
                    skill_id=skill_id,
                    canonical_id=canonical_id,
                    similarity=float(similarity or 0.0),
                    decided_by=decided_by,
                    name=name,
                    description=description,
                    error_class=error_class,
                ).model_dump(mode="json"),
                student_id=student_id,
                exam_id=payload.exam_id,
                set_id=payload.set_id,
                topic_skill_id=payload.topic_skill_id,
                chat_id=event.chat_id,
                source_event_ids=[observation_event_id],
            )
            decision_name = "merge"
        else:
            misconception_id = await _personal_id(graph, student_id, name)
            new = EventIn(
                type=EventType.misconception_personal_created,
                payload=MisconceptionPersonalCreatedPayload(
                    misconception_id=misconception_id,
                    source_event_id=observation_event_id,
                    ordinal=ordinal,
                    skill_id=skill_id,
                    name=name,
                    description=description,
                    error_class=error_class,
                    embedding=vector,
                    best_similarity=similarity,
                ).model_dump(mode="json"),
                student_id=student_id,
                exam_id=payload.exam_id,
                set_id=payload.set_id,
                topic_skill_id=payload.topic_skill_id,
                chat_id=event.chat_id,
                source_event_ids=[observation_event_id],
            )
            decision_name = "create"
        saved = await store.append(session, ctx["redis"], new, dispatch_event=False)
        await dispatch.dispatch(session, saved, _rule_deps(ctx))
        await session.commit()
    _logger.info(
        "canonize",
        event_id=observation_event_id,
        ordinal=ordinal,
        decision=decision_name,
        similarity=similarity,
        decided_by=decided_by if canonical_id else None,
    )


async def _adjudicate(
    ctx: dict, name: str, description: str, best: Any
) -> CanonDecision:
    prompt = load_prompt("canon")
    messages = [
        LLMMessage(
            role="system",
            content=prompt.render(
                a=f"{name}: {description}", b=f"{best.name}: {best.description}"
            ),
        ),
        LLMMessage(role="user", content="Одно ли это заблуждение?"),
    ]
    try:
        return await ctx["llm"].structured(
            messages, CanonDecision, settings.OBSERVER_SLOT
        )
    except LLMUnavailable as exc:
        # Ложная склейка хуже потери одного наблюдения (§11.2): не создаём
        # узел наугад, а фиксируем отказ.
        if "structured output failed" in str(exc):
            raise _Failed("adjudication_failed") from exc
        raise


async def _personal_id(graph: Any, student_id: UUID, name: str) -> str:
    base = f"pers.{student_id.hex[:8]}.{slug(name)[:24]}"
    candidate = base
    suffix = 2
    while await canonical_q.get_misconception(graph, candidate) is not None:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


# --- later phases ---


async def pregenerate_set(
    ctx: dict, request_id: str, set_id: UUID, student_id: UUID
) -> None:
    """Pre-generate guidelines and explanations for every topic in a set so
    they're ready before the student opens them.

    Queue: `bulk` (tech-stack §2.5). Trigger: `set.opened`. Phase 4.
    """
    raise NotImplementedError("phase 4")


async def set_summary(
    ctx: dict, request_id: str, set_id: UUID, student_id: UUID
) -> None:
    """Build the short end-of-set report — what's closed, which skills
    firmed up, which misconceptions resolved (product-logic §4.1).

    Queue: `interactive` (tech-stack §2.5). Trigger: `set.completed`. Phase 4.
    """
    raise NotImplementedError("phase 4")


async def propose_personal_nodes(
    ctx: dict, request_id: str, set_id: UUID, student_id: UUID
) -> None:
    """Decide whether any canonical skill entering a new set needs a
    personal node under it (product-logic §5.2).

    Queue: `interactive` (tech-stack §2.5). Trigger: `set.opened`. Phase 6.
    """
    raise NotImplementedError("phase 6")


async def soft_match(
    ctx: dict, request_id: str, student_id: UUID, program_ids: list[str]
) -> None:
    """Score soft fit between the student's trait summary and each given
    program's environment text (product-logic §3.3).

    Queue: `bulk` (tech-stack §2.5). Phase 4.
    """
    raise NotImplementedError("phase 4")


async def extract_program(ctx: dict, request_id: str, url: str) -> None:
    """Fetch the program page at `url` and extract `Program` fields via
    `MODEL_BULK` structured output (tech-stack §4.6, product-logic §5.1).

    Queue: `bulk` (tech-stack §2.5). Phase 4.
    """
    raise NotImplementedError("phase 4")
