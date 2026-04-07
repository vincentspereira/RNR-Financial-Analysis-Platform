"""
Sentiment analyzer using financial lexicon-based approach.

Scores news articles from -1.0 (very negative) to +1.0 (very positive)
using financial domain-specific keyword lists and recency weighting.
"""
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger

logger = get_logger("app.services.sentiment.analyzer")

# Financial sentiment lexicons
POSITIVE_KEYWORDS = {
    # Strong positive
    "bullish": 0.8, "surge": 0.7, "soar": 0.7, "rally": 0.6, "breakout": 0.6,
    "outperform": 0.7, "upgrade": 0.6, "strong buy": 0.8, "buy rating": 0.6,
    "profit": 0.5, "profits": 0.5, "profitable": 0.5,
    # Moderate positive
    "growth": 0.4, "growing": 0.4, "grew": 0.4, "gain": 0.4, "gains": 0.4,
    "beat": 0.5, "beats": 0.5, "exceeded": 0.5, "exceeds": 0.5,
    "revenue growth": 0.5, "earnings beat": 0.6, "raised": 0.4,
    "dividend": 0.3, "buyback": 0.4, "share repurchase": 0.4,
    "innovation": 0.3, "expansion": 0.4, "partnership": 0.3,
    "record": 0.4, "all-time high": 0.6, "new high": 0.5,
    "optimistic": 0.5, "positive": 0.4, "confident": 0.4,
    "recovery": 0.4, "resilient": 0.3, "robust": 0.4,
    "outperforming": 0.5, "undervalued": 0.4, "attractive": 0.3,
    "momentum": 0.3, "upside": 0.4, "opportunity": 0.3,
}

NEGATIVE_KEYWORDS = {
    # Strong negative
    "bearish": -0.8, "crash": -0.8, "collapse": -0.8, "plunge": -0.7,
    "sell-off": -0.7, "bankruptcy": -0.9, "insolvent": -0.9,
    "strong sell": -0.8, "sell rating": -0.6,
    # Moderate negative
    "decline": -0.4, "declining": -0.4, "declined": -0.4,
    "drop": -0.4, "drops": -0.4, "dropped": -0.4, "falling": -0.4,
    "loss": -0.5, "losses": -0.5, "losing": -0.4,
    "miss": -0.5, "missed": -0.5, "misses": -0.5,
    "downgrade": -0.6, "underperform": -0.5, "cut": -0.4,
    "debt": -0.3, "default": -0.6, "lawsuit": -0.4,
    "recession": -0.5, "downturn": -0.4, "contraction": -0.4,
    "warning": -0.3, "warned": -0.4, "caution": -0.2,
    "weak": -0.4, "weakness": -0.4, "disappointing": -0.4,
    "disappointed": -0.4, "below expectations": -0.5,
    "overvalued": -0.3, "overpriced": -0.3, "bubble": -0.5,
    "risk": -0.2, "risky": -0.3, "uncertain": -0.3, "uncertainty": -0.3,
    "volatility": -0.2, "turbulent": -0.3, "slump": -0.5,
    "layoffs": -0.4, "job cuts": -0.4, "restructuring": -0.3,
    "regulatory": -0.2, "investigation": -0.4, "fraud": -0.7,
}

# Negation words that flip sentiment
NEGATION_WORDS = {"not", "no", "never", "neither", "nobody", "nothing", "nowhere", "hardly", "barely"}


