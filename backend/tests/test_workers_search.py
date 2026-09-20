"""Infrastructure worker and search tests without external services."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import structlog
from pydantic import SecretStr

from app.config import settings
from app.errors import SearchUnavailable, ValidationFailed
from app.schemas.programs import SearchHit
from app.search import client as search
from app.search.extract import extract_program
from app.workers import main as workers
from app.workers.registry import (
    BULK,
    INTERACTIVE,
    JOB_QUEUES,
    JOB_TIMEOUTS,
    ping,
)


async def test_worker_registry_and_queue_settings():
    assert INTERACTIVE[0] is ping
    assert BULK[0] is ping
    assert await ping({}, "request-id") == "pong"
    assert workers.WorkerInteractive.queue_name == "interactive"
    assert workers.WorkerInteractive.max_tries == 3
    assert workers.WorkerInteractive.job_timeout == 30
    assert workers.WorkerBulk.queue_name == "bulk"
    assert workers.WorkerBulk.max_tries == 3
    assert workers.WorkerBulk.job_timeout == 90


async def test_llm_jobs_declare_their_own_timeout():
    """Очередь interactive живёт с job_timeout=30, а наблюдатель ходит в LLM
    на слоте bulk (LLM_TIMEOUT_BULK_S): без собственного таймаута задача
    гарантированно не укладывалась (phase3 §3.12, F19)."""
    by_name = {
        entry.name: entry for entry in (*INTERACTIVE, *BULK) if hasattr(entry, "name")
    }
    # Фаза 4 (§1.2) дополнила оба реестра; таймаут у каждой задачи свой.
    assert (
        set(by_name)
        == set(JOB_TIMEOUTS)
        == {
            "observe_chat",
            "canonize_misconception",
            "set_summary",
            "pregenerate_set",
            "soft_match",
            "extract_program",
            "search_programs",
            "realism_texts",
            "compare_text",
            "daily_aggregates",
            "recommendations_batch",
            "outbox_replay",
            # Фаза 5 (§13.3).
            "recover_graph_events",
        }
    )
    assert by_name["observe_chat"].timeout_s == settings.OBSERVER_JOB_TIMEOUT_S
    assert by_name["observe_chat"].timeout_s > settings.LLM_TIMEOUT_BULK_S
    assert by_name["canonize_misconception"].timeout_s == settings.CANON_JOB_TIMEOUT_S
    assert JOB_QUEUES["observe_chat"] == "interactive"
    assert by_name["observe_chat"] in INTERACTIVE
    assert by_name["canonize_misconception"] in INTERACTIVE
    assert [entry.name for entry in BULK[1:]] == [
        "pregenerate_set",
        "soft_match",
        "extract_program",
        "search_programs",
        "realism_texts",
        "compare_text",
        "daily_aggregates",
        "recommendations_batch",
        "outbox_replay",
        "recover_graph_events",
    ]
    assert by_name["set_summary"] in INTERACTIVE
    assert JOB_QUEUES["set_summary"] == "interactive"
    for name in ("observe_chat", "canonize_misconception", "set_summary"):
        assert by_name[name].max_tries == 3
    # Дедупликация по `job_id` работает только пока ARQ держит результат;
    # часовое значение по умолчанию душило бы повторные постановки (§1.3).
    assert workers.WorkerBulk.keep_result == settings.JOB_KEEP_RESULT_S
    assert workers.WorkerBulk.max_jobs == settings.BULK_MAX_JOBS
    for entry in by_name.values():
        assert entry.timeout_s <= settings.JOB_TIMEOUT_MAX_S
    # a finished observer must not keep its job id busy for keep_result
    assert by_name["observe_chat"].keep_result_s == 0


async def test_worker_startup_shutdown_reuses_factories(monkeypatch):
    engine = object()
    driver = object()
    redis = SimpleNamespace(aclose=AsyncMock())
    llm = SimpleNamespace(aclose=AsyncMock())
    close_engine = AsyncMock()
    close_driver = AsyncMock()
    graph = SimpleNamespace(
        create_driver=lambda _settings: driver, close_driver=close_driver
    )
    llm_module = SimpleNamespace(LLMClient=lambda _settings, _redis: llm)
    monkeypatch.setattr(workers, "create_engine", lambda _settings: engine)
    monkeypatch.setattr(workers, "create_sessionmaker", lambda _engine: "sessions")
    monkeypatch.setattr(workers, "close_engine", close_engine)
    monkeypatch.setattr(workers.redis_async, "from_url", lambda _url: redis)
    monkeypatch.setattr(
        workers,
        "_optional_layer",
        lambda name: graph if name == "app.graph.client" else llm_module,
    )
    ctx = {}
    await workers.startup(ctx)
    assert ctx["sessionmaker"] == "sessions"
    assert ctx["neo4j"] is driver
    assert ctx["redis"] is redis
    assert ctx["llm"] is llm
    await workers.shutdown(ctx)
    llm.aclose.assert_awaited_once()
    redis.aclose.assert_awaited_once()
    close_driver.assert_awaited_once_with(driver)
    close_engine.assert_awaited_once_with(engine)


async def test_worker_preserves_arq_redis_pool(monkeypatch):
    arq_pool = SimpleNamespace(aclose=AsyncMock())
    monkeypatch.setattr(workers, "create_engine", lambda _settings: object())
    monkeypatch.setattr(workers, "create_sessionmaker", lambda _engine: object())
    monkeypatch.setattr(workers, "close_engine", AsyncMock())
    monkeypatch.setattr(workers, "_optional_layer", lambda _name: None)
    ctx = {"redis": arq_pool}
    await workers.startup(ctx)
    await workers.shutdown(ctx)
    arq_pool.aclose.assert_not_awaited()


async def test_enqueue_propagates_request_id_and_rejects_other_queues():
    redis = SimpleNamespace(
        enqueue_job=AsyncMock(return_value=SimpleNamespace(job_id="j1"))
    )
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id="trace-123")
    try:
        assert await workers.enqueue(redis, "bulk", "ping") == "j1"
        redis.enqueue_job.assert_awaited_once_with(
            "ping", _queue_name="bulk", request_id="trace-123"
        )
        with pytest.raises(ValueError):
            await workers.enqueue(redis, "wrong", "ping")
    finally:
        structlog.contextvars.clear_contextvars()


def test_tavily_result_is_search_hit(monkeypatch):
    calls = []

    class FakeTavily:
        def __init__(self, api_key):
            calls.append(api_key)

        def search(self, query, **kwargs):
            calls.append((query, kwargs))
            return {
                "results": [
                    {"title": "School", "url": "https://x.test", "content": "Study"}
                ]
            }

    monkeypatch.setattr(
        search, "settings", SimpleNamespace(TAVILY_API_KEY=SecretStr("test-key"))
    )
    monkeypatch.setattr(search, "TavilyClient", FakeTavily)
    result = search.search_programs("math", n=3)
    assert result == [SearchHit(title="School", url="https://x.test", snippet="Study")]
    assert calls[1] == (
        "math",
        {"search_depth": "basic", "max_results": 3, "timeout": 10},
    )


def test_ddgs_fallback_and_both_errors(monkeypatch):
    class FakeDDGS:
        def __init__(self, timeout):
            assert timeout == 10

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def text(self, query, max_results):
            return [{"title": "Fallback", "href": "https://y.test", "body": "Course"}]

    monkeypatch.setattr(
        search, "settings", SimpleNamespace(TAVILY_API_KEY=SecretStr("key"))
    )
    monkeypatch.setattr(search, "_tavily", lambda *_: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(search, "DDGS", FakeDDGS)
    assert search.search_programs("math") == [
        SearchHit(title="Fallback", url="https://y.test", snippet="Course")
    ]
    monkeypatch.setattr(search, "_ddgs", lambda *_: (_ for _ in ()).throw(OSError()))
    with pytest.raises(SearchUnavailable):
        search.search_programs("math")


async def test_fetch_page_strips_html_and_rejects_non_http(monkeypatch):
    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs == {
                "timeout": 10,
                "follow_redirects": True,
                "headers": {"User-Agent": "QuackBot/0.1"},
            }

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def get(self, _url):
            return SimpleNamespace(
                text=(
                    "<h1>Welcome</h1><script>private()</script>"
                    "<p>Math &amp; science</p>"
                ),
                headers={"content-type": "text/html"},
                raise_for_status=lambda: None,
            )

    monkeypatch.setattr(search.httpx, "AsyncClient", FakeClient)
    assert (
        await search.fetch_page("https://school.test", max_chars=12) == "Welcome Math"
    )
    with pytest.raises(ValidationFailed):
        await search.fetch_page("file:///etc/passwd")


async def test_extract_program_calls_the_model_with_the_page_text():
    """Фаза 4 (§6.4): граница закрыта — извлечение идёт через structured
    output, а `html` это уже текст страницы из `fetch_page`."""
    from app.schemas.programs import ExtractedProgram

    class FakeLLM:
        def __init__(self):
            self.calls = []

        async def structured(self, messages, schema, slot):
            self.calls.append((messages, schema, slot))
            return ExtractedProgram(university="MIT")

    llm = FakeLLM()
    result = await extract_program(llm, "page text", "https://school.test")
    assert result.university == "MIT"
    messages, schema, slot = llm.calls[0]
    assert schema is ExtractedProgram
    assert slot == "bulk"
    assert "page text" in messages[0].content
