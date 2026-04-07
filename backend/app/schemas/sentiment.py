"""
Pydantic v2 schemas for sentiment analysis endpoints.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NewsArticle(BaseModel):
    """A news article with optional sentiment data."""
    title: str
    source: str
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    symbol: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None


class SentimentRequest(BaseModel):
    """Request to analyze sentiment for symbols."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"symbols": ["AAPL", "MSFT"], "days": 7}
        }
    )

    symbols: List[str] = Field(..., min_length=1, max_length=20)
    days: Optional[int] = Field(default=7, ge=1, le=90)


class SentimentScore(BaseModel):
    """Sentiment score and label."""
    score: float
    label: str
    confidence: float


class TickerSentiment(BaseModel):
    """Aggregated sentiment for a ticker."""
    symbol: str
    overall_sentiment: SentimentScore
    article_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    sentiment_trend: str
    recent_articles: List[NewsArticle]
    score_history: List[Dict[str, Any]]


class SentimentResponse(BaseModel):
    """Response with sentiment analysis results."""
    results: List[TickerSentiment]
    analyzed_at: datetime


class SentimentDashboardRequest(BaseModel):
    """Request for sentiment dashboard overview."""
    symbols: List[str] = Field(..., min_length=1, max_length=50)


class SentimentDashboardResponse(BaseModel):
    """Dashboard with sentiment overview for multiple symbols."""
    most_positive: List[Dict[str, Any]]
    most_negative: List[Dict[str, Any]]
    sentiment_overview: Dict[str, float]
    total_articles_analyzed: int
    analyzed_at: datetime


class KeywordsResponse(BaseModel):
    """List of sentiment keywords."""
    positive: List[str]
    negative: List[str]
    total: int
