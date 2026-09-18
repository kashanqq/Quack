"""Synchronous-in-transaction event handler registry."""

from collections.abc import Awaitable, Callable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.events import Event, EventType

Handler = Callable[[AsyncSession, Event], Awaitable[None]]
_handlers: dict[EventType, list[Handler]] = {}
_logger = structlog.get_logger(__name__)


def on(event_type: EventType) -> Callable[[Handler], Handler]:
    def register(handler: Handler) -> Handler:
        _handlers.setdefault(event_type, []).append(handler)
        return handler

    return register


async def dispatch(session: AsyncSession, event: Event) -> None:
    handlers = _handlers.get(event.type, ())
    for handler in handlers:
        await handler(session, event)
    _logger.info(
        "event_dispatched",
        event_id=event.id,
        type=event.type.value,
        handlers=len(handlers),
    )
