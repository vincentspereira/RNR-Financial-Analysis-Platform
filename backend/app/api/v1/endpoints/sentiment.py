"""
Sentiment Analysis API endpoints.

Provides endpoints for analyzing market sentiment from news articles,
generating sentiment dashboards, and listing sentiment keywords.
"""
from datetime import datetime, timezone
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.schemas.sentiment import (
    KeywordsResponse,
    NewsArticle,
    SentimentDashboardRequest,
    SentimentDashboardResponse,
    SentimentRequest,
    SentimentResponse,
    SentimentScore,
    TickerSentiment,
)
from app.services.sentiment import news_client, sentiment_analyzer
from app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/sentiment", tags=["sentiment"])
logger = get_logger("api.sentiment")


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


async def get_current_user_from_token(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header format")
    access_token = authorization.split(" ")[1]
    user = await auth_service.verify_session(access_token, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is disabled")
    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/analyze",
    response_model=SentimentResponse,
    summary="Analyze sentiment",
    description="Analyze market sentiment for the given symbols based on recent news.",
)
async def analyze_sentiment(
    request: SentimentRequest,
    current_user=Depends(get_current_user_from_token),
):
    """Analyze sentiment for one or more symbols."""
    try:
        results = []

        for symbol in request.symbols:
            # Fetch news
            articles = await news_client.fetch_news(symbol, request.days or 7)

            # Analyze sentiment
            analyzed = sentiment_analyzer.analyze_batch(articles)

            # Aggregate
            aggregate = sentiment_analyzer.compute_aggregate_sentiment(analyzed, symbol)

            # Build response articles (limit to 10 most recent)
            recent = analyzed[:10]
            article_responses = [
                NewsArticle(
                    title=a.get("title", ""),
                    source=a.get("source", ""),
                    url=a.get("url"),
                    published_at=a.get("published_at"),
                    summary=a.get("summary"),
                    symbol=a.get("symbol"),
                    sentiment_score=a.get("sentiment_score"),
                    sentiment_label=a.get("sentiment_label"),
                )
                for a in recent
            ]

            results.append(TickerSentiment(
                symbol=symbol.upper(),
                overall_sentiment=SentimentScore(
                    score=aggregate["overall_score"],
                    label=aggregate["overall_label"],
                    confidence=aggregate["overall_confidence"],
                ),
                article_count=aggregate["article_count"],
                positive_count=aggregate["positive_count"],
                negative_count=aggregate["negative_count"],
                neutral_count=aggregate["neutral_count"],
                sentiment_trend=aggregate["sentiment_trend"],
                recent_articles=article_responses,
                score_history=aggregate["score_history"],
            ))

        return SentimentResponse(
            results=results,
            analyzed_at=datetime.now(timezone.utc),
        )

    except Exception as exc:
        logger.error(f"Sentiment analysis error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Sentiment analysis failed. Please try again later.")


@router.post(
    "/dashboard",
    response_model=SentimentDashboardResponse,
    summary="Sentiment dashboard",
    description="Get a sentiment dashboard overview for multiple symbols.",
)
async def sentiment_dashboard(
    request: SentimentDashboardRequest,
    current_user=Depends(get_current_user_from_token),
):
    """Get sentiment dashboard overview for multiple symbols."""
    try:
        sentiment_overview = {}
        all_articles_count = 0

        for symbol in request.symbols:
            articles = await news_client.fetch_news(symbol, days=7)
            analyzed = sentiment_analyzer.analyze_batch(articles)
            aggregate = sentiment_analyzer.compute_aggregate_sentiment(analyzed, symbol)

            sentiment_overview[symbol.upper()] = aggregate["overall_score"]
            all_articles_count += aggregate["article_count"]

        # Sort by sentiment
        sorted_symbols = sorted(sentiment_overview.items(), key=lambda x: x[1], reverse=True)

        most_positive = [
            {"symbol": s, "score": score}
            for s, score in sorted_symbols[:5]
            if score > 0
        ]
        most_negative = [
            {"symbol": s, "score": score}
            for s, score in sorted_symbols[-5:]
            if score < 0
        ]

        return SentimentDashboardResponse(
            most_positive=most_positive,
            most_negative=most_negative,
            sentiment_overview=sentiment_overview,
            total_articles_analyzed=all_articles_count,
            analyzed_at=datetime.now(timezone.utc),
        )

    except Exception as exc:
        logger.error(f"Sentiment dashboard error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Dashboard generation failed. Please try again later.")


@router.get(
    "/news/{symbol}",
    summary="Get recent news",
    description="Fetch recent news articles for a symbol.",
)
async def get_recent_news(
    symbol: str,
    days: int = 7,
    current_user=Depends(get_current_user_from_token),
):
    """Get recent news articles for a symbol."""
    try:
        articles = await news_client.fetch_news(symbol, days)
        analyzed = sentiment_analyzer.analyze_batch(articles)

        return {
            "symbol": symbol.upper(),
            "articles": analyzed,
            "total": len(analyzed),
            "days": days,
        }

    except Exception as exc:
        logger.error(f"News fetch error for {symbol}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch news. Please try again later.")


@router.get(
    "/keywords",
    response_model=KeywordsResponse,
    summary="List sentiment keywords",
    description="Get the positive and negative keyword lists used for sentiment analysis.",
)
async def get_keywords(
    current_user=Depends(get_current_user_from_token),
):
    """Get the financial sentiment keyword lists."""
    keywords = sentiment_analyzer.get_financial_keywords()
    return KeywordsResponse(
        positive=keywords["positive"],
        negative=keywords["negative"],
        total=len(keywords["positive"]) + len(keywords["negative"]),
    )
