"""
WebSocket server implementation for real-time features
"""
import json
import asyncio
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timezone
from uuid import uuid4
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.monitoring import metrics_collector

# Optional redis.asyncio dependency. The pub/sub backplane is only activated
# when this import succeeds AND settings.WEBSOCKET_REDIS_BACKPLANE_ENABLED is
# truthy AND a connection can be established. Any failure leaves the manager
# running in single-instance mode, so the module never crashes on Redis being
# absent.
try:  # pragma: no cover - exercised indirectly by environments with/without redis
    import redis.asyncio as aioredis
    from redis.asyncio import Redis as AsyncRedis

    REDIS_AVAILABLE = True
except Exception:  # ImportError or binary compatibility issues
    aioredis = None  # type: ignore[assignment]
    AsyncRedis = None  # type: ignore[assignment,misc]
    REDIS_AVAILABLE = False

websocket_logger = get_logger("websocket")

# Redis channel used to fan out WebSocket broadcasts across backend replicas.
_WS_BROADCAST_CHANNEL = "ws:broadcast"


class MessageType(Enum):
    """WebSocket message types"""
    # Connection management
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    
    # Authentication
    AUTHENTICATE = "authenticate"
    AUTHENTICATED = "authenticated"
    UNAUTHORIZED = "unauthorized"
    
    # Market data
    MARKET_DATA_SUBSCRIBE = "market_data_subscribe"
    MARKET_DATA_UNSUBSCRIBE = "market_data_unsubscribe"
    MARKET_DATA_UPDATE = "market_data_update"
    
    # Portfolio updates
    PORTFOLIO_SUBSCRIBE = "portfolio_subscribe"
    PORTFOLIO_UNSUBSCRIBE = "portfolio_unsubscribe"
    PORTFOLIO_UPDATE = "portfolio_update"
    
    # Notifications
    NOTIFICATION = "notification"
    ALERT = "alert"
    
    # Collaboration
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    USER_TYPING = "user_typing"
    CHAT_MESSAGE = "chat_message"
    
    # System
    ERROR = "error"
    SUCCESS = "success"


class WebSocketMessage(BaseModel):
    """WebSocket message structure"""
    type: MessageType
    data: Dict[str, Any] = {}
    timestamp: datetime = None
    message_id: str = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now(timezone.utc)
        if 'message_id' not in data:
            data['message_id'] = str(uuid4())
        super().__init__(**data)


class WebSocketConnection:
    """Individual WebSocket connection"""
    
    def __init__(self, websocket: WebSocket, connection_id: str):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id: Optional[str] = None
        self.subscriptions: Set[str] = set()
        self.last_ping: datetime = datetime.now(timezone.utc)
        self.is_authenticated = False
        self.metadata: Dict[str, Any] = {}
    
    async def send_message(self, message: WebSocketMessage):
        """Send message to this connection"""
        try:
            await self.websocket.send_text(message.model_dump_json())
            metrics_collector.increment_counter("websocket_messages_sent")
        except Exception as e:
            websocket_logger.error(f"Failed to send message to {self.connection_id}: {str(e)}")
            raise
    
    async def send_error(self, error_message: str, error_code: str = "GENERAL_ERROR"):
        """Send error message"""
        error_msg = WebSocketMessage(
            type=MessageType.ERROR,
            data={
                "error": error_message,
                "code": error_code
            }
        )
        await self.send_message(error_msg)
    
    async def send_success(self, message: str, data: Dict[str, Any] = None):
        """Send success message"""
        success_msg = WebSocketMessage(
            type=MessageType.SUCCESS,
            data={
                "message": message,
                **(data or {})
            }
        )
        await self.send_message(success_msg)


