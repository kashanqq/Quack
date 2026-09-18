"""Transactional Phase 2 event handler registry and dispatcher."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog
from neo4j import AsyncDriver
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import KnowledgeParams
from app.schemas.events import Event, EventType


@dataclass
class RuleDeps:
    graph: AsyncDriver | None
    redis: Redis
    params: KnowledgeParams
    now: Callable[[], datetime]


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
    for handler in _handlers.get(event.type, ()):
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
        if result is GraphUnavailable:
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
