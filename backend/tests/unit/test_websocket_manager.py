"""
Tests for app.core.websocket.WebSocketManager / WebSocketConnection.

Uses a stubbed WebSocket-like object (no real network).
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.websocket import (
    MessageType,
    WebSocketConnection,
    WebSocketManager,
    WebSocketMessage,
)


class FakeWebSocket:
    """Stand-in for fastapi.WebSocket — captures sent messages."""

    def __init__(self):
        self.sent: list[str] = []
        self.closed = False

    async def accept(self):
        pass

    async def send_text(self, text: str):
        self.sent.append(text)

    async def close(self, code: int = 1000):
        self.closed = True


@pytest.fixture
def manager() -> WebSocketManager:
    return WebSocketManager()


@pytest.fixture
def fake_ws() -> FakeWebSocket:
    return FakeWebSocket()


# ---------------------------------------------------------------------------
# WebSocketMessage / WebSocketConnection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMessage:
    def test_message_auto_assigns_id_and_timestamp(self):
        msg = WebSocketMessage(type=MessageType.PING)
        assert msg.message_id is not None
        assert msg.timestamp is not None

    def test_message_serialises(self):
        msg = WebSocketMessage(type=MessageType.NOTIFICATION, data={"x": 1})
        # Pydantic v2: model_dump_json() or .json()
        text = msg.model_dump_json()
        parsed = json.loads(text)
        assert parsed["type"] == "notification"
        assert parsed["data"]["x"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestWebSocketConnection:
    async def test_send_message_writes_text(self, fake_ws):
        conn = WebSocketConnection(fake_ws, "c1")
        msg = WebSocketMessage(type=MessageType.PING)
        await conn.send_message(msg)
        assert len(fake_ws.sent) == 1
        parsed = json.loads(fake_ws.sent[0])
        assert parsed["type"] == "ping"

    async def test_send_error(self, fake_ws):
        conn = WebSocketConnection(fake_ws, "c1")
        await conn.send_error("oops", error_code="BAD")
        parsed = json.loads(fake_ws.sent[0])
        assert parsed["type"] == "error"
        assert parsed["data"]["error"] == "oops"
        assert parsed["data"]["code"] == "BAD"

    async def test_send_success(self, fake_ws):
        conn = WebSocketConnection(fake_ws, "c1")
        await conn.send_success("done", data={"id": 42})
        parsed = json.loads(fake_ws.sent[0])
        assert parsed["type"] == "success"
        assert parsed["data"]["message"] == "done"
        assert parsed["data"]["id"] == 42


# ---------------------------------------------------------------------------
# WebSocketManager — lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestManagerLifecycle:
    async def test_connect_assigns_id_and_sends_welcome(self, manager, fake_ws):
        conn_id = await manager.connect(fake_ws)
        assert conn_id in manager.connections
        # Welcome message was sent
        assert len(fake_ws.sent) == 1
        parsed = json.loads(fake_ws.sent[0])
        assert parsed["type"] == "connect"
        assert parsed["data"]["connection_id"] == conn_id

    async def test_disconnect_removes_connection(self, manager, fake_ws):
        conn_id = await manager.connect(fake_ws)
        await manager.disconnect(conn_id)
        assert conn_id not in manager.connections

    async def test_disconnect_unknown_is_noop(self, manager):
        await manager.disconnect("no-such-id")  # Should not raise

    async def test_authenticate_connection(self, manager, fake_ws):
        conn_id = await manager.connect(fake_ws)
        ok = await manager.authenticate_connection(conn_id, user_id="alice")
        assert ok is True
        assert manager.connections[conn_id].is_authenticated is True
        assert "alice" in manager.user_connections
        # Authenticated message was sent
        assert any(json.loads(s)["type"] == "authenticated" for s in fake_ws.sent)

    async def test_authenticate_unknown_connection(self, manager):
        ok = await manager.authenticate_connection("nope", "alice")
        assert ok is False

    async def test_disconnect_cleans_up_user_connections(self, manager, fake_ws):
        conn_id = await manager.connect(fake_ws)
        await manager.authenticate_connection(conn_id, "alice")
        await manager.disconnect(conn_id)
        # User connections cleaned up
        assert "alice" not in manager.user_connections


# ---------------------------------------------------------------------------
# Subscription & rooms
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestSubscriptions:
    async def test_subscribe_and_unsubscribe(self, manager, fake_ws):
        conn_id = await manager.connect(fake_ws)
        ok = await manager.subscribe_to_channel(conn_id, "market_data:AAPL")
        assert ok is True
        assert "market_data:AAPL" in manager.subscriptions
        ok = await manager.unsubscribe_from_channel(conn_id, "market_data:AAPL")
        assert ok is True
        # Channel removed entirely (no subscribers)
        assert "market_data:AAPL" not in manager.subscriptions

    async def test_subscribe_unknown_connection(self, manager):
        ok = await manager.subscribe_to_channel("nope", "any")
        assert ok is False

    async def test_broadcast_to_channel(self, manager):
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        c1 = await manager.connect(ws1)
        c2 = await manager.connect(ws2)
        await manager.subscribe_to_channel(c1, "market_data:AAPL")
        await manager.subscribe_to_channel(c2, "market_data:AAPL")
        msg = WebSocketMessage(type=MessageType.MARKET_DATA_UPDATE, data={"price": 175.5})
        count = await manager.broadcast_to_channel("market_data:AAPL", msg)
        assert count == 2

    async def test_broadcast_to_channel_with_exclude(self, manager):
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        c1 = await manager.connect(ws1)
        c2 = await manager.connect(ws2)
        await manager.subscribe_to_channel(c1, "x")
        await manager.subscribe_to_channel(c2, "x")
        msg = WebSocketMessage(type=MessageType.NOTIFICATION)
        count = await manager.broadcast_to_channel("x", msg, exclude_connection=c1)
        assert count == 1

    async def test_broadcast_to_unknown_channel(self, manager):
        msg = WebSocketMessage(type=MessageType.NOTIFICATION)
        count = await manager.broadcast_to_channel("nobody-here", msg)
        assert count == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestRooms:
    async def test_join_and_leave_room(self, manager, fake_ws):
        conn_id = await manager.connect(fake_ws)
        assert await manager.join_room(conn_id, "room1") is True
        assert conn_id in manager.rooms["room1"]
        assert await manager.leave_room(conn_id, "room1") is True
        assert "room1" not in manager.rooms

    async def test_join_room_notifies_existing_members(self, manager):
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        c1 = await manager.connect(ws1)
        c2 = await manager.connect(ws2)
        await manager.authenticate_connection(c1, "alice")
        await manager.authenticate_connection(c2, "bob")
        await manager.join_room(c1, "chatroom")
        ws1.sent.clear()
        await manager.join_room(c2, "chatroom")
        # ws1 should have received a user_joined notification
        types = [json.loads(s)["type"] for s in ws1.sent]
        assert "user_joined" in types


# ---------------------------------------------------------------------------
# Directed messaging
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestDirectedMessaging:
    async def test_send_to_connection(self, manager, fake_ws):
        conn_id = await manager.connect(fake_ws)
        fake_ws.sent.clear()
        msg = WebSocketMessage(type=MessageType.PONG)
        ok = await manager.send_to_connection(conn_id, msg)
        assert ok is True
        assert any(json.loads(s)["type"] == "pong" for s in fake_ws.sent)

    async def test_send_to_unknown_connection(self, manager):
        msg = WebSocketMessage(type=MessageType.PONG)
        ok = await manager.send_to_connection("no-such", msg)
        assert ok is False

    async def test_send_to_user(self, manager):
        ws1 = FakeWebSocket()
        c1 = await manager.connect(ws1)
        await manager.authenticate_connection(c1, "alice")
        ws1.sent.clear()
        msg = WebSocketMessage(type=MessageType.NOTIFICATION, data={"x": 1})
        ok = await manager.send_to_user("alice", msg)
        assert ok is True
        assert any(json.loads(s)["type"] == "notification" for s in ws1.sent)

    async def test_send_to_user_unknown(self, manager):
        msg = WebSocketMessage(type=MessageType.NOTIFICATION)
        assert await manager.send_to_user("nobody", msg) is False

    async def test_broadcast_to_all(self, manager):
        wss = [FakeWebSocket() for _ in range(3)]
        for ws in wss:
            await manager.connect(ws)
        for ws in wss:
            ws.sent.clear()
        msg = WebSocketMessage(type=MessageType.NOTIFICATION, data={"sys": True})
        count = await manager.broadcast_to_all(msg)
        assert count == 3


# ---------------------------------------------------------------------------
# Message handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestHandleMessage:
    async def test_ping_results_in_pong(self, manager, fake_ws):
        conn_id = await manager.connect(fake_ws)
        fake_ws.sent.clear()
        await manager.handle_message(conn_id, json.dumps({"type": "ping"}))
        types = [json.loads(s)["type"] for s in fake_ws.sent]
        assert "pong" in types

    async def test_market_data_subscribe_requires_auth(self, manager, fake_ws):
        # Without auth, _handle_market_data_subscribe sends an AUTH_REQUIRED error
        conn_id = await manager.connect(fake_ws)
        fake_ws.sent.clear()
        await manager.handle_message(
            conn_id,
            json.dumps({"type": "market_data_subscribe", "data": {"symbols": ["AAPL"]}}),
        )
        types = [json.loads(s)["type"] for s in fake_ws.sent]
        assert "error" in types

    async def test_market_data_subscribe_authenticated(self, manager, fake_ws):
        conn_id = await manager.connect(fake_ws)
        await manager.authenticate_connection(conn_id, "alice")
        await manager.handle_message(
            conn_id,
            json.dumps({"type": "market_data_subscribe", "data": {"symbols": ["AAPL"]}}),
        )
        assert any("market_data" in s for s in manager.subscriptions)

    async def test_invalid_json_sends_error(self, manager, fake_ws):
        conn_id = await manager.connect(fake_ws)
        fake_ws.sent.clear()
        await manager.handle_message(conn_id, "not valid json {{{")
        types = [json.loads(s)["type"] for s in fake_ws.sent]
        assert "error" in types


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestStats:
    async def test_get_connection_stats(self, manager, fake_ws):
        await manager.connect(fake_ws)
        stats = manager.get_connection_stats()
        assert stats["total_connections"] >= 1
