"""ARQ queues and shared infrastructure lifecycle."""

import asyncio
import inspect
from typing import Any

import redis.asyncio as redis_async
import structlog
from arq import cron
from arq.connections import RedisSettings

from app.config import settings
from app.db.engine import close_engine, create_engine, create_sessionmaker
from app.events import handlers  # noqa: F401 (jobs dispatch through the rule table)
from app.events.outbox import JobOutbox
from app.loader import optional_layer as _optional_layer
from app.workers import registry
from app.workers.queue import enqueue

__all__ = [
    "WorkerBulk",
    "WorkerInteractive",
    "enqueue",
    "shutdown",
    "startup",
    "startup_interactive",
]

_logger = structlog.get_logger(__name__)


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
        # Фаза 4 (§1.4): в воркере тот же outbox, что и в запросе; задача
        # флашит его сама сразу после своего коммита.
        ctx["jobs"] = JobOutbox()
    except BaseException:
        await shutdown(ctx)
        raise


async def startup_bulk(ctx: dict[str, Any]) -> None:
    """Bulk worker start: infrastructure plus the missed-cron catch-up.

    A cron that never fired because the worker was down is compensated once
    at startup (§9.7) — the aggregate window is two weeks wide, so one run
    covers any realistic outage.
    """
    await startup(ctx)
    infra = _optional_layer("app.workers.jobs_infra")
    if infra is None:
        return
    try:
        await infra.catch_up(ctx)
    except Exception:  # noqa: BLE001 — a missed cron must not block the worker
        _logger.warning("cron_catch_up_failed", exc_info=True)


async def load_embedder(ctx: dict[str, Any]) -> None:
    """The sentence embedder for canonization (phase3 3.12, tech-stack 8.3).

    Loaded and warmed up once per interactive worker, off the event loop. A
    failure leaves `ctx["embedder"] = None`: the worker still starts, and
    `canonize_misconception` records `job.failed{embedder_unavailable}`.
    """
    try:
        from app.embeddings import Embedder

        embedder = Embedder(settings.EMBEDDING_MODEL, settings.EMBEDDING_DIM)
        await asyncio.to_thread(embedder.embed, ["warmup"])
        ctx["embedder"] = embedder
    except Exception:  # noqa: BLE001
        _logger.warning("embedder_unavailable", exc_info=True)
        ctx["embedder"] = None


async def startup_interactive(ctx: dict[str, Any]) -> None:
    await startup(ctx)
    await load_embedder(ctx)


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
    ctx.pop("embedder", None)


class WorkerInteractive:
    functions = registry.INTERACTIVE
    queue_name = "interactive"
    max_tries = 3
    job_timeout = 30
    keep_result = settings.JOB_KEEP_RESULT_S
    on_startup = startup_interactive
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)


def _cron_jobs() -> list[Any]:
    """Three schedules (§1.2); absent B3 infra means no crons at all."""
    infra = _optional_layer("app.workers.jobs_infra")
    if infra is None:
        return []
    interval = max(1, settings.knowledge.recs_interval_h)
    return [
        cron(infra.daily_aggregates_cron, hour=3, minute=0),  # UTC
        cron(
            infra.recommendations_batch_cron,
            hour=set(range(0, 24, interval)),
            minute=15,
        ),
        cron(infra.outbox_replay_cron, minute=set(range(0, 60, 10))),
    ]


class WorkerBulk:
    functions = registry.BULK
    queue_name = "bulk"
    max_tries = 3
    job_timeout = 90
    # Два фоновых воркера при LLM_RPM_BULK=10 не упираются в лимит (§10.3).
    max_jobs = settings.BULK_MAX_JOBS
    keep_result = settings.JOB_KEEP_RESULT_S
    cron_jobs = _cron_jobs()
    on_startup = startup_bulk
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
