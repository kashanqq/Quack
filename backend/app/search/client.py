"""Program search and bounded page text retrieval."""

from urllib.parse import urlsplit

import httpx
from ddgs import DDGS
from selectolax.parser import HTMLParser
from tavily import TavilyClient

from app.config import settings
from app.errors import SearchUnavailable, ValidationFailed
from app.schemas.programs import SearchHit


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
    except httpx.HTTPError as exc:
        raise SearchUnavailable("page fetch unavailable") from exc
    tree = HTMLParser(response.text)
    for node in tree.css("script, style, noscript, svg, nav, footer"):
        node.decompose()
    content = tree.body or tree.root
    return " ".join(content.text(separator=" ", strip=True).split())[:max_chars]
