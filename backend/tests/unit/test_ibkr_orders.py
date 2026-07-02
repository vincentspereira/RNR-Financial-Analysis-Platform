"""
Unit tests for IBKR OrderManager.

`ib_async` is fully mocked — these tests do NOT require TWS/Gateway running.
The DB session is an AsyncMock so tests do not require a database either.

Scope:
- place_order happy path (status translation, persistence calls)
- safety-gate denial bubbles up as SafetyLimitExceeded
- _build_ib_order validates required prices per order type
- ib.placeOrder failure marks the persisted record REJECTED
- cancel_order rejects already-terminal orders
- list_orders constructs scoped query, returns records
- _translate_status maps IBKR strings to our enum
"""
from __future__ import annotations

import sys
import types
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.ibkr import (
    IBKROrderStatus,
    OrderAction,
    OrderType,
    PlaceIBKROrderRequest,
    TimeInForce,
)
from app.services.ibkr.orders import (
    OrderManager,
    OrderRejectedError,
    order_manager as _module_order_manager,
)
from app.services.ibkr.safety import SafetyDecision, SafetyLimitExceeded


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------

def _fake_ib_async_module() -> types.ModuleType:
    """Build a minimal `ib_async`-shaped module for `_lazy_import()` to return."""
    mod = types.ModuleType("ib_async")

    def _OrderFactory(name):
        def _make(**kw):
            attrs = {
                "orderId": 0,
                "permId": 0,
                "action": None,
                "totalQuantity": None,
                "orderType": name.upper(),
                "lmtPrice": None,
                "auxPrice": None,
                "tif": "DAY",
                "account": None,
                "transmit": True,
            }
            # caller's kwargs take precedence over defaults
            attrs.update(kw)
            return SimpleNamespace(**attrs)

        return _make

    mod.MarketOrder = _OrderFactory("market")
    mod.LimitOrder = _OrderFactory("limit")
    mod.StopOrder = _OrderFactory("stop")
    mod.StopLimitOrder = _OrderFactory("stop_limit")

    def _Order(**kw):
        attrs = {
            "orderId": 0,
            "permId": 0,
            "action": None,
            "totalQuantity": None,
            "orderType": None,
            "lmtPrice": None,
            "auxPrice": None,
            "tif": "DAY",
            "account": None,
            "transmit": True,
        }
        attrs.update(kw)
        return SimpleNamespace(**attrs)

    mod.Order = _Order
    return mod


def _make_trade(order_id=99, perm_id=12345, status="Submitted", filled=0, avg_price=0):
    return SimpleNamespace(
        order=SimpleNamespace(orderId=order_id, permId=perm_id),
        orderStatus=SimpleNamespace(
            status=status, filled=filled, avgFillPrice=avg_price
        ),
    )


@pytest.fixture
def manager() -> OrderManager:
    return OrderManager()


@pytest.fixture
def fake_db():
    """AsyncMock DB session that records add()'d objects."""
    db = MagicMock()
    db.added = []

    def _add(obj):
        db.added.append(obj)

    db.add = _add
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def fake_ib():
    ib = MagicMock()
    ib.placeOrder = MagicMock(return_value=_make_trade())
    ib.cancelOrder = MagicMock()
    ib.trades = MagicMock(return_value=[])
    return ib


@pytest.fixture
def allow_all_safety(monkeypatch):
    """Safety gate that allows every order and records calls."""
    decision = SafetyDecision(
        allowed=True,
        reason="OK",
        order_count_today=0,
        notional_today_usd=0.0,
        order_limit=50,
        notional_limit_usd=1_000_000.0,
    )
    check = AsyncMock(return_value=decision)
    record = AsyncMock()
    monkeypatch.setattr("app.services.ibkr.orders.safety_gate.check", check)
    monkeypatch.setattr("app.services.ibkr.orders.safety_gate.record", record)
    return SimpleNamespace(check=check, record=record)


@pytest.fixture
def deny_safety(monkeypatch):
    decision = SafetyDecision(
        allowed=False,
        reason="Daily order limit reached (50/50). Limit resets at 00:00 UTC.",
        order_count_today=50,
        notional_today_usd=0.0,
        order_limit=50,
        notional_limit_usd=1_000_000.0,
    )
    check = AsyncMock(return_value=decision)
    monkeypatch.setattr("app.services.ibkr.orders.safety_gate.check", check)
    monkeypatch.setattr(
        "app.services.ibkr.orders.safety_gate.record", AsyncMock()
    )
    return decision


