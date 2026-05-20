import time
import asyncio
import logging
from typing import Any

from app.clients import explore_client

logger = logging.getLogger(__name__)

# Module-level in-memory cache
# Format:
# - "trending": { (language, days): (data, expires_at) }
# - "hn_news": (data, expires_at)
# - "ai_tools": (data, expires_at)
_cache: dict[str, Any] = {
    "trending": {},
    "hn_news": (None, 0.0),
    "ai_tools": (None, 0.0),
}

# Cache TTL configurations (in seconds)
TRENDING_TTL = 900.0  # 15 minutes
HN_TTL = 600.0        # 10 minutes
AI_TTL = 600.0        # 10 minutes


class ExploreService:
    @staticmethod
    async def get_trending_repos(language: str | None = None, days: int = 7) -> list[dict[str, Any]]:
        """Retrieves and caches trending repositories from GitHub search API."""
        now = time.time()
        key = (language, days)
        cached_data, expires_at = _cache["trending"].get(key, (None, 0.0))

        if cached_data is not None and now < expires_at:
            logger.info("Serving trending repos from cache for language=%s, days=%d", language, days)
            return cached_data

        logger.info("Fetching fresh trending repos from GitHub for language=%s, days=%d", language, days)
        data = await explore_client.fetch_trending_repos(language, days)
        _cache["trending"][key] = (data, now + TRENDING_TTL)
        return data

    @staticmethod
    async def get_hn_news() -> list[dict[str, Any]]:
        """Retrieves and caches top Hacker News developer stories."""
        now = time.time()
        cached_data, expires_at = _cache["hn_news"]

        if cached_data is not None and now < expires_at:
            logger.info("Serving HN news from cache")
            return cached_data

        logger.info("Fetching fresh HN news")
        data = await explore_client.fetch_hn_news()
        _cache["hn_news"] = (data, now + HN_TTL)
        return data

    @staticmethod
    async def get_ai_tools() -> list[dict[str, Any]]:
        """Retrieves and caches trending AI and LLM developer tool repositories."""
        now = time.time()
        cached_data, expires_at = _cache["ai_tools"]

        if cached_data is not None and now < expires_at:
            logger.info("Serving AI tools from cache")
            return cached_data

        logger.info("Fetching fresh AI tools")
        data = await explore_client.fetch_ai_tools()
        _cache["ai_tools"] = (data, now + AI_TTL)
        return data

    @classmethod
    async def get_explore_data(cls, language: str | None = None, days: int = 7) -> dict[str, Any]:
        """Gathers trending repos, HN news, and AI tools in parallel."""
        trending_task = cls.get_trending_repos(language, days)
        hn_task = cls.get_hn_news()
        ai_task = cls.get_ai_tools()

        trending, hn, ai = await asyncio.gather(
            trending_task,
            hn_task,
            ai_task,
            return_exceptions=True,
        )

        return {
            "trending_repos": trending if isinstance(trending, list) else [],
            "hn_news": hn if isinstance(hn, list) else [],
            "ai_tools": ai if isinstance(ai, list) else [],
        }
