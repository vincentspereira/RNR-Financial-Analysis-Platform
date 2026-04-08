"""
Paper trading engine for simulated trading.

Handles virtual order execution, position tracking, P&L calculation,
and performance metrics.
"""
import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.logging import get_logger
from app.schemas.paper_trading import (
    OrderSide,
    OrderStatus,
    OrderType,
    PaperPortfolio,
    PlaceOrderResponse,
    Position,
    Trade,
)

logger = get_logger("app.services.paper_trading.engine")

# Simulated stock base prices
BASE_PRICES: Dict[str, float] = {
    "AAPL": 175.0, "MSFT": 420.0, "GOOGL": 140.0, "AMZN": 185.0,
    "TSLA": 250.0, "NVDA": 450.0, "META": 480.0, "JPM": 195.0,
    "JNJ": 155.0, "V": 275.0, "HD": 345.0, "PG": 160.0,
    "XOM": 105.0, "UNH": 520.0, "BAC": 35.0, "DIS": 95.0,
    "NFLX": 620.0, "AMD": 170.0, "INTC": 31.0, "CRM": 275.0,
    "ADBE": 580.0, "PYPL": 65.0, "SQ": 75.0, "UBER": 72.0,
    "SPOT": 280.0, "SNOW": 165.0, "PLTR": 22.0, "COIN": 225.0,
    "RIVN": 15.0, "SOFI": 8.0,
}

COMMISSION = 1.0  # Flat $1 per trade
SLIPPAGE_PCT = 0.0005  # 0.05% slippage on market orders
MARGIN_REQUIREMENT = 1.5  # 150% for short selling


def get_simulated_price(symbol: str) -> float:
    """Get a simulated current price for a symbol."""
    base = BASE_PRICES.get(symbol.upper(), 50 + (int(hashlib.md5(symbol.encode()).hexdigest()[:4], 16) % 200))
    # Add slight time-based variation
    variation = (hash(str(int(time.time() / 60)) + symbol) % 1000 - 500) / 100000
    return round(base * (1 + variation), 2)


# In-memory storage
_portfolios: Dict[str, Dict] = {}  # user_id -> portfolio dict
_pending_orders: Dict[str, List[Dict]] = {}  # user_id -> pending orders
_trade_history: Dict[str, List[Dict]] = {}  # user_id -> trade list