class SentimentAnalyzer:
    """Rule-based sentiment analyzer using financial keyword lexicons."""

    def analyze_article(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a single text article.

        Args:
            text: Article title and/or body text.

        Returns:
            Dict with score (-1.0 to 1.0), label, and confidence.
        """
        if not text:
            return {"score": 0.0, "label": "neutral", "confidence": 0.0}

        text_lower = text.lower()
        words = re.findall(r"\b\w+\b", text_lower)

        total_score = 0.0
        match_count = 0

        # Check for multi-word phrases first
        for phrase, weight in {**POSITIVE_KEYWORDS, **NEGATIVE_KEYWORDS}.items():
            if " " in phrase and phrase in text_lower:
                # Check for negation before the phrase
                negated = self._check_negation(text_lower, phrase)
                total_score += (-weight if negated else weight)
                match_count += 1

        # Check single-word matches
        single_positive = {k: v for k, v in POSITIVE_KEYWORDS.items() if " " not in k}
        single_negative = {k: v for k, v in NEGATIVE_KEYWORDS.items() if " " not in k}

        for i, word in enumerate(words):
            if word in single_positive:
                negated = self._check_word_negation(words, i)
                total_score += (-single_positive[word] if negated else single_positive[word])
                match_count += 1
            elif word in single_negative:
                negated = self._check_word_negation(words, i)
                total_score += (-single_negative[word] if negated else single_negative[word])
                match_count += 1

        # Normalize score
        if match_count > 0:
            raw_score = total_score / match_count
            score = max(-1.0, min(1.0, raw_score))
            confidence = min(1.0, match_count / 5.0)  # More matches = higher confidence
        else:
            score = 0.0
            confidence = 0.0

        # Determine label
        if score > 0.15:
            label = "positive"
        elif score < -0.15:
            label = "negative"
        else:
            label = "neutral"

        return {
            "score": round(score, 4),
            "label": label,
            "confidence": round(confidence, 4),
        }

    def analyze_batch(
        self, articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for a batch of articles.

        Args:
            articles: List of article dicts with 'title' and optionally 'summary'.

        Returns:
            Articles with sentiment_score and sentiment_label added.
        """
        results = []
        for article in articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}"
            sentiment = self.analyze_article(text)
            article_copy = {**article}
            article_copy["sentiment_score"] = sentiment["score"]
            article_copy["sentiment_label"] = sentiment["label"]
            results.append(article_copy)
        return results

    def compute_aggregate_sentiment(
        self, articles: List[Dict[str, Any]], symbol: str
    ) -> Dict[str, Any]:
        """
        Compute aggregate sentiment for a symbol from analyzed articles.

        Applies recency weighting - more recent articles get higher weight.

        Args:
            articles: List of articles with sentiment scores.
            symbol: The ticker symbol.

        Returns:
            Aggregate sentiment with breakdown and trend.
        """
        if not articles:
            return {
                "symbol": symbol,
                "overall_score": 0.0,
                "overall_label": "neutral",
                "overall_confidence": 0.0,
                "article_count": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "sentiment_trend": "stable",
                "score_history": [],
            }

        now = datetime.now(timezone.utc)
        total_weighted_score = 0.0
        total_weight = 0.0
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        score_history = []

        for article in articles:
            score = article.get("sentiment_score", 0.0)
            label = article.get("sentiment_label", "neutral")

            if label == "positive":
                positive_count += 1
            elif label == "negative":
                negative_count += 1
            else:
                neutral_count += 1

            # Recency weight: articles from last 24h get weight 1.0,
            # older articles decay linearly over 7 days
            pub_date = article.get("published_at")
            if pub_date:
                if isinstance(pub_date, str):
                    try:
                        pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pub_date = now

                age_hours = max(0, (now - pub_date).total_seconds() / 3600)
                if age_hours < 24:
                    weight = 1.0
                elif age_hours < 168:  # 7 days
                    weight = 1.0 - ((age_hours - 24) / 144) * 0.6
                else:
                    weight = 0.2
            else:
                weight = 0.5

            total_weighted_score += score * weight
            total_weight += weight

            if pub_date:
                date_key = pub_date.strftime("%Y-%m-%d") if hasattr(pub_date, "strftime") else str(pub_date)[:10]
                score_history.append({"date": date_key, "score": round(score, 4)})

        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        overall_score = round(max(-1.0, min(1.0, overall_score)), 4)

        if overall_score > 0.15:
            overall_label = "positive"
        elif overall_score < -0.15:
            overall_label = "negative"
        else:
            overall_label = "neutral"

        # Determine trend by comparing recent vs older articles
        sentiment_trend = "stable"
        if len(score_history) >= 4:
            half = len(score_history) // 2
            recent_scores = [s["score"] for s in score_history[:half]]
            older_scores = [s["score"] for s in score_history[half:]]
            recent_avg = sum(recent_scores) / len(recent_scores)
            older_avg = sum(older_scores) / len(older_scores)
            diff = recent_avg - older_avg
            if diff > 0.1:
                sentiment_trend = "improving"
            elif diff < -0.1:
                sentiment_trend = "declining"

        confidence = min(1.0, len(articles) / 10.0)

        return {
            "symbol": symbol,
            "overall_score": overall_score,
            "overall_label": overall_label,
            "overall_confidence": round(confidence, 4),
            "article_count": len(articles),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "sentiment_trend": sentiment_trend,
            "score_history": score_history,
        }

    def get_financial_keywords(self) -> Dict[str, List[str]]:
        """Return the positive and negative keyword lists."""
        return {
            "positive": sorted(POSITIVE_KEYWORDS.keys()),
            "negative": sorted(NEGATIVE_KEYWORDS.keys()),
        }

    def _check_negation(self, text: str, phrase: str) -> bool:
        """Check if there's a negation word before a phrase in text."""
        idx = text.find(phrase)
        if idx <= 0:
            return False
        preceding = text[:idx].strip().split()
        if preceding:
            last_word = preceding[-1].lower()
            return last_word in NEGATION_WORDS
        return False

    def _check_word_negation(self, words: List[str], index: int) -> bool:
        """Check if a word at index is negated by preceding words."""
        lookback = min(3, index)
        for i in range(index - lookback, index):
            if i >= 0 and words[i] in NEGATION_WORDS:
                return True
        return False
