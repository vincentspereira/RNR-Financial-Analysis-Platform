"""
Subscription manager for real-time market data distribution.

Manages per-user symbol subscriptions and distributes market data
updates to the appropriate WebSocket connections.
"""
import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.logging import get_logger

logger = get_logger("app.services.market_data.subscription_manager")


class SubscriptionManager:
    """
    Manages market data subscriptions and distribution.

    Tracks which symbols each user is subscribed to and which
    WebSocket connections belong to each user. When market data
    arrives, it distributes updates only to subscribed users.
    """

    def __init__(self) -> None:
        # user_id -> set of subscribed symbols
        self._user_subscriptions: Dict[str, Set[str]] = defaultdict(set)

        # symbol -> set of user_ids subscribed
        self._symbol_subscribers: Dict[str, Set[str]] = defaultdict(set)

        # user_id -> list of asyncio.Queue for pushing data
        self._user_queues: Dict[str, List[asyncio.Queue]] = defaultdict(list)

        # connection_id -> (user_id, asyncio.Queue)
        self._connections: Dict[str, Tuple[str, asyncio.Queue]] = {}

        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        user_id: str,
        connection_id: str,
        symbols: List[str],
    ) -> List[str]:
        """
        Subscribe a user's connection to the given symbols.

        Args:
            user_id: The authenticated user's ID.
            connection_id: Unique identifier for the WebSocket connection.
            symbols: List of ticker symbols to subscribe to.

        Returns:
            List of newly subscribed symbols.
        """
        normalized = {s.upper() for s in symbols}
        async with self._lock:
            new_symbols = normalized - self._user_subscriptions[user_id]

            self._user_subscriptions[user_id].update(normalized)
            for symbol in normalized:
                self._symbol_subscribers[symbol].add(user_id)

            logger.info(
                f"User {user_id} subscribed to {len(new_symbols)} new symbols "
                f"via connection {connection_id} (total: {len(self._user_subscriptions[user_id])})"
            )
            return list(new_symbols)

    async def unsubscribe(
        self,
        user_id: str,
        symbols: List[str],
    ) -> List[str]:
        """
        Unsubscribe a user from the given symbols.

        Args:
            user_id: The authenticated user's ID.
            symbols: List of ticker symbols to unsubscribe from.

        Returns:
            List of unsubscribed symbols.
        """
        normalized = {s.upper() for s in symbols}
        async with self._lock:
            removed = []
            for symbol in normalized:
                self._user_subscriptions[user_id].discard(symbol)
                self._symbol_subscribers[symbol].discard(user_id)
                removed.append(symbol)

                # Clean up empty subscriber sets
                if not self._symbol_subscribers[symbol]:
                    del self._symbol_subscribers[symbol]

            logger.info(
                f"User {user_id} unsubscribed from {len(removed)} symbols "
                f"(remaining: {len(self._user_subscriptions[user_id])})"
            )
            return removed

    async def register_connection(
        self,
        user_id: str,
        connection_id: str,
    ) -> asyncio.Queue:
        """
        Register a new WebSocket connection for a user.

        Args:
            user_id: The authenticated user's ID.
            connection_id: Unique identifier for the connection.

        Returns:
            asyncio.Queue that will receive market data updates.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._user_queues[user_id].append(queue)
            self._connections[connection_id] = (user_id, queue)

        logger.info(f"Registered connection {connection_id} for user {user_id}")
        return queue

    async def unregister_connection(self, connection_id: str) -> None:
        """
        Unregister a WebSocket connection and clean up subscriptions.

        Args:
            connection_id: The connection to remove.
        """
        async with self._lock:
            entry = self._connections.pop(connection_id, None)
            if not entry:
                return

            user_id, queue = entry

            # Remove queue from user's queue list
            if user_id in self._user_queues:
                try:
                    self._user_queues[user_id].remove(queue)
                except ValueError:
                    pass
                if not self._user_queues[user_id]:
                    del self._user_queues[user_id]

            logger.info(f"Unregistered connection {connection_id} for user {user_id}")

    async def distribute(self, symbol: str, data: Dict[str, Any]) -> int:
        """
        Distribute market data for a symbol to all subscribed users.

        Args:
            symbol: The ticker symbol this data is for.
            data: The normalized market data payload.

        Returns:
            Number of users that received the update.
        """
        symbol_upper = symbol.upper()
        subscriber_ids = self._symbol_subscribers.get(symbol_upper, set())

        if not subscriber_ids:
            return 0

        message = {
            "type": "market_data_update",
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        delivered = 0
        for user_id in subscriber_ids:
            queues = self._user_queues.get(user_id, [])
            for queue in queues:
                try:
                    queue.put_nowait(message)
                    delivered += 1
                except asyncio.QueueFull:
                    # Drop oldest and try again
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    try:
                        queue.put_nowait(message)
                        delivered += 1
                    except asyncio.QueueFull:
                        logger.warning(
                            f"Queue full for user {user_id}, dropping market data for {symbol}"
                        )

        return delivered

    def get_user_subscriptions(self, user_id: str) -> List[str]:
        """Get the list of symbols a user is subscribed to."""
        return sorted(self._user_subscriptions.get(user_id, set()))

    def get_symbol_subscriber_count(self, symbol: str) -> int:
        """Get the number of users subscribed to a symbol."""
        return len(self._symbol_subscribers.get(symbol.upper(), set()))

    def get_all_subscribed_symbols(self) -> List[str]:
        """Get all symbols that have at least one subscriber."""
        return sorted(self._symbol_subscribers.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get subscription statistics."""
        return {
            "total_subscribed_symbols": len(self._symbol_subscribers),
            "total_subscribed_users": len(self._user_subscriptions),
            "total_active_connections": len(self._connections),
            "top_symbols": sorted(
                [(s, len(u)) for s, u in self._symbol_subscribers.items()],
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        }
