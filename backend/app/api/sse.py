"""Server-sent events framing for the public chat stream."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress

from fastapi.responses import StreamingResponse

from app.schemas.chat import StreamError, StreamEvent


async def _frames(events: AsyncIterator[StreamEvent]) -> AsyncIterator[str]:
    iterator = aiter(events)
    pending: asyncio.Task[StreamEvent] | None = None
    try:
        while True:
            if pending is None:
                pending = asyncio.create_task(anext(iterator))
            ready, _ = await asyncio.wait({pending}, timeout=15)
            if not ready:
                yield ": keepalive\n\n"
                continue
            try:
                event = pending.result()
            except StopAsyncIteration:
                return
            except Exception:
                event = StreamError(code="internal", message="Internal server error")
                yield f"data: {event.model_dump_json()}\n\n"
                return
            pending = None
            yield f"data: {event.model_dump_json()}\n\n"
            if event.type in {"done", "error"}:
                return
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            with suppress(asyncio.CancelledError):
                await pending
        close = getattr(iterator, "aclose", None)
        if close is not None:
            await close()


def sse_response(events: AsyncIterator[StreamEvent]) -> StreamingResponse:
    return StreamingResponse(
        _frames(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