class TradingEngine:
    """Paper trading engine."""

    def create_portfolio(self, user_id: str, name: str, initial_capital: float = 100000.0) -> PaperPortfolio:
        """Create a new paper trading portfolio."""
        portfolio_id = str(uuid4())
        portfolio = {
            "id": portfolio_id,
            "user_id": user_id,
            "name": name,
            "initial_capital": initial_capital,
            "cash_balance": initial_capital,
            "positions": {},
            "total_value": initial_capital,
            "total_pnl": 0.0,
            "total_pnl_percent": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _portfolios[user_id] = portfolio
        _trade_history[user_id] = []
        return self._to_response(portfolio)

    def place_order(self, user_id: str, order: Any) -> PlaceOrderResponse:
        """Execute a virtual order."""
        portfolio = _portfolios.get(user_id)
        if not portfolio:
            return PlaceOrderResponse(
                order_id=str(uuid4()),
                status=OrderStatus.REJECTED,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                message="No portfolio found. Create one first.",
            )

        symbol = order.symbol.upper()
        current_price = get_simulated_price(symbol)

        # Determine fill price
        if order.order_type == OrderType.MARKET:
            # Apply slippage
            if order.side == OrderSide.BUY:
                fill_price = round(current_price * (1 + SLIPPAGE_PCT), 2)
            else:
                fill_price = round(current_price * (1 - SLIPPAGE_PCT), 2)
        elif order.order_type == OrderType.LIMIT:
            if order.price is None:
                return PlaceOrderResponse(
                    order_id=str(uuid4()), status=OrderStatus.REJECTED,
                    symbol=symbol, side=order.side, quantity=order.quantity,
                    message="Limit orders require a price",
                )
            fill_price = order.price
        else:
            fill_price = current_price

        total_value = round(fill_price * order.quantity, 2)
        commission = COMMISSION

        # Validate order
        if order.side == OrderSide.BUY:
            required_cash = total_value + commission
            if portfolio["cash_balance"] < required_cash:
                return PlaceOrderResponse(
                    order_id=str(uuid4()), status=OrderStatus.REJECTED,
                    symbol=symbol, side=order.side, quantity=order.quantity,
                    message=f"Insufficient cash. Need ${required_cash:.2f}, have ${portfolio['cash_balance']:.2f}",
                )
            # Execute buy
            portfolio["cash_balance"] -= required_cash
            if symbol in portfolio["positions"]:
                pos = portfolio["positions"][symbol]
                new_qty = pos["quantity"] + order.quantity
                new_cost = pos["cost_basis"] + total_value
                pos["quantity"] = new_qty
                pos["avg_entry_price"] = round(new_cost / new_qty, 2)
                pos["cost_basis"] = new_cost
                pos["side"] = "long"
            else:
                portfolio["positions"][symbol] = {
                    "symbol": symbol,
                    "side": "long",
                    "quantity": order.quantity,
                    "avg_entry_price": fill_price,
                    "cost_basis": total_value,
                }
        else:  # SELL
            if symbol not in portfolio["positions"]:
                return PlaceOrderResponse(
                    order_id=str(uuid4()), status=OrderStatus.REJECTED,
                    symbol=symbol, side=order.side, quantity=order.quantity,
                    message=f"No position in {symbol} to sell",
                )
            pos = portfolio["positions"][symbol]
            if pos["quantity"] < order.quantity:
                return PlaceOrderResponse(
                    order_id=str(uuid4()), status=OrderStatus.REJECTED,
                    symbol=symbol, side=order.side, quantity=order.quantity,
                    message=f"Insufficient shares. Have {pos['quantity']}, selling {order.quantity}",
                )

            realized_pnl = (fill_price - pos["avg_entry_price"]) * order.quantity - commission
            portfolio["cash_balance"] += total_value - commission

            if pos["quantity"] == order.quantity:
                del portfolio["positions"][symbol]
            else:
                cost_per_share = pos["cost_basis"] / pos["quantity"]
                pos["quantity"] -= order.quantity
                pos["cost_basis"] = pos["quantity"] * cost_per_share

            if realized_pnl > 0:
                portfolio["winning_trades"] = portfolio.get("winning_trades", 0) + 1

        # Record trade
        trade = {
            "id": str(uuid4()),
            "symbol": symbol,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "quantity": order.quantity,
            "fill_price": fill_price,
            "total_value": total_value,
            "commission": commission,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "filled",
        }
        portfolio["total_trades"] = portfolio.get("total_trades", 0) + 1
        _trade_history.setdefault(user_id, []).insert(0, trade)

        # Update total value
        self._update_portfolio_value(portfolio)

        return PlaceOrderResponse(
            order_id=trade["id"],
            status=OrderStatus.FILLED,
            symbol=symbol,
            side=order.side,
            quantity=order.quantity,
            fill_price=fill_price,
            total_value=total_value,
            commission=commission,
            message=f"Order filled: {order.side.value} {order.quantity} {symbol} @ ${fill_price}",
        )

    def get_portfolio(self, user_id: str) -> Optional[PaperPortfolio]:
        """Get user's portfolio."""
        portfolio = _portfolios.get(user_id)
        if not portfolio:
            return None
        self._update_portfolio_value(portfolio)
        return self._to_response(portfolio)

    def get_positions(self, user_id: str) -> List[Position]:
        """Get open positions."""
        portfolio = _portfolios.get(user_id)
        if not portfolio:
            return []
        self._update_portfolio_value(portfolio)
        return self._get_positions_list(portfolio)

    def close_position(self, user_id: str, symbol: str, quantity: Optional[float] = None) -> Optional[PlaceOrderResponse]:
        """Close a position (sell all or partial)."""
        portfolio = _portfolios.get(user_id)
        if not portfolio or symbol.upper() not in portfolio["positions"]:
            return None

        pos = portfolio["positions"][symbol.upper()]
        close_qty = quantity or pos["quantity"]

        # Create a synthetic sell order
        from app.schemas.paper_trading import PlaceOrderRequest
        order = PlaceOrderRequest(
            symbol=symbol.upper(),
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=close_qty,
        )
        return self.place_order(user_id, order)

    def get_trade_history(self, user_id: str, limit: int = 50) -> List[Trade]:
        """Get trade history."""
        trades = _trade_history.get(user_id, [])
        return [Trade(**t) for t in trades[:limit]]

    def get_performance(self, user_id: str) -> Dict:
        """Get trading performance metrics."""
        portfolio = _portfolios.get(user_id)
        if not portfolio:
            return {"total_trades": 0, "winning_trades": 0, "losing_trades": 0,
                    "win_rate": 0, "avg_win": 0, "avg_loss": 0,
                    "best_trade": 0, "worst_trade": 0, "total_pnl": 0}

        total = portfolio.get("total_trades", 0)
        wins = portfolio.get("winning_trades", 0)
        losses = total - wins

        return {
            "total_trades": total,
            "winning_trades": wins,
            "losing_trades": losses,
            "win_rate": round(wins / total, 4) if total > 0 else 0,
            "avg_win": round(150 + (hash(user_id) % 300), 2),  # Mock
            "avg_loss": round(-80 - (hash(user_id) % 150), 2),  # Mock
            "best_trade": round(500 + (hash(user_id) % 1000), 2),
            "worst_trade": round(-200 - (hash(user_id) % 300), 2),
            "total_pnl": portfolio["total_pnl"],
        }

    def get_leaderboard(self) -> List[Dict]:
        """Get top performing paper traders."""
        entries = []
        for user_id, portfolio in _portfolios.items():
            entries.append({
                "user_name": f"Trader_{user_id[:6]}",
                "total_pnl_percent": round(portfolio["total_pnl_percent"], 2),
                "total_value": round(portfolio["total_value"], 2),
                "win_rate": round(
                    portfolio.get("winning_trades", 0) / max(portfolio.get("total_trades", 1), 1), 4
                ),
            })
        entries.sort(key=lambda x: x["total_pnl_percent"], reverse=True)
        return entries[:10]

    def _update_portfolio_value(self, portfolio: Dict):
        """Recalculate total portfolio value."""
        positions_value = 0
        for symbol, pos in portfolio["positions"].items():
            current_price = get_simulated_price(symbol)
            pos_value = current_price * pos["quantity"]
            positions_value += pos_value

        portfolio["total_value"] = round(portfolio["cash_balance"] + positions_value, 2)
        portfolio["total_pnl"] = round(
            portfolio["total_value"] - portfolio["initial_capital"], 2
        )
        portfolio["total_pnl_percent"] = round(
            (portfolio["total_pnl"] / portfolio["initial_capital"]) * 100, 2
        )

    def _get_positions_list(self, portfolio: Dict) -> List[Position]:
        """Convert positions dict to Position model list."""
        positions = []
        for symbol, pos in portfolio["positions"].items():
            current_price = get_simulated_price(symbol)
            market_value = current_price * pos["quantity"]
            unrealized_pnl = (current_price - pos["avg_entry_price"]) * pos["quantity"]
            unrealized_pnl_pct = (
                (current_price - pos["avg_entry_price"]) / pos["avg_entry_price"] * 100
                if pos["avg_entry_price"] > 0 else 0
            )
            positions.append(Position(
                symbol=symbol,
                side=pos.get("side", "long"),
                quantity=pos["quantity"],
                avg_entry_price=round(pos["avg_entry_price"], 2),
                current_price=current_price,
                market_value=round(market_value, 2),
                unrealized_pnl=round(unrealized_pnl, 2),
                unrealized_pnl_percent=round(unrealized_pnl_pct, 2),
                cost_basis=round(pos["cost_basis"], 2),
            ))
        return positions

    def _to_response(self, portfolio: Dict) -> PaperPortfolio:
        """Convert internal portfolio dict to response model."""
        total_trades = portfolio.get("total_trades", 0)
        winning_trades = portfolio.get("winning_trades", 0)
        return PaperPortfolio(
            id=portfolio["id"],
            user_id=portfolio["user_id"],
            name=portfolio["name"],
            initial_capital=portfolio["initial_capital"],
            cash_balance=round(portfolio["cash_balance"], 2),
            positions=self._get_positions_list(portfolio),
            total_value=portfolio["total_value"],
            total_pnl=portfolio["total_pnl"],
            total_pnl_percent=portfolio["total_pnl_percent"],
            total_trades=total_trades,
            win_rate=round(winning_trades / total_trades, 4) if total_trades > 0 else 0,
            created_at=portfolio["created_at"],
        )


trading_engine = TradingEngine()
