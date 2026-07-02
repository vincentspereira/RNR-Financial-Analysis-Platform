"""
Order placement, cancellation, and tracking against IBKR.

Persists every order placed through this manager into the `ibkr_orders` table
(see app.models.ibkr) for audit, post-mortem analysis, and recovery after a
backend restart. Uses the singleton IBKRClient and ContractResolver.

Order types supported: market, limit, stop, stop-limit.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.ibkr import IBKROrder
from app.schemas.ibkr import (
    IBKROrderRecord,
    IBKROrderStatus,
    OrderAction,
    OrderType,
    PlaceIBKROrderRequest,
    TimeInForce,
)
from app.services.ibkr.client import IBKRConnectionError, ibkr_client
from app.services.ibkr.contracts import contract_resolver
from app.services.ibkr.safety import SafetyLimitExceeded, safety_gate

logger = get_logger("app.services.ibkr.orders")


class OrderRejectedError(RuntimeError):
    """Raised when IBKR or the safety gate rejects an order pre-placement."""


class OrderManager:
    async def place_order(
        self,
        db: AsyncSession,
        user_id: UUID,
        req: PlaceIBKROrderRequest,
    ) -> IBKROrderRecord:
        """
        Place an order on IBKR after running the safety gate, persisting the
        order, and forwarding to ib_async. The returned record reflects the
        order at submission time; status updates happen asynchronously and
        can be re-fetched via `get_order()`.
        """
        # 1. Resolve contract
        contract = await contract_resolver.resolve(
            symbol=req.symbol,
            sec_type=req.sec_type,
            exchange=req.exchange,
            currency=req.currency,
        )

        # 2. Compute notional. For market orders we use the most recent quote
        #    from IBKR's snapshot to do the safety check; if no quote, we
        #    fall back to req.limit_price * quantity, and if neither, we
        #    refuse the safety check (worst-case behavior — better safe).
        notional_usd = await self._estimate_notional(req)

        # 3. Safety gate
        decision = await safety_gate.check(str(user_id), notional_usd)
        if not decision.allowed:
            raise SafetyLimitExceeded(decision)

        # 4. Build ib_async.Order
        order = self._build_ib_order(req)

        # 5. Persist as PENDING_SUBMIT
        # NB: explicitly set Python-side defaults so the record is fully
        # populated even before flush (matters for callers that serialise
        # from-attributes immediately or when running against a mocked DB).
        now = datetime.now(timezone.utc)
        record = IBKROrder(
            id=uuid4(),
            user_id=user_id,
            client_order_id=str(uuid4()),
            symbol=req.symbol.upper(),
            sec_type=req.sec_type,
            exchange=req.exchange,
            currency=req.currency,
            action=req.action.value,
            order_type=req.order_type.value,
            quantity=Decimal(str(req.quantity)),
            limit_price=Decimal(str(req.limit_price)) if req.limit_price is not None else None,
            stop_price=Decimal(str(req.stop_price)) if req.stop_price is not None else None,
            time_in_force=req.time_in_force.value,
            account_id=settings.IBKR_ACCOUNT_ID,
            status=IBKROrderStatus.PENDING_SUBMIT.value,
            filled_quantity=Decimal(0),
            submitted_at=now,
            updated_at=now,
            notional_usd_at_submit=Decimal(str(notional_usd)),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        # 6. Submit to IBKR
        try:
            ib = await ibkr_client.ensure_connected()
            trade = ib.placeOrder(contract, order)
            await asyncio.sleep(0)  # let ib_async event loop process
        except IBKRConnectionError as exc:
            record.status = IBKROrderStatus.REJECTED.value
            record.last_error = f"IBKR not reachable: {exc}"
            record.updated_at = datetime.now(timezone.utc)
            await db.commit()
            raise OrderRejectedError(record.last_error) from exc
        except Exception as exc:
            record.status = IBKROrderStatus.REJECTED.value
            record.last_error = str(exc)
            record.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.error("placeOrder threw: %s", exc, exc_info=True)
            raise OrderRejectedError(str(exc)) from exc

        # 7. Record safety counters & update DB with IB-assigned id
        await safety_gate.record(str(user_id), notional_usd)
        record.ib_order_id = trade.order.orderId
        record.ib_perm_id = trade.order.permId
        record.status = self._translate_status(trade.orderStatus.status)
        record.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(record)

        return IBKROrderRecord.model_validate(record)

    async def cancel_order(
        self,
        db: AsyncSession,
        user_id: UUID,
        order_record_id: UUID,
    ) -> IBKROrderRecord:
        record = await self._get_order_for_user(db, user_id, order_record_id)
        if record.status in {
            IBKROrderStatus.FILLED.value,
            IBKROrderStatus.CANCELLED.value,
            IBKROrderStatus.REJECTED.value,
        }:
            raise OrderRejectedError(
                f"Cannot cancel order in state {record.status!r}"
            )

        if record.ib_order_id is None:
            # Never made it to IB; mark cancelled locally.
            record.status = IBKROrderStatus.CANCELLED.value
            record.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(record)
            return IBKROrderRecord.model_validate(record)

        ib = await ibkr_client.ensure_connected()
        # ib_async exposes `ib.cancelOrder(order)` — we need the Order instance.
        # Rebuild a minimal Order from the record so ib_async can match by orderId.
        ib_async = _lazy_import()
        order = ib_async.Order(
            orderId=record.ib_order_id,
            action=record.action,
            orderType=self._to_ib_order_type(record.order_type),
            totalQuantity=float(record.quantity),
        )
        if record.limit_price is not None:
            order.lmtPrice = float(record.limit_price)
        if record.stop_price is not None:
            order.auxPrice = float(record.stop_price)

        ib.cancelOrder(order)
        await asyncio.sleep(0)

        record.status = IBKROrderStatus.PENDING_CANCEL.value
        record.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(record)
        return IBKROrderRecord.model_validate(record)

    async def list_orders(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 50,
        include_closed: bool = True,
    ) -> List[IBKROrderRecord]:
        stmt = select(IBKROrder).where(IBKROrder.user_id == user_id)
        if not include_closed:
            stmt = stmt.where(
                IBKROrder.status.in_(
                    [
                        IBKROrderStatus.PENDING_SUBMIT.value,
                        IBKROrderStatus.SUBMITTED.value,
                        IBKROrderStatus.PARTIALLY_FILLED.value,
                        IBKROrderStatus.PENDING_CANCEL.value,
                    ]
                )
            )
        stmt = stmt.order_by(IBKROrder.submitted_at.desc()).limit(limit)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [IBKROrderRecord.model_validate(r) for r in rows]

    async def get_order(
        self,
        db: AsyncSession,
        user_id: UUID,
        order_record_id: UUID,
    ) -> IBKROrderRecord:
        record = await self._get_order_for_user(db, user_id, order_record_id)
        # Refresh status from live IB if order is still open.
        if record.status in {
            IBKROrderStatus.PENDING_SUBMIT.value,
            IBKROrderStatus.SUBMITTED.value,
            IBKROrderStatus.PARTIALLY_FILLED.value,
            IBKROrderStatus.PENDING_CANCEL.value,
        }:
            await self._sync_one(db, record)
        return IBKROrderRecord.model_validate(record)

    async def sync_open_orders(self, db: AsyncSession, user_id: UUID) -> int:
        """
        Sync the status of all open orders for `user_id` from IBKR into the DB.
        Returns the number of orders updated.
        """
        stmt = select(IBKROrder).where(
            IBKROrder.user_id == user_id,
            IBKROrder.status.in_(
                [
                    IBKROrderStatus.PENDING_SUBMIT.value,
                    IBKROrderStatus.SUBMITTED.value,
                    IBKROrderStatus.PARTIALLY_FILLED.value,
                    IBKROrderStatus.PENDING_CANCEL.value,
                ]
            ),
        )
        result = await db.execute(stmt)
        records = result.scalars().all()
        updated = 0
        for r in records:
            if await self._sync_one(db, r):
                updated += 1
        await db.commit()
        return updated

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    async def _get_order_for_user(
        self, db: AsyncSession, user_id: UUID, order_record_id: UUID
    ) -> IBKROrder:
        stmt = select(IBKROrder).where(
            IBKROrder.id == order_record_id, IBKROrder.user_id == user_id
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            raise OrderRejectedError(
                f"Order {order_record_id} not found for this user."
            )
        return record

    async def _sync_one(self, db: AsyncSession, record: IBKROrder) -> bool:
        if record.ib_order_id is None:
            return False
        try:
            ib = await ibkr_client.ensure_connected()
        except IBKRConnectionError:
            return False
        trades = ib.trades()
        match = next(
            (t for t in trades if t.order.orderId == record.ib_order_id), None
        )
        if match is None:
            return False
        new_status = self._translate_status(match.orderStatus.status)
        new_filled = Decimal(str(match.orderStatus.filled or 0))
        new_avg_fill = (
            Decimal(str(match.orderStatus.avgFillPrice))
            if match.orderStatus.avgFillPrice
            else None
        )
        changed = (
            record.status != new_status
            or record.filled_quantity != new_filled
            or record.avg_fill_price != new_avg_fill
        )
        record.status = new_status
        record.filled_quantity = new_filled
        record.avg_fill_price = new_avg_fill
        record.updated_at = datetime.now(timezone.utc)
        return changed

    async def _estimate_notional(self, req: PlaceIBKROrderRequest) -> float:
        """
        Best-effort estimate of order notional in USD for the safety gate.
        Uses limit_price if provided; otherwise pulls a snapshot quote.
        Returns 0.0 only if we genuinely can't estimate — caller's safety
        check will still operate on whatever we returned.
        """
        if req.limit_price is not None:
            return float(req.limit_price) * float(req.quantity)
        try:
            contract = await contract_resolver.resolve(
                symbol=req.symbol,
                sec_type=req.sec_type,
                exchange=req.exchange,
                currency=req.currency,
            )
            ib = await ibkr_client.ensure_connected()
            ticker = ib.reqMktData(contract, "", False, False)
            # Allow up to 2s for the snapshot
            for _ in range(20):
                await asyncio.sleep(0.1)
                price = ticker.last or ticker.close or ticker.marketPrice()
                if price and price > 0:
                    ib.cancelMktData(contract)
                    return float(price) * float(req.quantity)
            ib.cancelMktData(contract)
        except Exception as exc:  # pragma: no cover - best-effort
            logger.warning("Notional estimate failed for %s: %s", req.symbol, exc)
        # Worst case: we couldn't price it — fall back to quantity * 1
        return float(req.quantity)

    def _build_ib_order(self, req: PlaceIBKROrderRequest) -> Any:
        ib_async = _lazy_import()
        ib_action = "BUY" if req.action == OrderAction.BUY else "SELL"

        if req.order_type == OrderType.MARKET:
            order = ib_async.MarketOrder(
                action=ib_action, totalQuantity=float(req.quantity)
            )
        elif req.order_type == OrderType.LIMIT:
            if req.limit_price is None:
                raise OrderRejectedError("Limit orders require limit_price")
            order = ib_async.LimitOrder(
                action=ib_action,
                totalQuantity=float(req.quantity),
                lmtPrice=float(req.limit_price),
            )
        elif req.order_type == OrderType.STOP:
            if req.stop_price is None:
                raise OrderRejectedError("Stop orders require stop_price")
            order = ib_async.StopOrder(
                action=ib_action,
                totalQuantity=float(req.quantity),
                stopPrice=float(req.stop_price),
            )
        elif req.order_type == OrderType.STOP_LIMIT:
            if req.limit_price is None or req.stop_price is None:
                raise OrderRejectedError(
                    "Stop-limit orders require both stop_price and limit_price"
                )
            order = ib_async.StopLimitOrder(
                action=ib_action,
                totalQuantity=float(req.quantity),
                lmtPrice=float(req.limit_price),
                stopPrice=float(req.stop_price),
            )
        else:
            raise OrderRejectedError(f"Unsupported order_type {req.order_type}")

        order.tif = req.time_in_force.value
        if settings.IBKR_ACCOUNT_ID:
            order.account = settings.IBKR_ACCOUNT_ID
        order.transmit = True
        return order

    @staticmethod
    def _to_ib_order_type(order_type: str) -> str:
        return {
            OrderType.MARKET.value: "MKT",
            OrderType.LIMIT.value: "LMT",
            OrderType.STOP.value: "STP",
            OrderType.STOP_LIMIT.value: "STP LMT",
        }.get(order_type, order_type)

    @staticmethod
    def _translate_status(ib_status: str) -> str:
        """Map IBKR's status strings onto our enum."""
        s = (ib_status or "").lower()
        if s in {"presubmitted", "pendingsubmit", "apipending"}:
            return IBKROrderStatus.PENDING_SUBMIT.value
        if s in {"submitted", "apicancelled"}:
            return IBKROrderStatus.SUBMITTED.value
        if s in {"filled"}:
            return IBKROrderStatus.FILLED.value
        if s in {"cancelled", "apicanceled"}:
            return IBKROrderStatus.CANCELLED.value
        if s in {"pendingcancel"}:
            return IBKROrderStatus.PENDING_CANCEL.value
        if s in {"inactive", "rejected"}:
            return IBKROrderStatus.REJECTED.value
        if s in {"partiallyfilled"}:
            return IBKROrderStatus.PARTIALLY_FILLED.value
        return IBKROrderStatus.UNKNOWN.value


def _lazy_import() -> Any:
    import ib_async  # type: ignore

    return ib_async


order_manager = OrderManager()
