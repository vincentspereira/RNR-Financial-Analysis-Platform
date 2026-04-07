"""
News client for fetching financial news from multiple sources.

Integrates with NewsAPI, Finnhub, and Alpha Vantage to aggregate
financial news articles for sentiment analysis.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.services.sentiment.news_client")


class NewsClient:
    """Async client for fetching financial news from multiple APIs."""

    def __init__(self) -> None:
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def fetch_news(
        self, symbol: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Fetch news from all configured sources and merge results.

        Args:
            symbol: Stock ticker symbol.
            days: Number of days to look back.

        Returns:
            List of normalized news article dicts.
        """
        articles: List[Dict[str, Any]] = []
        seen_titles = set()

        # Fetch from each source
        sources = [
            self.fetch_from_newsapi,
            self.fetch_from_finnhub,
        ]

        for source_func in sources:
            try:
                source_articles = await source_func(symbol, days)
                for article in source_articles:
                    title_key = article.get("title", "").lower().strip()
                    if title_key and title_key not in seen_titles:
                        seen_titles.add(title_key)
                        articles.append(article)
            except Exception as exc:
                logger.warning(f"Error fetching from {source_func.__name__}: {exc}")

        # Sort by date (most recent first)
        articles.sort(
            key=lambda a: a.get("published_at", datetime.min.replace(tzinfo=timezone.utc)),
            reverse=True,
        )

        return articles

    async def fetch_from_newsapi(
        self, symbol: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        """Fetch news from NewsAPI."""
        api_key = getattr(settings, "NEWSAPI_KEY", None)
        if not api_key:
            return []

        client = await self._get_client()
        from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": f"{symbol} stock",
                "from": from_date,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": 50,
                "apiKey": api_key,
            }

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            articles = []
            for item in data.get("articles", []):
                pub_date = item.get("publishedAt")
                if pub_date:
                    try:
                        pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pub_date = None

                articles.append({
                    "title": item.get("title", ""),
                    "source": item.get("source", {}).get("name", "NewsAPI"),
                    "url": item.get("url"),
                    "published_at": pub_date,
                    "summary": item.get("description", ""),
                    "symbol": symbol.upper(),
                })

            return articles

        except httpx.HTTPStatusError as exc:
            logger.warning(f"NewsAPI HTTP error: {exc.response.status_code}")
            return []
        except Exception as exc:
            logger.error(f"NewsAPI error: {exc}")
            return []

    async def fetch_from_finnhub(
        self, symbol: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        """Fetch news from Finnhub."""
        api_key = getattr(settings, "FINNHUB_API_KEY", None)
        if not api_key:
            return []

        client = await self._get_client()
        now = datetime.now(timezone.utc)
        from_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        to_date = now.strftime("%Y-%m-%d")

        try:
            url = "https://finnhub.io/api/v1/company-news"
            params = {
                "symbol": symbol.upper(),
                "from": from_date,
                "to": to_date,
                "token": api_key,
            }

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            articles = []
            for item in data:
                pub_date = None
                ts = item.get("datetime")
                if ts:
                    try:
                        pub_date = datetime.fromtimestamp(ts, tz=timezone.utc)
                    except (ValueError, TypeError, OSError):
                        pass

                articles.append({
                    "title": item.get("headline", ""),
                    "source": item.get("source", "Finnhub"),
                    "url": item.get("url"),
                    "published_at": pub_date,
                    "summary": item.get("summary", ""),
                    "symbol": symbol.upper(),
                })

            return articles

        except httpx.HTTPStatusError as exc:
            logger.warning(f"Finnhub HTTP error: {exc.response.status_code}")
            return []
        except Exception as exc:
            logger.error(f"Finnhub error: {exc}")
            return []