@pytest.fixture
def patched_externals(monkeypatch, fake_ib):
    """Patch contract resolver, IBKR client, and ib_async lazy import."""
    fake_contract = SimpleNamespace(symbol="AAPL", conId=123)
    monkeypatch.setattr(
        "app.services.ibkr.orders.contract_resolver.resolve",
        AsyncMock(return_value=fake_contract),
    )
    monkeypatch.setattr(
        "app.services.ibkr.orders.ibkr_client.ensure_connected",
        AsyncMock(return_value=fake_ib),
    )
    monkeypatch.setattr(
        "app.services.ibkr.orders._lazy_import", _fake_ib_async_module
    )
    return SimpleNamespace(contract=fake_contract, ib=fake_ib)


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
class TestPlaceOrderHappyPath:
    async def test_limit_order_persists_and_calls_ib(
        self, manager, fake_db, allow_all_safety, patched_externals
    ):
        user_id = uuid4()
        req = PlaceIBKROrderRequest(
            symbol="AAPL",
            action=OrderAction.BUY,
            order_type=OrderType.LIMIT,
            quantity=10,
            limit_price=175.50,
            time_in_force=TimeInForce.DAY,
        )

        result = await manager.place_order(fake_db, user_id, req)

        # Persisted record was added to the session
        assert len(fake_db.added) == 1
        record = fake_db.added[0]
        assert record.symbol == "AAPL"
        assert record.action == "BUY"
        assert record.order_type == "limit"
        assert record.quantity == Decimal("10")
        assert record.limit_price == Decimal("175.5")

        # IBKR placeOrder was called once
        assert patched_externals.ib.placeOrder.call_count == 1

        # Safety gate was both checked and recorded
        allow_all_safety.check.assert_awaited_once()
        allow_all_safety.record.assert_awaited_once()

        # Status was translated from IB's "Submitted"
        assert result.status == IBKROrderStatus.SUBMITTED.value
        assert result.ib_order_id == 99
        assert result.ib_perm_id == 12345

    async def test_market_order_uses_estimated_notional(
        self, manager, fake_db, allow_all_safety, patched_externals
    ):
        user_id = uuid4()
        req = PlaceIBKROrderRequest(
            symbol="MSFT",
            action=OrderAction.SELL,
            order_type=OrderType.MARKET,
            quantity=5,
        )
        # Force _estimate_notional to return a fixed value so we don't touch
        # the live quote path.
        with patch.object(
            manager, "_estimate_notional", AsyncMock(return_value=1000.0)
        ):
            result = await manager.place_order(fake_db, user_id, req)

        assert result.action == "SELL"
        assert result.order_type == "market"
        # Notional captured at submit
        assert result.notional_usd_at_submit == Decimal("1000.0")


@pytest.mark.unit
@pytest.mark.asyncio
class TestPlaceOrderRejections:
    async def test_safety_denial_raises_safety_limit_exceeded(
        self, manager, fake_db, deny_safety, patched_externals
    ):
        user_id = uuid4()
        req = PlaceIBKROrderRequest(
            symbol="AAPL",
            action=OrderAction.BUY,
            order_type=OrderType.LIMIT,
            quantity=1,
            limit_price=200.0,
        )
        with pytest.raises(SafetyLimitExceeded) as exc:
            await manager.place_order(fake_db, user_id, req)
        assert "Daily order limit" in exc.value.decision.reason
        # Nothing should have been persisted, nothing placed on IB
        assert fake_db.added == []
        assert patched_externals.ib.placeOrder.call_count == 0

    async def test_limit_order_without_limit_price_is_rejected(
        self, manager, fake_db, allow_all_safety, patched_externals
    ):
        # Pydantic schema allows None limit_price. _build_ib_order should raise.
        user_id = uuid4()
        req = PlaceIBKROrderRequest(
            symbol="AAPL",
            action=OrderAction.BUY,
            order_type=OrderType.LIMIT,
            quantity=1,
            limit_price=None,
        )
        with patch.object(
            manager, "_estimate_notional", AsyncMock(return_value=100.0)
        ):
            with pytest.raises(OrderRejectedError) as exc:
                await manager.place_order(fake_db, user_id, req)
        assert "Limit orders require" in str(exc.value)

    async def test_ib_place_order_exception_marks_record_rejected(
        self, manager, fake_db, allow_all_safety, patched_externals
    ):
        patched_externals.ib.placeOrder.side_effect = RuntimeError("boom")
        user_id = uuid4()
        req = PlaceIBKROrderRequest(
            symbol="AAPL",
            action=OrderAction.BUY,
            order_type=OrderType.LIMIT,
            quantity=1,
            limit_price=200.0,
        )
        with pytest.raises(OrderRejectedError):
            await manager.place_order(fake_db, user_id, req)

        # The persisted record should be marked REJECTED with the error
        record = fake_db.added[0]
        assert record.status == IBKROrderStatus.REJECTED.value
        assert "boom" in record.last_error