class WebSocketManager:
    """WebSocket connection manager"""

    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self.subscriptions: Dict[str, Set[str]] = {}  # subscription_key -> connection_ids
        self.rooms: Dict[str, Set[str]] = {}  # room_id -> connection_ids

        # Start background tasks
        self.ping_task = None
        self.cleanup_task = None

        # --- Redis pub/sub backplane (optional, for horizontal scaling) ---
        # When active, broadcast_* methods publish to Redis instead of looping
        # local connections; a background subscriber fans received messages out
        # to the connections living on THIS process.
        self._redis_enabled: bool = False
        self._redis_url: str = ""
        self._publisher: Optional["AsyncRedis"] = None
        self._subscriber_task: Optional[asyncio.Task] = None
        self._stopping: bool = True

    # ------------------------------------------------------------------
    # Backplane configuration / lifecycle
    # ------------------------------------------------------------------
    def configure(self, redis_url: str, enabled: bool) -> None:
        """Configure the Redis pub/sub backplane.

        Safe to call at any time. The backplane only becomes active once
        ``start_redis_backplane`` connects successfully. When ``enabled`` is
        False or the ``redis`` package is missing the manager stays in
        single-instance mode.
        """
        self._redis_url = redis_url or ""
        self._redis_enabled = bool(enabled and REDIS_AVAILABLE)
        if enabled and not REDIS_AVAILABLE:
            websocket_logger.warning(
                "WebSocket Redis backplane requested but the 'redis' package "
                "is not installed; falling back to single-instance mode."
            )

    def _is_backplane_active(self) -> bool:
        """True when broadcasts should be published to Redis."""
        return self._redis_enabled and self._publisher is not None and not self._stopping

    async def start_redis_backplane(self) -> None:
        """Open the publisher connection and start the subscriber loop.

        Failures are logged and swallowed so application startup never crashes
        when Redis is unavailable; the manager simply runs in local mode.
        """
        if not self._redis_enabled:
            return

        self._stopping = False
        try:
            self._publisher = aioredis.from_url(
                self._redis_url, decode_responses=False
            )
            await self._publisher.ping()
            websocket_logger.info(
                "WebSocket Redis backplane publisher connected to %s",
                self._redis_url,
            )
        except Exception as exc:
            websocket_logger.error(
                "WebSocket Redis backplane publisher failed to connect "
                "(falling back to single-instance mode): %s",
                exc,
            )
            await self._close_publisher()
            self._stopping = True
            return

        # Subscriber loop runs independently and reconnects with backoff.
        self._subscriber_task = asyncio.create_task(
            self._subscriber_loop(), name="ws_redis_subscriber"
        )

    async def stop_redis_backplane(self) -> None:
        """Stop the subscriber loop and close Redis connections."""
        self._stopping = True
        task = self._subscriber_task
        self._subscriber_task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        await self._close_publisher()
        websocket_logger.info("WebSocket Redis backplane stopped")

    async def _close_publisher(self) -> None:
        if self._publisher is not None:
            try:
                await self._publisher.aclose()
            except Exception:
                pass
            self._publisher = None

    # ------------------------------------------------------------------
    # Subscriber (receiving cross-instance broadcasts)
    # ------------------------------------------------------------------
    async def _subscriber_loop(self) -> None:
        """Consume broadcast messages from Redis and fan them out locally.

        Reconnects with exponential backoff so a transient Redis outage does
        not permanently disable cross-instance delivery.
        """
        backoff = 1.0
        max_backoff = 30.0
        while not self._stopping:
            sub_redis = None
            pubsub = None
            try:
                sub_redis = aioredis.from_url(self._redis_url, decode_responses=False)
                await sub_redis.ping()
                pubsub = sub_redis.pubsub()
                await pubsub.subscribe(_WS_BROADCAST_CHANNEL)
                backoff = 1.0  # reset after a successful connection
                websocket_logger.info(
                    "WebSocket Redis subscriber connected to channel '%s'",
                    _WS_BROADCAST_CHANNEL,
                )
                async for raw in pubsub.listen():
                    if self._stopping:
                        break
                    if raw.get("type") != "message":
                        continue
                    await self._handle_redis_message(raw.get("data"))
            except asyncio.CancelledError:
                break
            except Exception as exc:
                if not self._stopping:
                    websocket_logger.warning(
                        "WebSocket Redis subscriber error (will retry in "
                        "%.1fs): %s",
                        backoff,
                        exc,
                    )
            finally:
                if pubsub is not None:
                    try:
                        await pubsub.unsubscribe(_WS_BROADCAST_CHANNEL)
                        await pubsub.aclose()
                    except Exception:
                        pass
                if sub_redis is not None:
                    try:
                        await sub_redis.aclose()
                    except Exception:
                        pass

            if self._stopping:
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)

    async def _handle_redis_message(self, raw: Any) -> None:
        """Deserialize a Redis broadcast envelope and fan out locally."""
        try:
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            envelope = json.loads(raw)
            method = envelope.get("method")
            message = WebSocketMessage(**envelope.get("message", {}))
            exclude = envelope.get("exclude_connection")

            if method == "broadcast_to_all":
                await self._local_broadcast_to_all(message, exclude)
            elif method == "broadcast_to_channel":
                await self._local_broadcast_to_channel(
                    envelope.get("channel", ""), message, exclude
                )
            elif method == "broadcast_to_room":
                await self._local_broadcast_to_room(
                    envelope.get("room_id", ""), message, exclude
                )
            elif method == "send_to_user":
                await self._local_send_to_user(envelope.get("user_id", ""), message)
            else:
                websocket_logger.warning(
                    "Unknown WebSocket broadcast method from Redis: %s", method
                )
        except Exception as exc:
            websocket_logger.error("Failed to handle Redis broadcast message: %s", exc)

    # ------------------------------------------------------------------
    # Publisher (sending broadcasts cross-instance)
    # ------------------------------------------------------------------
    async def _publish_broadcast(
        self,
        method: str,
        message: WebSocketMessage,
        *,
        channel: str = None,
        room_id: str = None,
        user_id: str = None,
        exclude_connection: str = None,
    ) -> None:
        """Publish a broadcast envelope to Redis.

        If publishing fails the caller falls back to local fan-out so at least
        the connections on this instance still receive the message.
        """
        envelope: Dict[str, Any] = {
            "method": method,
            "message": message.model_dump(mode="json"),
        }
        if channel is not None:
            envelope["channel"] = channel
        if room_id is not None:
            envelope["room_id"] = room_id
        if user_id is not None:
            envelope["user_id"] = user_id
        if exclude_connection is not None:
            envelope["exclude_connection"] = exclude_connection

        try:
            await self._publisher.publish(
                _WS_BROADCAST_CHANNEL, json.dumps(envelope)
            )
        except Exception as exc:
            websocket_logger.warning(
                "Redis publish failed, falling back to local delivery: %s", exc
            )
            # Drop the stale publisher so _is_backplane_active() returns False
            # and subsequent broadcasts go local until reconnect.
            await self._close_publisher()
            raise
    
    async def connect(self, websocket: WebSocket) -> str:
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        connection_id = str(uuid4())
        connection = WebSocketConnection(websocket, connection_id)
        
        self.connections[connection_id] = connection
        
        # Send connection confirmation
        welcome_msg = WebSocketMessage(
            type=MessageType.CONNECT,
            data={
                "connection_id": connection_id,
                "server_time": datetime.now(timezone.utc).isoformat()
            }
        )
        await connection.send_message(welcome_msg)
        
        websocket_logger.info(f"WebSocket connection established: {connection_id}")
        metrics_collector.increment_counter("websocket_connections_total")
        metrics_collector.set_gauge("websocket_active_connections", len(self.connections))
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        
        # Remove from user connections
        if connection.user_id:
            if connection.user_id in self.user_connections:
                self.user_connections[connection.user_id].discard(connection_id)
                if not self.user_connections[connection.user_id]:
                    del self.user_connections[connection.user_id]
        
        # Remove from subscriptions
        for subscription in connection.subscriptions:
            if subscription in self.subscriptions:
                self.subscriptions[subscription].discard(connection_id)
                if not self.subscriptions[subscription]:
                    del self.subscriptions[subscription]
        
        # Remove from rooms
        for room_id, room_connections in self.rooms.items():
            room_connections.discard(connection_id)
        
        # Remove connection
        del self.connections[connection_id]
        
        websocket_logger.info(f"WebSocket connection closed: {connection_id}")
        metrics_collector.increment_counter("websocket_disconnections_total")
        metrics_collector.set_gauge("websocket_active_connections", len(self.connections))
    
    async def authenticate_connection(self, connection_id: str, user_id: str):
        """Authenticate a WebSocket connection"""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        connection.user_id = user_id
        connection.is_authenticated = True
        
        # Add to user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Send authentication confirmation
        auth_msg = WebSocketMessage(
            type=MessageType.AUTHENTICATED,
            data={"user_id": user_id}
        )
        await connection.send_message(auth_msg)
        
        websocket_logger.info(f"WebSocket connection authenticated: {connection_id} for user {user_id}")
        return True
    
    async def subscribe_to_channel(self, connection_id: str, channel: str):
        """Subscribe connection to a channel"""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        connection.subscriptions.add(channel)
        
        if channel not in self.subscriptions:
            self.subscriptions[channel] = set()
        self.subscriptions[channel].add(connection_id)
        
        websocket_logger.info(f"Connection {connection_id} subscribed to {channel}")
        return True
    
    async def unsubscribe_from_channel(self, connection_id: str, channel: str):
        """Unsubscribe connection from a channel"""
        if connection_id not in self.connections:
            return False
        
        connection = self.connections[connection_id]
        connection.subscriptions.discard(channel)
        
        if channel in self.subscriptions:
            self.subscriptions[channel].discard(connection_id)
            if not self.subscriptions[channel]:
                del self.subscriptions[channel]
        
        websocket_logger.info(f"Connection {connection_id} unsubscribed from {channel}")
        return True
    
    async def join_room(self, connection_id: str, room_id: str):
        """Add connection to a room"""
        if connection_id not in self.connections:
            return False
        
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(connection_id)
        
        # Notify other users in the room
        if len(self.rooms[room_id]) > 1:
            user_joined_msg = WebSocketMessage(
                type=MessageType.USER_JOINED,
                data={
                    "room_id": room_id,
                    "user_id": self.connections[connection_id].user_id,
                    "connection_id": connection_id
                }
            )
            await self.broadcast_to_room(room_id, user_joined_msg, exclude_connection=connection_id)
        
        websocket_logger.info(f"Connection {connection_id} joined room {room_id}")
        return True
    
    async def leave_room(self, connection_id: str, room_id: str):
        """Remove connection from a room"""
        if room_id in self.rooms:
            self.rooms[room_id].discard(connection_id)
            
            # Notify other users in the room
            if self.rooms[room_id] and connection_id in self.connections:
                user_left_msg = WebSocketMessage(
                    type=MessageType.USER_LEFT,
                    data={
                        "room_id": room_id,
                        "user_id": self.connections[connection_id].user_id,
                        "connection_id": connection_id
                    }
                )
                await self.broadcast_to_room(room_id, user_left_msg)
            
            if not self.rooms[room_id]:
                del self.rooms[room_id]
        
        websocket_logger.info(f"Connection {connection_id} left room {room_id}")
        return True
    
    async def send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send message to specific connection"""
        if connection_id in self.connections:
            await self.connections[connection_id].send_message(message)
            return True
        return False
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage):
        """Send message to all connections of a user across all instances."""
        if self._is_backplane_active():
            try:
                await self._publish_broadcast(
                    "send_to_user", message, user_id=user_id
                )
                return True
            except Exception:
                pass  # publish failed -> fall through to local delivery
        return await self._local_send_to_user(user_id, message)

    async def _local_send_to_user(self, user_id: str, message: WebSocketMessage):
        """Send message to all LOCAL connections of a user."""
        if user_id in self.user_connections:
            tasks = []
            for connection_id in self.user_connections[user_id]:
                if connection_id in self.connections:
                    tasks.append(self.connections[connection_id].send_message(message))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                return True
        return False
    
    async def broadcast_to_channel(self, channel: str, message: WebSocketMessage, exclude_connection: str = None):
        """Broadcast message to all subscribers of a channel across all instances."""
        if self._is_backplane_active():
            try:
                await self._publish_broadcast(
                    "broadcast_to_channel",
                    message,
                    channel=channel,
                    exclude_connection=exclude_connection,
                )
                return 1
            except Exception:
                pass  # publish failed -> fall through to local delivery
        return await self._local_broadcast_to_channel(channel, message, exclude_connection)

    async def _local_broadcast_to_channel(self, channel: str, message: WebSocketMessage, exclude_connection: str = None):
        """Broadcast message to LOCAL subscribers of a channel."""
        if channel in self.subscriptions:
            tasks = []
            for connection_id in self.subscriptions[channel]:
                if connection_id != exclude_connection and connection_id in self.connections:
                    tasks.append(self.connections[connection_id].send_message(message))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                return len(tasks)
        return 0
    
    async def broadcast_to_room(self, room_id: str, message: WebSocketMessage, exclude_connection: str = None):
        """Broadcast message to all connections in a room across all instances."""
        if self._is_backplane_active():
            try:
                await self._publish_broadcast(
                    "broadcast_to_room",
                    message,
                    room_id=room_id,
                    exclude_connection=exclude_connection,
                )
                return 1
            except Exception:
                pass  # publish failed -> fall through to local delivery
        return await self._local_broadcast_to_room(room_id, message, exclude_connection)

    async def _local_broadcast_to_room(self, room_id: str, message: WebSocketMessage, exclude_connection: str = None):
        """Broadcast message to LOCAL connections in a room."""
        if room_id in self.rooms:
            tasks = []
            for connection_id in self.rooms[room_id]:
                if connection_id != exclude_connection and connection_id in self.connections:
                    tasks.append(self.connections[connection_id].send_message(message))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                return len(tasks)
        return 0
    
    async def broadcast_to_all(self, message: WebSocketMessage, exclude_connection: str = None):
        """Broadcast message to all connections across all instances."""
        if self._is_backplane_active():
            try:
                await self._publish_broadcast(
                    "broadcast_to_all",
                    message,
                    exclude_connection=exclude_connection,
                )
                return 1
            except Exception:
                pass  # publish failed -> fall through to local delivery
        return await self._local_broadcast_to_all(message, exclude_connection)

    async def _local_broadcast_to_all(self, message: WebSocketMessage, exclude_connection: str = None):
        """Broadcast message to all LOCAL connections."""
        tasks = []
        for connection_id, connection in self.connections.items():
            if connection_id != exclude_connection:
                tasks.append(connection.send_message(message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            return len(tasks)
        return 0
    
    async def handle_message(self, connection_id: str, message_data: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message_data)
            message_type = MessageType(data.get('type'))
            message_data = data.get('data', {})
            
            connection = self.connections.get(connection_id)
            if not connection:
                return
            
            # Handle different message types
            if message_type == MessageType.PING:
                await self._handle_ping(connection)
            elif message_type == MessageType.AUTHENTICATE:
                await self._handle_authenticate(connection, message_data)
            elif message_type == MessageType.MARKET_DATA_SUBSCRIBE:
                await self._handle_market_data_subscribe(connection, message_data)
            elif message_type == MessageType.MARKET_DATA_UNSUBSCRIBE:
                await self._handle_market_data_unsubscribe(connection, message_data)
            elif message_type == MessageType.PORTFOLIO_SUBSCRIBE:
                await self._handle_portfolio_subscribe(connection, message_data)
            elif message_type == MessageType.PORTFOLIO_UNSUBSCRIBE:
                await self._handle_portfolio_unsubscribe(connection, message_data)
            elif message_type == MessageType.CHAT_MESSAGE:
                await self._handle_chat_message(connection, message_data)
            elif message_type == MessageType.USER_TYPING:
                await self._handle_user_typing(connection, message_data)
            else:
                await connection.send_error(f"Unknown message type: {message_type}")
            
            metrics_collector.increment_counter("websocket_messages_received")
            
        except Exception as e:
            websocket_logger.error(f"Error handling WebSocket message: {str(e)}")
            if connection_id in self.connections:
                await self.connections[connection_id].send_error("Invalid message format")
    
    async def _handle_ping(self, connection: WebSocketConnection):
        """Handle ping message"""
        connection.last_ping = datetime.now(timezone.utc)
        pong_msg = WebSocketMessage(type=MessageType.PONG)
        await connection.send_message(pong_msg)
    
    async def _handle_authenticate(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle authentication message"""
        token = data.get('token')
        if not token:
            await connection.send_error("Authentication token required", "AUTH_TOKEN_MISSING")
            return
        
        # TODO: Validate JWT token and get user_id
        # For now, we'll extract user_id from token (implement proper JWT validation)
        try:
            from app.services.auth.jwt_handler import jwt_handler
            payload = jwt_handler.verify_token(token)
            if payload:
                user_id = payload.get('sub')
                await self.authenticate_connection(connection.connection_id, user_id)
            else:
                await connection.send_error("Invalid authentication token", "AUTH_TOKEN_INVALID")
        except Exception as e:
            await connection.send_error("Authentication failed", "AUTH_FAILED")
    
    async def _handle_market_data_subscribe(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle market data subscription"""
        if not connection.is_authenticated:
            await connection.send_error("Authentication required", "AUTH_REQUIRED")
            return
        
        symbols = data.get('symbols', [])
        for symbol in symbols:
            channel = f"market_data:{symbol}"
            await self.subscribe_to_channel(connection.connection_id, channel)
        
        await connection.send_success(f"Subscribed to market data for {len(symbols)} symbols")
    
    async def _handle_market_data_unsubscribe(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle market data unsubscription"""
        symbols = data.get('symbols', [])
        for symbol in symbols:
            channel = f"market_data:{symbol}"
            await self.unsubscribe_from_channel(connection.connection_id, channel)
        
        await connection.send_success(f"Unsubscribed from market data for {len(symbols)} symbols")
    
    async def _handle_portfolio_subscribe(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle portfolio subscription"""
        if not connection.is_authenticated:
            await connection.send_error("Authentication required", "AUTH_REQUIRED")
            return
        
        portfolio_id = data.get('portfolio_id')
        if portfolio_id:
            channel = f"portfolio:{portfolio_id}"
            await self.subscribe_to_channel(connection.connection_id, channel)
            await connection.send_success(f"Subscribed to portfolio {portfolio_id}")
    
    async def _handle_portfolio_unsubscribe(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle portfolio unsubscription"""
        portfolio_id = data.get('portfolio_id')
        if portfolio_id:
            channel = f"portfolio:{portfolio_id}"
            await self.unsubscribe_from_channel(connection.connection_id, channel)
            await connection.send_success(f"Unsubscribed from portfolio {portfolio_id}")
    
    async def _handle_chat_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle chat message"""
        if not connection.is_authenticated:
            await connection.send_error("Authentication required", "AUTH_REQUIRED")
            return
        
        room_id = data.get('room_id')
        message = data.get('message')
        
        if room_id and message:
            chat_msg = WebSocketMessage(
                type=MessageType.CHAT_MESSAGE,
                data={
                    "room_id": room_id,
                    "user_id": connection.user_id,
                    "message": message,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            await self.broadcast_to_room(room_id, chat_msg, exclude_connection=connection.connection_id)
    
    async def _handle_user_typing(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """Handle user typing indicator"""
        if not connection.is_authenticated:
            return
        
        room_id = data.get('room_id')
        is_typing = data.get('is_typing', False)
        
        if room_id:
            typing_msg = WebSocketMessage(
                type=MessageType.USER_TYPING,
                data={
                    "room_id": room_id,
                    "user_id": connection.user_id,
                    "is_typing": is_typing
                }
            )
            await self.broadcast_to_room(room_id, typing_msg, exclude_connection=connection.connection_id)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            "total_connections": len(self.connections),
            "authenticated_connections": len([c for c in self.connections.values() if c.is_authenticated]),
            "total_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
            "active_channels": len(self.subscriptions),
            "active_rooms": len(self.rooms),
            "users_online": len(self.user_connections)
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


# Market data streaming
class MarketDataStreamer:
    """Stream real-time market data to WebSocket clients"""
    
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self.streaming_task = None
    
    async def start_streaming(self):
        """Start market data streaming"""
        self.streaming_task = asyncio.create_task(self._stream_market_data())
    
    async def stop_streaming(self):
        """Stop market data streaming"""
        if self.streaming_task:
            self.streaming_task.cancel()
    
    async def _stream_market_data(self):
        """Stream market data updates"""
        while True:
            try:
                # TODO: Fetch real market data from external API
                # For now, we'll simulate market data updates
                
                # Get all market data subscriptions
                market_channels = [ch for ch in self.ws_manager.subscriptions.keys() 
                                 if ch.startswith('market_data:')]
                
                for channel in market_channels:
                    symbol = channel.split(':')[1]
                    
                    # Simulate market data update
                    market_update = WebSocketMessage(
                        type=MessageType.MARKET_DATA_UPDATE,
                        data={
                            "symbol": symbol,
                            "price": 100.0 + (hash(symbol) % 100),  # Simulated price
                            "change": (hash(symbol) % 10) - 5,  # Simulated change
                            "volume": hash(symbol) % 1000000,  # Simulated volume
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    
                    await self.ws_manager.broadcast_to_channel(channel, market_update)
                
                # Wait before next update
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                websocket_logger.error(f"Error in market data streaming: {str(e)}")
                await asyncio.sleep(1)


# Global market data streamer
market_data_streamer = MarketDataStreamer(websocket_manager)
