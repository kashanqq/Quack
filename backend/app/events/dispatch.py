"""Transactional Phase 2 event handler registry and dispatcher."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog
from neo4j import AsyncDriver
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import KnowledgeParams
from app.events.outbox import JobOutbox
from app.schemas.events import Event, EventType


@dataclass
class RuleDeps:
    graph: AsyncDriver | None
    redis: Redis
    params: KnowledgeParams
    now: Callable[[], datetime]
    # Фаза 4 (§1.4): обработчик только записывает намерение поставить задачу;
    # транспорт флашит его после коммита. Значение по умолчанию оставляет
    # конструкторы фаз 1–3 рабочими — их обработчики задач не ставят.
    jobs: JobOutbox = field(default_factory=JobOutbox)


GraphUnavailable = object()
Handler = Callable[[AsyncSession, Event, RuleDeps], Awaitable[Any]]
_handlers: dict[EventType, list[Handler]] = {}
_logger = structlog.get_logger(__name__)


def on(event_type: EventType) -> Callable[[Handler], Handler]:
    def register(handler: Handler) -> Handler:
        _handlers.setdefault(event_type, []).append(handler)
        return handler

    return register


async def dispatch(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> dict[str, Any]:
    """Run registered rules in order and mark only fully processed events."""
    from app.events.store import mark_processed

    results: dict[str, Any] = {}
    graph_unavailable = deps.graph is None
    deferred = not graph_unavailable and await _overtakes_backlog(session, event)
    if deferred:
        # Фаза 5 (§11 A2): у ученика есть более раннее неприменённое событие
        # того же рода. Спроецировать это — значит посчитать состояние из
        # неверной базы, а затем «догнать» старое поверх нового. Событие
        # остаётся неприменённым, порядок восстановит `recover_graph_events`.
        _logger.warning(
            "event_deferred_behind_backlog",
            event_id=event.id,
            type=event.type.value,
        )
        graph_unavailable = True
    for handler in () if deferred else _handlers.get(event.type, ()):
        try:
            result = await handler(session, event, deps)
        except (ServiceUnavailable, SessionExpired):
            graph_unavailable = True
            _logger.warning(
                "graph_unavailable",
                event_id=event.id,
                type=event.type.value,
                handler=handler.__name__,
            )
            break
        except Exception:
            _logger.exception(
                "event_handler_failed",
                event_id=event.id,
                type=event.type.value,
                handler=handler.__name__,
            )
            raise
        results[handler.__name__] = result
        if result is GraphUnavailable or _projection_pending(result):
            graph_unavailable = True

    if graph_unavailable:
        _logger.warning("graph_unavailable", event_id=event.id, type=event.type.value)
    else:
        await mark_processed(session, [event.id])
        event.processed_at = deps.now()
    _logger.info(
        "event_dispatched",
        event_id=event.id,
        type=event.type.value,
        handlers=len(results),
    )
    return results


def _projection_pending(result: Any) -> bool:
    """The phase-5 way a handler says "kept, but not projected" (D03).

    `GraphUnavailable` says nothing back to the caller; a handler that must
    still return a result — a graded answer — sets `projection_status` on it
    instead. Either way the event keeps `processed_at IS NULL` and stays in
    the recovery backlog.
    """
    return getattr(result, "projection_status", None) == "pending"


async def _overtakes_backlog(session: AsyncSession, event: Event) -> bool:
    """Would applying this event jump ahead of an older unapplied one?

    Only asked for the graph-mutating types (`events.recovery.RECOVERABLE`):
    a `set.opened` that only queues a pre-generation is free to run while an
    answer is still waiting for Neo4j.
    """
    from app.events import recovery

    if event.id is None or not recovery.is_recoverable(event.type):
        return False
    try:
        return await recovery.has_backlog_before(session, event.student_id, event.id)
    except Exception:  # noqa: BLE001 — the ordering check must not fail a write
        _logger.warning("backlog_check_failed", event_id=event.id, exc_info=True)
        return False
