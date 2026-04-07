"""
Real-time market data services.
"""
from app.services.market_data.streamer import MarketDataStreamer
from app.services.market_data.subscription_manager import SubscriptionManager
from app.services.market_data.normalizer import normalize_polygon_trade, normalize_polygon_quote, normalize_polygon_aggregate

market_data_streamer = MarketDataStreamer()
subscription_manager = SubscriptionManager()

__all__ = [
    "market_data_streamer",
    "subscription_manager",
    "normalize_polygon_trade",
    "normalize_polygon_quote",
    "normalize_polygon_aggregate",
]
