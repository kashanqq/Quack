"""Search limits, URL hygiene and fetch failures — §13.3."""

from types import SimpleNamespace

import pytest

from app.config import KnowledgeParams, settings
from app.errors import SearchUnavailable, ValidationFailed
from app.search import client as search

pytestmark = pytest.mark.phase4

PARAMS = KnowledgeParams()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://WWW.Example.com/a/b/", "https://example.com/a/b"),
        ("https://example.com/a?utm_source=x&q=1", "https://example.com/a?q=1"),
        ("https://example.com/a#section", "https://example.com/a"),
        ("http://example.com:80/a", "http://example.com/a"),
        ("https://example.com", "https://example.com/"),
    ],
)
def test_url_normalization(raw, expected):
    assert search.normalize_url(raw) == expected


def test_the_same_page_normalizes_to_one_key():
    first = search.normalize_url("https://mit.edu/cs/?utm_campaign=ads#top")
    second = search.normalize_url("http://www.MIT.edu/cs")
    assert first.split("://", 1)[1] == second.split("://", 1)[1]


@pytest.mark.parametrize(
    ("url", "allowed"),
    [
        ("https://mit.edu/programs", True),
        ("https://reddit.com/r/sat", False),
        ("https://old.reddit.com/r/sat", False),
        ("https://mit.edu/handbook.pdf", False),
        ("ftp://mit.edu/x", False),
        ("not a url", False),
    ],
)
def test_denylist_and_scheme_filtering(url, allowed):
    assert search.allowed_url(url, PARAMS) is allowed


async def test_rate_limit_raises_after_the_minute_budget(redis, monkeypatch):
    monkeypatch.setattr(settings, "SEARCH_RPM", 2)
    await search.acquire_slot(redis)
    await search.acquire_slot(redis)
    with pytest.raises(SearchUnavailable, match="rate limit"):
        await search.acquire_slot(redis)


async def test_a_missing_redis_never_blocks_the_only_working_path():
    class _Broken:
        async def incr(self, _key):
            raise OSError("redis down")

    await search.acquire_slot(_Broken())  # не бросает
    await search.acquire_slot(None)


async def test_monthly_cap_falls_back_to_the_free_provider(redis, monkeypatch):
    monkeypatch.setattr(settings, "SEARCH_MONTHLY_CAP", 1)
    monkeypatch.setattr(
        settings, "TAVILY_API_KEY", SimpleNamespace(get_secret_value=lambda: "key")
    )
    tavily_calls, ddgs_calls = [], []
    monkeypatch.setattr(search, "_tavily", lambda *a: tavily_calls.append(a) or [])
    monkeypatch.setattr(search, "_ddgs", lambda *a: ddgs_calls.append(a) or [])

    await search.search_programs_limited(redis, "query", 3)
    await search.search_programs_limited(redis, "query", 3)
    # Первый запрос израсходовал месячный бюджет, второй ушёл в ddgs.
    assert len(tavily_calls) == 1
    assert len(ddgs_calls) == 1


async def test_both_providers_down_record_the_error_for_health(redis, monkeypatch):
    monkeypatch.setattr(
        settings, "TAVILY_API_KEY", SimpleNamespace(get_secret_value=lambda: "")
    )

    def boom(*_args):
        raise RuntimeError("no network")

    monkeypatch.setattr(search, "_ddgs", boom)
    with pytest.raises(SearchUnavailable):
        await search.search_programs_limited(redis, "query", 3)
    from app import keys

    assert await redis.get(keys.search_last_error()) is not None


async def test_fetch_failure_carries_the_http_status(monkeypatch):
    import httpx

    class _Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get(self, url):
            request = httpx.Request("GET", url)
            response = httpx.Response(404, request=request)
            response.raise_for_status()

    monkeypatch.setattr(search.httpx, "AsyncClient", _Client)
    with pytest.raises(search.FetchFailed) as caught:
        await search.fetch_page("https://school.test")
    assert caught.value.status == 404


async def test_a_non_html_content_type_is_refused(monkeypatch):
    class _Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def get(self, _url):
            return SimpleNamespace(
                text="%PDF-1.4",
                headers={"content-type": "application/pdf"},
                raise_for_status=lambda: None,
            )

    monkeypatch.setattr(search.httpx, "AsyncClient", _Client)
    with pytest.raises(search.FetchFailed) as caught:
        await search.fetch_page("https://school.test/file")
    assert caught.value.status == 415


async def test_a_non_http_url_is_a_validation_error():
    with pytest.raises(ValidationFailed):
        await search.fetch_page("file:///etc/passwd")
