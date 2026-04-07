"""
Real-time market data streamer using Polygon.io WebSocket API.

Connects to the Polygon.io Stocks WebSocket feed, authenticates,
subscribes to trade/quote/aggregate channels, and distributes
normalized data through asyncio queues.
"""
import asyncio
import json
import time
from typing import Any, Callable, Dict, List, Optional

import aiohttp

from app.core.config import settings
from app.core.logging import get_logger
from app.services.market_data.normalizer import (
    normalize_polygon_aggregate,
    normalize_polygon_quote,
    normalize_polygon_trade,
)

logger = get_logger("app.services.market_data.streamer")

# Reconnection settings
INITIAL_RECONNECT_DELAY = 1.0
MAX_RECONNECT_DELAY = 60.0
MAX_RECONNECT_ATTEMPTS = 50


class MarketDataStreamer:
    """
    WebSocket client for real-time market data from Polygon.io.

    Handles connection lifecycle, authentication, subscription management,
    data normalization, and distribution via asyncio queues.
    """

    def __init__(self) -> None:
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._connected = False
        self._running = False
        self._reconnect_attempts = 0
        self._reconnect_delay = INITIAL_RECONNECT_DELAY

        # Symbols we're subscribed to on the Polygon connection
        self._polygon_subscriptions: set = set()

        # Callback for distributing normalized data
        self._on_data: Optional[Callable] = None

        # Background tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def subscribed_symbols(self) -> List[str]:
        return sorted(self._polygon_subscriptions)

    def set_data_callback(self, callback: Callable) -> None:
        """Set the callback invoked when normalized market data arrives."""
        self._on_data = callback

    async def start(self) -> None:
        """Start the streamer with automatic reconnection."""
        if self._running:
            logger.warning("Streamer is already running")
            return

        self._running = True
        logger.info("Starting market data streamer")

        while self._running:
            try:
                await self._connect()
                await self._authenticate()
                await self._resubscribe()
                self._reconnect_attempts = 0
                self._reconnect_delay = INITIAL_RECONNECT_DELAY

                # Start heartbeat
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                # Receive loop (blocks until disconnect)
                await self._receive_loop()

            except asyncio.CancelledError:
                logger.info("Streamer task cancelled")
                break
            except Exception as exc:
                self._connected = False
                self._reconnect_attempts += 1
                logger.error(
                    f"Market data streamer error (attempt {self._reconnect_attempts}): {exc}"
                )

                if self._reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                    logger.error("Max reconnect attempts reached, stopping streamer")
                    break

                # Exponential backoff with jitter
                delay = min(
                    self._reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
                    MAX_RECONNECT_DELAY,
                )
                jitter = delay * 0.1 * (time.time() % 1)
                total_delay = delay + jitter

                logger.info(f"Reconnecting in {total_delay:.1f} seconds...")
                await asyncio.sleep(total_delay)
            finally:
                await self._cleanup_connection()

        self._running = False
        logger.info("Market data streamer stopped")

    async def stop(self) -> None:
        """Gracefully stop the streamer."""
        logger.info("Stopping market data streamer")
        self._running = False
        await self._cleanup_connection()

    async def subscribe_symbols(self, symbols: List[str]) -> None:
        """
        Subscribe to real-time data for the given symbols.

        Args:
            symbols: List of ticker symbols to subscribe to.
        """
        if not self._connected or not self._ws:
            logger.warning("Cannot subscribe: not connected to Polygon")
            # Queue for subscription on reconnect
            self._polygon_subscriptions.update(s.upper() for s in symbols)
            return

        new_symbols = [s.upper() for s in symbols if s.upper() not in self._polygon_subscriptions]
        if not new_symbols:
            return

        # Subscribe to trades, quotes, and aggregates
        msg = {
            "action": "subscribe",
            "params": ",".join(
                [f"T.{s}" for s in new_symbols]   # trades
                + [f"Q.{s}" for s in new_symbols]  # quotes
                + [f"A.{s}" for s in new_symbols]  # aggregates
            ),
        }

        await self._ws.send_str(json.dumps(msg))
        self._polygon_subscriptions.update(new_symbols)
        logger.info(f"Subscribed to Polygon for {len(new_symbols)} symbols: {new_symbols}")

    async def unsubscribe_symbols(self, symbols: List[str]) -> None:
        """Unsubscribe from real-time data for the given symbols."""
        if not self._connected or not self._ws:
            self._polygon_subscriptions.difference_update(s.upper() for s in symbols)
            return

        removed = [s.upper() for s in symbols if s.upper() in self._polygon_subscriptions]
        if not removed:
            return

        msg = {
            "action": "unsubscribe",
            "params": ",".join(
                [f"T.{s}" for s in removed]
                + [f"Q.{s}" for s in removed]
                + [f"A.{s}" for s in removed]
            ),
        }

        await self._ws.send_str(json.dumps(msg))
        self._polygon_subscriptions.difference_update(removed)
        logger.info(f"Unsubscribed from Polygon for {len(removed)} symbols: {removed}")

    # ------------------------------------------------------------------ #
    #  Internal methods                                                   #
    # ------------------------------------------------------------------ #

    async def _connect(self) -> None:
        """Establish WebSocket connection to Polygon.io."""
        url = getattr(settings, "POLYGON_WEBSOCKET_URL", "wss://socket.polygon.io/stocks")

        self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(
            url,
            heartbeat=30,
            receive_timeout=60,
        )
        self._connected = True
        logger.info(f"Connected to Polygon WebSocket at {url}")

    async def _authenticate(self) -> None:
        """Send authentication message with API key."""
        api_key = getattr(settings, "POLYGON_API_KEY", None)
        if not api_key:
            logger.warning("No POLYGON_API_KEY configured, skipping authentication")
            return

        msg = {"action": "auth", "params": api_key}
        await self._ws.send_str(json.dumps(msg))

        # Wait for auth response
        raw = await asyncio.wait_for(self._ws.receive(), timeout=10)
        if raw.type == aiohttp.WSMsgType.TEXT:
            response = json.loads(raw.data)
            if isinstance(response, list):
                response = response[0]
            status = response.get("status", "")
            if status == "auth_success" or response.get("ev") == "status":
                logger.info("Polygon WebSocket authenticated successfully")
            else:
                logger.warning(f"Polygon auth response: {response}")
        elif raw.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
            raise ConnectionError("Connection closed during authentication")

    async def _resubscribe(self) -> None:
        """Re-subscribe to previously subscribed symbols after reconnect."""
        if self._polygon_subscriptions:
            symbols = list(self._polygon_subscriptions)
            self._polygon_subscriptions.clear()
            await self.subscribe_symbols(symbols)

    async def _receive_loop(self) -> None:
        """Main receive loop that processes incoming WebSocket messages."""
        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self._process_message(msg.data)
            elif msg.type == aiohttp.WSMsgType.PING:
                await self._ws.pong()
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                logger.warning("WebSocket connection closed or error")
                break

    async def _process_message(self, raw_data: str) -> None:
        """Process a raw WebSocket message from Polygon."""
        try:
            messages = json.loads(raw_data)
            if not isinstance(messages, list):
                messages = [messages]

            for msg in messages:
                event_type = msg.get("ev")

                normalized = None
                if event_type == "T":
                    normalized = normalize_polygon_trade(msg)
                elif event_type == "Q":
                    normalized = normalize_polygon_quote(msg)
                elif event_type == "A" or event_type == "AM":
                    normalized = normalize_polygon_aggregate(msg)
                elif event_type == "status":
                    logger.debug(f"Polygon status: {msg.get('message', '')}")
                    continue
                else:
                    continue

                if normalized and self._on_data:
                    await self._on_data(normalized)

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from Polygon: {raw_data[:200]}")
        except Exception as exc:
            logger.error(f"Error processing Polygon message: {exc}")

    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat to detect stale connections."""
        while self._connected and self._running:
            await asyncio.sleep(30)
            if self._ws and not self._ws.closed:
                try:
                    await self._ws.ping()
                except Exception:
                    logger.warning("Heartbeat ping failed")
                    break

    async def _cleanup_connection(self) -> None:
        """Clean up WebSocket connection resources."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        self._connected = False

        if self._ws and not self._ws.closed:
            await self._ws.close()

        if self._session and not self._session.closed:
            await self._session.close()

        self._ws = None
        self._session = None

    def get_status(self) -> Dict[str, Any]:
        """Get current streamer status."""
        return {
            "connected": self._connected,
            "running": self._running,
            "reconnect_attempts": self._reconnect_attempts,
            "subscribed_symbols": len(self._polygon_subscriptions),
            "symbols": sorted(self._polygon_subscriptions)[:50],
        }
