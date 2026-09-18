"""ARQ queues and shared infrastructure lifecycle."""

import inspect
from typing import Any, Literal
from uuid import uuid4

import redis.asyncio as redis_async
import structlog
from arq.connections import ArqRedis, RedisSettings

from app.config import settings
from app.db.engine import close_engine, create_engine, create_sessionmaker
from app.main import _optional_layer
from app.workers import registry


async def startup(ctx: dict[str, Any]) -> None:
    engine = create_engine(settings)
    ctx["engine"] = engine
    try:
        ctx["sessionmaker"] = create_sessionmaker(engine)
        graph_client = _optional_layer("app.graph.client")  # B1 integration point.
        ctx["graph_client"] = graph_client
        driver = None
        if graph_client is not None:
            driver = graph_client.create_driver(settings)
            if inspect.isawaitable(driver):
                driver = await driver
        ctx["neo4j"] = driver
        redis = ctx.get("redis")  # ARQ supplies its own Redis pool in workers.
        ctx["owns_redis"] = redis is None
        if redis is None:
            redis = redis_async.from_url(settings.REDIS_URL)
            ctx["redis"] = redis
        llm_module = _optional_layer("app.llm.client")  # B2 integration point.
        ctx["llm"] = (
            llm_module.LLMClient(settings, redis) if llm_module is not None else None
        )
    except BaseException:
        await shutdown(ctx)
        raise


async def shutdown(ctx: dict[str, Any]) -> None:
    llm = ctx.pop("llm", None)
    if llm is not None:
        close = getattr(llm, "aclose", None) or getattr(llm, "close", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result
    redis = ctx.pop("redis", None)
    if redis is not None and ctx.pop("owns_redis", False):
        await redis.aclose()
    driver = ctx.pop("neo4j", None)
    graph_client = ctx.pop("graph_client", None)
    if driver is not None and graph_client is not None:
        result = graph_client.close_driver(driver)
        if inspect.isawaitable(result):
            await result
    engine = ctx.pop("engine", None)
    if engine is not None:
        await close_engine(engine)
    ctx.pop("sessionmaker", None)


async def enqueue(
    redis: ArqRedis,
    queue: Literal["interactive", "bulk"],
    fn_name: str,
    **kwargs: Any,
) -> str | None:
    if queue not in {"interactive", "bulk"}:
        raise ValueError("queue must be interactive or bulk")
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    kwargs["request_id"] = request_id or uuid4().hex[:16]
    job = await redis.enqueue_job(fn_name, _queue_name=queue, **kwargs)
    return job.job_id if job is not None else None


class WorkerInteractive:
    functions = registry.INTERACTIVE
    queue_name = "interactive"
    max_tries = 3
    job_timeout = 30
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)


class WorkerBulk:
    functions = registry.BULK
    queue_name = "bulk"
    max_tries = 3
    job_timeout = 90
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
