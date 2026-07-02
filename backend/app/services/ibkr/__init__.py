"""
Interactive Brokers (IBKR) integration package.

Wraps the `ib-async` library (BSD-2-Clause) to provide a controlled, audited
order-placement and market-data surface for the Financial Analysis Platform.

Entry points:
- `ibkr_client` (singleton): connection management to TWS / IB Gateway.
- `order_manager`: place / cancel / track orders with safety brakes.
- `contract_resolver`: ticker -> Contract resolution with caching.

Configuration is read from `app.core.config.settings.IBKR_*`. The integration
remains a no-op (and never imports `ib_async`) when `IBKR_ENABLED=False`, so
the rest of the platform runs unchanged.
"""

from app.services.ibkr.client import ibkr_client, IBKRClient, IBKRConnectionState
from app.services.ibkr.contracts import contract_resolver, ContractResolver
from app.services.ibkr.orders import order_manager, OrderManager
from app.services.ibkr.safety import safety_gate, SafetyGate

__all__ = [
    "ibkr_client",
    "IBKRClient",
    "IBKRConnectionState",
    "contract_resolver",
    "ContractResolver",
    "order_manager",
    "OrderManager",
    "safety_gate",
    "SafetyGate",
]
