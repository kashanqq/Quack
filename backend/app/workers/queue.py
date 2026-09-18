"""Enqueue one ARQ job — importable from the API without pulling the worker in."""

from typing import Any, Literal
from uuid import uuid4

import structlog
from arq.connections import ArqRedis

_QUEUES = ("interactive", "bulk")


async def enqueue(
    redis: ArqRedis,
    queue: Literal["interactive", "bulk"],
    fn_name: str,
    **kwargs: Any,
) -> str | None:
    """Put `fn_name` on one of the two queues, tagged with the request id."""
    if queue not in _QUEUES:
        raise ValueError("queue must be interactive or bulk")
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    kwargs["request_id"] = request_id or uuid4().hex[:16]
    job = await redis.enqueue_job(fn_name, _queue_name=queue, **kwargs)
    return job.job_id if job is not None else None
