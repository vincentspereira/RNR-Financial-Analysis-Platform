"""
Symbol -> ib_async.Contract resolution with a small in-process cache.

For Paper Trading on TWS, we default to US-listed Stock contracts on SMART
routing with USD currency. Power users can supply explicit exchange / currency
overrides through the API.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from app.core.logging import get_logger
from app.services.ibkr.client import ibkr_client

logger = get_logger("app.services.ibkr.contracts")


@dataclass(frozen=True)
class ContractKey:
    symbol: str
    sec_type: str
    exchange: str
    currency: str
    expiry: Optional[str] = None  # YYYYMMDD for options/futures


class ContractResolver:
    """Cache of resolved ib_async.Contract objects keyed by ContractKey."""

    def __init__(self) -> None:
        self._cache: Dict[ContractKey, Any] = {}
        self._lock = asyncio.Lock()

    async def resolve(
        self,
        symbol: str,
        sec_type: str = "STK",
        exchange: str = "SMART",
        currency: str = "USD",
        expiry: Optional[str] = None,
    ) -> Any:
        """
        Resolve a ticker to a fully-qualified ib_async.Contract via
        IBKR's qualifyContracts(). Cached.

        Returns:
            ib_async.Contract instance.

        Raises:
            ValueError if IBKR cannot resolve the contract (ambiguous /
            unknown symbol).
        """
        key = ContractKey(
            symbol=symbol.upper().strip(),
            sec_type=sec_type.upper(),
            exchange=exchange.upper(),
            currency=currency.upper(),
            expiry=expiry,
        )
        async with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

        ib = await ibkr_client.ensure_connected()
        ib_async = _lazy_import()

        if key.sec_type == "STK":
            contract = ib_async.Stock(key.symbol, key.exchange, key.currency)
        elif key.sec_type == "OPT" and key.expiry:
            # Caller can supply full Option contract via separate path if needed
            contract = ib_async.Option(
                key.symbol, key.expiry, 0.0, "C", key.exchange, currency=key.currency
            )
        elif key.sec_type == "FUT" and key.expiry:
            contract = ib_async.Future(
                key.symbol, key.expiry, key.exchange, currency=key.currency
            )
        elif key.sec_type == "CASH":
            # Forex pair like EURUSD -> Forex('EUR', 'IDEALPRO', 'USD')
            base, quote = key.symbol[:3], key.symbol[3:]
            contract = ib_async.Forex(pair=key.symbol, exchange=key.exchange or "IDEALPRO")
        else:
            raise ValueError(
                f"Unsupported sec_type {key.sec_type!r} for symbol {key.symbol!r}"
            )

        qualified = await ib.qualifyContractsAsync(contract)
        if not qualified or not qualified[0].conId:
            raise ValueError(
                f"IBKR could not resolve contract {key.symbol} "
                f"({key.sec_type}/{key.exchange}/{key.currency}). "
                "Check the symbol, exchange, and currency."
            )

        resolved = qualified[0]
        async with self._lock:
            self._cache[key] = resolved
        logger.info("Resolved %s -> conId=%s", key.symbol, resolved.conId)
        return resolved


def _lazy_import() -> Any:
    import ib_async  # type: ignore

    return ib_async


contract_resolver = ContractResolver()