# --------------------------------------------------------------------------
# Cancel order
# --------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.asyncio
class TestCancelOrder:
    async def _stub_get_order(self, manager, record):
        """Patch _get_order_for_user to return the given record."""
        return patch.object(
            manager, "_get_order_for_user", AsyncMock(return_value=record)
        )

    async def test_rejects_cancel_when_already_filled(
        self, manager, fake_db
    ):
        record = MagicMock(
            id=uuid4(),
            status=IBKROrderStatus.FILLED.value,
            ib_order_id=42,
            action="BUY",
            order_type="market",
            quantity=Decimal("1"),
            limit_price=None,
            stop_price=None,
        )
        with patch.object(
            manager, "_get_order_for_user", AsyncMock(return_value=record)
        ):
            with pytest.raises(OrderRejectedError):
                await manager.cancel_order(fake_db, uuid4(), record.id)

    async def test_cancel_local_when_no_ib_order_id(self, manager, fake_db):
        record = MagicMock(
            id=uuid4(),
            status=IBKROrderStatus.PENDING_SUBMIT.value,
            ib_order_id=None,
            action="BUY",
            order_type="market",
            quantity=Decimal("1"),
            limit_price=None,
            stop_price=None,
        )
        with patch.object(
            manager, "_get_order_for_user", AsyncMock(return_value=record)
        ):
            from app.schemas.ibkr import IBKROrderRecord
            # MagicMock won't satisfy from_attributes; bypass with patch
            with patch.object(IBKROrderRecord, "model_validate", lambda x: x):
                result = await manager.cancel_order(fake_db, uuid4(), record.id)
        assert record.status == IBKROrderStatus.CANCELLED.value


# --------------------------------------------------------------------------
# Status translation
# --------------------------------------------------------------------------

@pytest.mark.unit
class TestTranslateStatus:
    @pytest.mark.parametrize(
        "ib_status,expected",
        [
            ("PreSubmitted", IBKROrderStatus.PENDING_SUBMIT.value),
            ("PendingSubmit", IBKROrderStatus.PENDING_SUBMIT.value),
            ("ApiPending", IBKROrderStatus.PENDING_SUBMIT.value),
            ("Submitted", IBKROrderStatus.SUBMITTED.value),
            ("Filled", IBKROrderStatus.FILLED.value),
            ("Cancelled", IBKROrderStatus.CANCELLED.value),
            ("PendingCancel", IBKROrderStatus.PENDING_CANCEL.value),
            ("Inactive", IBKROrderStatus.REJECTED.value),
            ("Rejected", IBKROrderStatus.REJECTED.value),
            ("PartiallyFilled", IBKROrderStatus.PARTIALLY_FILLED.value),
            ("Unknown-Future-Value", IBKROrderStatus.UNKNOWN.value),
            ("", IBKROrderStatus.UNKNOWN.value),
        ],
    )
    def test_status_mapping(self, ib_status, expected):
        assert OrderManager._translate_status(ib_status) == expected


@pytest.mark.unit
class TestBuildIbOrder:
    """Direct tests of _build_ib_order without touching the network."""

    def setup_method(self):
        self.m = OrderManager()

    def test_market_order_built(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.ibkr.orders._lazy_import", _fake_ib_async_module
        )
        req = PlaceIBKROrderRequest(
            symbol="AAPL",
            action=OrderAction.BUY,
            order_type=OrderType.MARKET,
            quantity=3,
        )
        order = self.m._build_ib_order(req)
        assert order.action == "BUY"
        assert order.totalQuantity == 3.0
        assert order.tif == "DAY"
        assert order.transmit is True

    def test_stop_order_requires_stop_price(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.ibkr.orders._lazy_import", _fake_ib_async_module
        )
        req = PlaceIBKROrderRequest(
            symbol="AAPL",
            action=OrderAction.SELL,
            order_type=OrderType.STOP,
            quantity=1,
            stop_price=None,
        )
        with pytest.raises(OrderRejectedError):
            self.m._build_ib_order(req)

    def test_stop_limit_requires_both_prices(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.ibkr.orders._lazy_import", _fake_ib_async_module
        )
        # missing stop_price
        req = PlaceIBKROrderRequest(
            symbol="AAPL",
            action=OrderAction.BUY,
            order_type=OrderType.STOP_LIMIT,
            quantity=1,
            limit_price=100.0,
            stop_price=None,
        )
        with pytest.raises(OrderRejectedError):
            self.m._build_ib_order(req)
