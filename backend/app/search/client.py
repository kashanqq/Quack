"""Program search and bounded page text retrieval.

Phase 4 (§6.2, §10.5) adds the limits around the two providers: a per-minute
counter, a monthly Tavily cap that silently falls back to `ddgs`, URL
normalization and a denylist, and an HTTP status on fetch failures so a 404
is not retried like a timeout.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import structlog
from ddgs import DDGS
from redis.exceptions import RedisError
from selectolax.parser import HTMLParser
from tavily import TavilyClient

from app import keys
from app.config import KnowledgeParams, settings
from app.errors import SearchUnavailable, ValidationFailed
from app.schemas.programs import SearchHit

_logger = structlog.get_logger(__name__)

_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {"fbclid", "gclid", "yclid", "mc_cid", "mc_eid", "ref", "_ga"}
_BINARY_SUFFIXES = (
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".rar",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".mp4",
)


class FetchFailed(SearchUnavailable):
    """A page fetch that failed with a known HTTP status (§6.3).

    4xx is final — the page will not appear on a retry; 5xx and timeouts are
    transient and the job defers.
    """

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def normalize_url(url: str) -> str:
    """Lowercase host, no fragment, no tracking parameters, no trailing slash."""
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if (scheme == "http" and netloc.endswith(":80")) or (
        scheme == "https" and netloc.endswith(":443")
    ):
        netloc = netloc.rsplit(":", 1)[0]
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() not in _TRACKING_KEYS
            and not key.lower().startswith(_TRACKING_PREFIXES)
        ]
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, query, ""))


def allowed_url(url: str, params: KnowledgeParams) -> bool:
    """http(s), not a denylisted domain, not an obviously binary file."""
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return False
    host = parts.netloc.lower().split(":", 1)[0]
    for denied in params.program_domain_denylist:
        denied = denied.lower()
        if host == denied or host.endswith(f".{denied}"):
            return False
    return not parts.path.lower().endswith(_BINARY_SUFFIXES)


def _tavily(query: str, n: int, api_key: str) -> list[SearchHit]:
    result = TavilyClient(api_key=api_key).search(
        query, search_depth="basic", max_results=n, timeout=10
    )
    return [
        SearchHit(
            title=item.get("title") or "",
            url=item["url"],
            snippet=item.get("content") or "",
        )
        for item in result.get("results", [])[:n]
    ]


def _ddgs(query: str, n: int) -> list[SearchHit]:
    with DDGS(timeout=10) as client:
        result = client.text(query, max_results=n)
    return [
        SearchHit(
            title=item.get("title") or "",
            url=item["href"],
            snippet=item.get("body") or "",
        )
        for item in result[:n]
    ]


def search_programs(query: str, n: int = 5) -> list[SearchHit]:
    """Tavily when a key is configured, `ddgs` otherwise; both down — raise."""
    api_key = settings.TAVILY_API_KEY.get_secret_value()
    if api_key:
        try:
            return _tavily(query, n, api_key)
        except Exception:
            pass
    try:
        return _ddgs(query, n)
    except Exception as exc:
        raise SearchUnavailable("search unavailable") from exc


async def acquire_slot(redis: Any) -> None:
    """`SEARCH_RPM` per minute across all students (§10.5).

    Redis unavailable — the limiter yields, exactly like the LLM client's:
    a missing counter must not stop the only working path.
    """
    if redis is None:
        return
    key = keys.search_ratelimit()
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
    except (RedisError, OSError) as exc:
        _logger.warning("search_ratelimit_unavailable", error=str(exc))
        return
    if count > settings.SEARCH_RPM:
        raise SearchUnavailable("rate limit")


async def _tavily_allowed(redis: Any) -> bool:
    """False once the monthly Tavily budget is spent — fall back to `ddgs`."""
    if redis is None:
        return True
    key = keys.search_monthly(datetime.now(UTC).strftime("%Y%m"))
    try:
        used = await redis.incr(key)
        if used == 1:
            await redis.expire(key, 40 * 24 * 3600)
    except (RedisError, OSError):
        return True
    if used > settings.SEARCH_MONTHLY_CAP:
        _logger.info("tavily_cap_reached", used=used)
        return False
    return True


async def note_error(redis: Any, error: str | None) -> None:
    """`/health.checks.search` reads this key (§6.2)."""
    if redis is None:
        return
    try:
        if error is None:
            await redis.delete(keys.search_last_error())
        else:
            await redis.set(keys.search_last_error(), error[:200], ex=300)
    except (RedisError, OSError):
        return


async def search_programs_limited(
    redis: Any, query: str, n: int = 5
) -> list[SearchHit]:
    """The rate-limited, budget-aware entry point background jobs use."""
    await acquire_slot(redis)
    api_key = settings.TAVILY_API_KEY.get_secret_value()
    if api_key and await _tavily_allowed(redis):
        try:
            hits = await asyncio.to_thread(_tavily, query, n, api_key)
            await note_error(redis, None)
            return hits
        except Exception as exc:  # noqa: BLE001 — try the free provider next
            _logger.info("tavily_failed", error=str(exc)[:200])
    try:
        hits = await asyncio.to_thread(_ddgs, query, n)
    except Exception as exc:
        await note_error(redis, "search unavailable")
        raise SearchUnavailable("search unavailable") from exc
    await note_error(redis, None)
    return hits


async def fetch_page(url: str, max_chars: int = 40000) -> str:
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValidationFailed("http(s) URL required")
    try:
        async with httpx.AsyncClient(
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "QuackBot/0.1"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise FetchFailed(
            "page fetch unavailable", status=exc.response.status_code
        ) from exc
    except httpx.HTTPError as exc:
        raise FetchFailed("page fetch unavailable") from exc
    content_type = response.headers.get("content-type", "")
    if content_type and "html" not in content_type.split(";", 1)[0].lower():
        raise FetchFailed("not html", status=415)
    tree = HTMLParser(response.text)
    for node in tree.css("script, style, noscript, svg, nav, footer"):
        node.decompose()
    content = tree.body or tree.root
    return " ".join(content.text(separator=" ", strip=True).split())[:max_chars]
