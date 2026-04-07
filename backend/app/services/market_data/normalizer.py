"""
Market data normalizer for standardizing external data feeds.

Converts Polygon.io trade, quote, and aggregate data into a consistent
internal format used throughout the platform.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from app.core.logging import get_logger

logger = get_logger("app.services.market_data.normalizer")

# Reasonable price bounds for validation
MIN_VALID_PRICE = Decimal("0.001")
MAX_VALID_PRICE = Decimal("999999.9999")
MIN_VALID_VOLUME = 0


def _validate_price(value: Any) -> Optional[Decimal]:
    """Validate and convert a price value to Decimal."""
    if value is None:
        return None
    try:
        price = Decimal(str(value))
        if price < MIN_VALID_PRICE or price > MAX_VALID_PRICE:
            logger.warning(f"Price out of valid range: {price}")
            return None
        return price
    except (ValueError, TypeError):
        return None


def _validate_volume(value: Any) -> int:
    """Validate and convert a volume value to int."""
    if value is None:
        return 0
    try:
        vol = int(value)
        return max(vol, 0)
    except (ValueError, TypeError):
        return 0


def _epoch_ms_to_datetime(epoch_ms: Any) -> Optional[datetime]:
    """Convert epoch milliseconds to UTC datetime."""
    if epoch_ms is None:
        return None
    try:
        return datetime.fromtimestamp(int(epoch_ms) / 1000, tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


def normalize_polygon_trade(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalize a Polygon.io trade event into standard format.

    Args:
        data: Raw Polygon trade data dict with keys like 'sym', 'p', 's', 't', 'x'.

    Returns:
        Normalized market data dict or None if data is invalid.
    """
    try:
        symbol = data.get("sym", "").upper()
        if not symbol:
            return None

        price = _validate_price(data.get("p"))
        if price is None:
            return None

        timestamp = _epoch_ms_to_datetime(data.get("t"))

        return {
            "symbol": symbol,
            "price": price,
            "volume": _validate_volume(data.get("s")),
            "timestamp": timestamp or datetime.now(timezone.utc),
            "bid": None,
            "ask": None,
            "high": None,
            "low": None,
            "open": None,
            "change": None,
            "change_percent": None,
            "source": "polygon_trade",
            "exchange": data.get("x"),
            "trade_id": data.get("i"),
        }
    except Exception as exc:
        logger.error(f"Error normalizing Polygon trade: {exc}")
        return None


def normalize_polygon_quote(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalize a Polygon.io quote event into standard format.

    Args:
        data: Raw Polygon quote data dict with 'sym', 'bp', 'ap', 'bs', 'as', 't'.

    Returns:
        Normalized market data dict or None if data is invalid.
    """
    try:
        symbol = data.get("sym", "").upper()
        if not symbol:
            return None

        bid_price = _validate_price(data.get("bp"))
        ask_price = _validate_price(data.get("ap"))
        timestamp = _epoch_ms_to_datetime(data.get("t"))

        # Mid-price as the primary price
        mid_price = None
        if bid_price and ask_price:
            mid_price = (bid_price + ask_price) / 2
        elif bid_price:
            mid_price = bid_price
        elif ask_price:
            mid_price = ask_price

        return {
            "symbol": symbol,
            "price": mid_price,
            "volume": 0,
            "timestamp": timestamp or datetime.now(timezone.utc),
            "bid": bid_price,
            "ask": ask_price,
            "bid_size": _validate_volume(data.get("bs")),
            "ask_size": _validate_volume(data.get("as")),
            "high": None,
            "low": None,
            "open": None,
            "change": None,
            "change_percent": None,
            "source": "polygon_quote",
        }
    except Exception as exc:
        logger.error(f"Error normalizing Polygon quote: {exc}")
        return None


def normalize_polygon_aggregate(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalize a Polygon.io aggregate (bar) event into standard format.

    Args:
        data: Raw Polygon aggregate data dict with 'sym', 'o', 'h', 'l', 'c', 'v', 's', 'e'.

    Returns:
        Normalized market data dict or None if data is invalid.
    """
    try:
        symbol = data.get("sym", "").upper()
        if not symbol:
            return None

        open_price = _validate_price(data.get("o"))
        high_price = _validate_price(data.get("h"))
        low_price = _validate_price(data.get("l"))
        close_price = _validate_price(data.get("c"))

        if close_price is None:
            return None

        # Start timestamp from the aggregate
        start_ts = _epoch_ms_to_datetime(data.get("s"))
        end_ts = _epoch_ms_to_datetime(data.get("e"))
        timestamp = end_ts or start_ts or datetime.now(timezone.utc)

        # Calculate change from open to close
        change = None
        change_percent = None
        if open_price and close_price and open_price > 0:
            change = close_price - open_price
            change_percent = (change / open_price) * 100

        return {
            "symbol": symbol,
            "price": close_price,
            "volume": _validate_volume(data.get("v")),
            "timestamp": timestamp,
            "bid": None,
            "ask": None,
            "high": high_price,
            "low": low_price,
            "open": open_price,
            "change": change,
            "change_percent": change_percent,
            "source": "polygon_aggregate",
        }
    except Exception as exc:
        logger.error(f"Error normalizing Polygon aggregate: {exc}")
        return None
