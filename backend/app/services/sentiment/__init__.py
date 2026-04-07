"""
Sentiment analysis services.
"""
from app.services.sentiment.news_client import NewsClient
from app.services.sentiment.analyzer import SentimentAnalyzer

news_client = NewsClient()
sentiment_analyzer = SentimentAnalyzer()

__all__ = ["news_client", "sentiment_analyzer"]
