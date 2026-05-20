"""External API client for the Explore/Trending module.

All HTTP calls live here. Services orchestrate and cache.
"""
import asyncio
import logging
from datetime import date, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(8.0)
_GH_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
_GH_BASE = "https://api.github.com"
_HN_BASE = "https://hacker-news.firebaseio.com/v0"


async def fetch_trending_repos(language: str | None = None, days: int = 7) -> list[dict[str, Any]]:
    since = (date.today() - timedelta(days=days)).isoformat()
    q = f"created:>{since}"
    if language and language.lower() != "all":
        q += f" language:{language}"

    params = {"q": q, "sort": "stars", "order": "desc", "per_page": 12}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_GH_HEADERS) as client:
            resp = await client.get(f"{_GH_BASE}/search/repositories", params=params)
            if resp.status_code == 200:
                return [_fmt_repo(r) for r in resp.json().get("items", [])]
            logger.warning("GitHub search HTTP %d", resp.status_code)
    except Exception as exc:
        logger.warning("fetch_trending_repos failed: %s", exc)
    return []


async def fetch_hn_news(limit: int = 12) -> list[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{_HN_BASE}/topstories.json")
            if resp.status_code != 200:
                return []
            ids = resp.json()[: limit * 2]
            items = await asyncio.gather(
                *[_fetch_hn_item(client, sid) for sid in ids[:limit]],
                return_exceptions=True,
            )
            return [_fmt_hn(i) for i in items if isinstance(i, dict) and i.get("type") == "story"][:limit]
    except Exception as exc:
        logger.warning("fetch_hn_news failed: %s", exc)
    return []


async def _fetch_hn_item(client: httpx.AsyncClient, item_id: int) -> dict | None:
    try:
        resp = await client.get(f"{_HN_BASE}/item/{item_id}.json")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


async def fetch_ai_tools(limit: int = 12) -> list[dict[str, Any]]:
    since = (date.today() - timedelta(days=60)).isoformat()
    queries = [
        f"topic:llm created:>{since}",
        f"topic:ai-agent created:>{since}",
    ]
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_GH_HEADERS) as client:
            results = await asyncio.gather(
                *[
                    client.get(
                        f"{_GH_BASE}/search/repositories",
                        params={"q": q, "sort": "stars", "order": "desc", "per_page": 6},
                    )
                    for q in queries
                ],
                return_exceptions=True,
            )
        seen: set[int] = set()
        repos: list[dict] = []
        for r in results:
            if isinstance(r, httpx.Response) and r.status_code == 200:
                for item in r.json().get("items", []):
                    if item["id"] not in seen:
                        seen.add(item["id"])
                        repos.append(_fmt_repo(item))
        repos.sort(key=lambda x: x["stars"], reverse=True)
        return repos[:limit]
    except Exception as exc:
        logger.warning("fetch_ai_tools failed: %s", exc)
    return []


# ── Formatters ────────────────────────────────────────────────────────────────

def _fmt_repo(r: dict) -> dict[str, Any]:
    owner = r.get("owner") or {}
    return {
        "id": r.get("id"),
        "full_name": r.get("full_name", ""),
        "name": r.get("name", ""),
        "owner_login": owner.get("login", ""),
        "owner_avatar": owner.get("avatar_url", ""),
        "description": (r.get("description") or "")[:180],
        "language": r.get("language"),
        "stars": r.get("stargazers_count", 0),
        "forks": r.get("forks_count", 0),
        "topics": (r.get("topics") or [])[:5],
        "html_url": r.get("html_url", ""),
    }


def _fmt_hn(item: dict) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "title": item.get("title", ""),
        "url": item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id')}",
        "score": item.get("score", 0),
        "by": item.get("by", ""),
        "time": item.get("time", 0),
        "comments": item.get("descendants", 0),
        "hn_url": f"https://news.ycombinator.com/item?id={item.get('id')}",
    }
