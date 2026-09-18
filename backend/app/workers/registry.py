"""ARQ job registry for Phase 1."""

from typing import Any


async def ping(ctx: dict[str, Any], request_id: str) -> str:
    return "pong"


INTERACTIVE = [ping]
BULK = [ping]
