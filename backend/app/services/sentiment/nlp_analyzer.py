"""
NLP-enhanced sentiment analyzer for financial news.

Layered approach:
  1. Lexicon-based (always available, fast)
  2. VADER sentiment (if nltk installed)
  3. FinBERT transformer (if transformers installed) — highest accuracy

Each layer refines the score; the final result includes per-layer scores
and a weighted ensemble.
"""
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

nlp_logger = get_logger("app.services.sentiment.nlp")

# --- Layer availability ---
VADER_AVAILABLE = False
try:
    from nltk.sentiment import SentimentIntensityAnalyzer
    sia = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
except ImportError:
    sia = None

TRANSFORMERS_AVAILABLE = False
try:
    from transformers import pipeline
    _finbert = pipeline(
        "sentiment-analysis",
        model="yiyanghkust/finbert-tone",
        top_k=None,
        device=-1,  # CPU by default; set to 0 for GPU
    )
    TRANSFORMERS_AVAILABLE = True
except Exception:
    _finbert = None

executor = ThreadPoolExecutor(max_workers=2)

# --- Financial lexicon (same as analyzer.py, kept here for self-containment) ---
POSITIVE_WORDS = {
    "bullish": 0.8, "surge": 0.7, "soar": 0.7, "rally": 0.6, "breakout": 0.6,
    "outperform": 0.7, "upgrade": 0.6, "strong buy": 0.8, "profit": 0.5,
    "growth": 0.4, "gain": 0.4, "beat": 0.5, "exceeded": 0.5,
    "dividend": 0.3, "buyback": 0.4, "record": 0.4, "optimistic": 0.5,
    "recovery": 0.4, "robust": 0.4, "undervalued": 0.4, "momentum": 0.3,
}

NEGATIVE_WORDS = {
    "bearish": -0.8, "crash": -0.8, "collapse": -0.8, "plunge": -0.7,
    "sell-off": -0.7, "bankruptcy": -0.9, "decline": -0.4, "drop": -0.4,
    "loss": -0.5, "miss": -0.5, "downgrade": -0.6, "debt": -0.3,
    "recession": -0.5, "warning": -0.3, "weak": -0.4, "overvalued": -0.3,
    "uncertainty": -0.3, "layoffs": -0.4, "fraud": -0.7, "investigation": -0.4,
}

NEGATION = {"not", "no", "never", "neither", "hardly", "barely"}


class NLPSentimentAnalyzer:
    """Multi-layer NLP sentiment analyzer for financial text."""

    def __init__(self):
        self._finbert_pipe = _finbert

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze a single piece of text with all available layers.

        Returns dict with per-layer scores and an ensemble result.
        """
        if not text or not text.strip():
            return self._empty_result()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, self._analyze_sync, text)

    async def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Analyze multiple texts in parallel."""
        tasks = [self.analyze(t) for t in texts]
        return await asyncio.gather(*tasks)

    async def analyze_articles(
        self,
        articles: List[Dict[str, Any]],
        symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a batch of news articles and compute aggregate sentiment.

        Each article should have 'title' and optionally 'summary'.
        """
        texts = []
        for a in articles:
            parts = [a.get("title", "")]
            if a.get("summary"):
                parts.append(a["summary"])
            texts.append(" ".join(parts))

        results = await self.analyze_batch(texts)

        # Merge results back into articles
        analyzed = []
        for article, result in zip(articles, results):
            merged = {**article}
            merged["nlp_sentiment"] = result
            analyzed.append(merged)

        # Compute aggregate
        aggregate = self._compute_aggregate(analyzed, symbol or "UNKNOWN")
        return {"articles": analyzed, "aggregate": aggregate}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _analyze_sync(self, text: str) -> Dict[str, Any]:
        layers = {}

        # Layer 1: Lexicon
        lex_score = self._lexicon_score(text)
        layers["lexicon"] = {
            "score": round(lex_score, 4),
            "label": self._score_to_label(lex_score),
        }

        # Layer 2: VADER
        if VADER_AVAILABLE and sia is not None:
            vader = sia.polarity_scores(text)
            vader_compound = vader["compound"]
            layers["vader"] = {
                "score": round(vader_compound, 4),
                "label": self._score_to_label(vader_compound),
                "detail": vader,
            }

        # Layer 3: FinBERT
        if TRANSFORMERS_AVAILABLE and self._finbert_pipe is not None:
            try:
                finbert_results = self._finbert_pipe(text[:512])
                # finbert_results is list of dicts per label
                if finbert_results and isinstance(finbert_results[0], list):
                    scores = {r["label"]: r["score"] for r in finbert_results[0]}
                elif isinstance(finbert_results, list):
                    scores = {r["label"]: r["score"] for r in finbert_results}
                else:
                    scores = {}

                positive = scores.get("Positive", scores.get("positive", 0))
                negative = scores.get("Negative", scores.get("negative", 0))
                neutral = scores.get("Neutral", scores.get("neutral", 0))

                finbert_score = positive - negative
                layers["finbert"] = {
                    "score": round(finbert_score, 4),
                    "label": self._score_to_label(finbert_score),
                    "distribution": {
                        "positive": round(positive, 4),
                        "negative": round(negative, 4),
                        "neutral": round(neutral, 4),
                    },
                }
            except Exception as e:
                nlp_logger.warning("FinBERT inference failed: %s", e)
                layers["finbert"] = {"score": 0.0, "label": "neutral", "error": str(e)}

        # Ensemble: weighted average
        ensemble = self._ensemble(layers)
        return {
            "ensemble": ensemble,
            "layers": layers,
            "confidence": self._compute_confidence(layers),
        }

    def _lexicon_score(self, text: str) -> float:
        words = re.findall(r"\b\w+\b", text.lower())
        total = 0.0
        count = 0

        # Check phrases
        text_lower = text.lower()
        all_terms = {**POSITIVE_WORDS, **NEGATIVE_WORDS}
        for phrase, weight in all_terms.items():
            if " " in phrase and phrase in text_lower:
                total += weight
                count += 1

        # Check individual words
        for i, w in enumerate(words):
            if w in POSITIVE_WORDS:
                negated = self._is_negated(words, i)
                total += -POSITIVE_WORDS[w] if negated else POSITIVE_WORDS[w]
                count += 1
            elif w in NEGATIVE_WORDS:
                negated = self._is_negated(words, i)
                total += -NEGATIVE_WORDS[w] if negated else NEGATIVE_WORDS[w]
                count += 1

        if count == 0:
            return 0.0
        return max(-1.0, min(1.0, total / count))

    def _is_negated(self, words: List[str], index: int) -> bool:
        for i in range(max(0, index - 3), index):
            if words[i] in NEGATION:
                return True
        return False

    def _ensemble(self, layers: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Weighted ensemble across available layers.
        FinBERT gets highest weight when available.
        """
        weights = {"lexicon": 0.2, "vader": 0.3, "finbert": 0.5}

        total_score = 0.0
        total_weight = 0.0
        for layer_name, layer_data in layers.items():
            w = weights.get(layer_name, 0.1)
            if "error" in layer_data:
                continue
            total_score += layer_data["score"] * w
            total_weight += w

        if total_weight == 0:
            return {"score": 0.0, "label": "neutral"}

        score = max(-1.0, min(1.0, total_score / total_weight))
        return {"score": round(score, 4), "label": self._score_to_label(score)}

    def _compute_confidence(self, layers: Dict[str, Dict]) -> float:
        """
        Higher confidence when multiple layers agree.
        """
        if len(layers) <= 1:
            return 0.3

        scores = [d["score"] for d in layers.values() if "error" not in d]
        if not scores:
            return 0.1

        agreement = 1.0 - (max(scores) - min(scores)) / 2.0
        layer_bonus = min(1.0, len(layers) / 3.0)
        return round(min(0.95, max(0.1, agreement * layer_bonus)), 4)

    def _score_to_label(self, score: float) -> str:
        if score > 0.15:
            return "positive"
        elif score < -0.15:
            return "negative"
        return "neutral"

    def _compute_aggregate(
        self, articles: List[Dict[str, Any]], symbol: str,
    ) -> Dict[str, Any]:
        if not articles:
            return {
                "symbol": symbol,
                "overall_score": 0.0,
                "overall_label": "neutral",
                "article_count": 0,
            }

        now = datetime.now(timezone.utc)
        scores = []
        pos = neg = neu = 0

        for a in articles:
            s = a.get("nlp_sentiment", {}).get("ensemble", {}).get("score", 0.0)
            label = a.get("nlp_sentiment", {}).get("ensemble", {}).get("label", "neutral")

            if label == "positive":
                pos += 1
            elif label == "negative":
                neg += 1
            else:
                neu += 1

            # Recency weighting
            pub = a.get("published_at")
            if pub:
                if isinstance(pub, str):
                    try:
                        pub = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pub = now
                age_hours = max(0, (now - pub).total_seconds() / 3600)
                weight = max(0.2, 1.0 - (age_hours / 168) * 0.8)
            else:
                weight = 0.5

            scores.append(s * weight)

        overall = sum(scores) / len(scores) if scores else 0.0
        overall = max(-1.0, min(1.0, overall))

        return {
            "symbol": symbol,
            "overall_score": round(overall, 4),
            "overall_label": self._score_to_label(overall),
            "article_count": len(articles),
            "positive_count": pos,
            "negative_count": neg,
            "neutral_count": neu,
            "confidence": round(min(1.0, len(articles) / 10.0), 4),
        }

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "ensemble": {"score": 0.0, "label": "neutral"},
            "layers": {},
            "confidence": 0.0,
        }


# Singleton
nlp_sentiment_analyzer = NLPSentimentAnalyzer()
