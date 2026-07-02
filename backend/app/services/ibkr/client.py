"""
IBKR connection manager.

Owns the singleton ib_async.IB() instance, manages connect/disconnect/reconnect
to TWS or IB Gateway, and exposes a `with_connection()` async helper that
guarantees the connection is live before invoking IBKR API calls.

`ib-async` is imported lazily so that the rest of the backend does not require
it at import time. If `IBKR_ENABLED=false`, this module never touches `ib_async`.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.services.ibkr.client")


class IBKRNotAvailableError(RuntimeError):
    """Raised when an IBKR-dependent call is made while IBKR is disabled
    or the underlying ib_async library is not installed."""


class IBKRConnectionError(RuntimeError):
    """Raised when the backend cannot reach TWS / IB Gateway."""


class IBKRConnectionState(str, Enum):
    DISABLED = "disabled"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class IBKRStatus:
    state: IBKRConnectionState
    host: str
    port: int
    client_id: int
    account_id: Optional[str]
    readonly: bool
    last_error: Optional[str] = None
    reconnect_attempts: int = 0
    server_version: Optional[int] = None


class IBKRClient:
    """
    Thin async wrapper around `ib_async.IB`.

    Lifecycle:
    - `await client.connect()`     idempotent; reuses existing connection.
    - `await client.disconnect()`  graceful close.
    - `await client.ensure_connected()` reconnects with backoff if dropped.

    Threading: `ib_async` uses asyncio internally, so we keep one `IB()`
    instance per backend process. TWS only accepts ONE socket per
    `clientId`, so do not change `IBKR_CLIENT_ID` while connected.
    """

    def __init__(self) -> None:
        self._ib: Any = None  # ib_async.IB, lazily imported
        self._lock = asyncio.Lock()
        self._state = (
            IBKRConnectionState.DISABLED
            if not settings.IBKR_ENABLED
            else IBKRConnectionState.DISCONNECTED
        )
        self._reconnect_attempts = 0
        self._last_error: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    @property
    def state(self) -> IBKRConnectionState:
        return self._state

    @property
    def ib(self) -> Any:
        """The underlying ib_async.IB instance. Caller must have connected."""
        if self._ib is None:
            raise IBKRNotAvailableError(
                "IBKR client not initialised. Call connect() first or set "
                "IBKR_ENABLED=true."
            )
        return self._ib

    def status(self) -> IBKRStatus:
        server_version = None
        try:
            if self._ib is not None and self._ib.isConnected():
                server_version = self._ib.client.serverVersion()
        except Exception:  # pragma: no cover - server_version is best-effort
            pass
        return IBKRStatus(
            state=self._state,
            host=settings.IBKR_HOST,
            port=settings.IBKR_PORT,
            client_id=settings.IBKR_CLIENT_ID,
            account_id=settings.IBKR_ACCOUNT_ID,
            readonly=settings.IBKR_READONLY,
            last_error=self._last_error,
            reconnect_attempts=self._reconnect_attempts,
            server_version=server_version,
        )

    async def connect(self) -> IBKRStatus:
        """Connect to TWS / IB Gateway. Idempotent."""
        if not settings.IBKR_ENABLED:
            raise IBKRNotAvailableError(
                "IBKR integration is disabled. Set IBKR_ENABLED=true in .env "
                "and restart the backend."
            )

        async with self._lock:
            if self._ib is not None and self._ib.isConnected():
                self._state = IBKRConnectionState.CONNECTED
                return self.status()

            ib_async = self._import_ib_async()
            if self._ib is None:
                self._ib = ib_async.IB()
                # Wire up disconnect handler for auto-reconnect
                self._ib.disconnectedEvent += self._on_disconnect  # type: ignore[attr-defined]
                self._ib.errorEvent += self._on_error  # type: ignore[attr-defined]

            self._state = IBKRConnectionState.CONNECTING
            try:
                await self._ib.connectAsync(
                    host=settings.IBKR_HOST,
                    port=settings.IBKR_PORT,
                    clientId=settings.IBKR_CLIENT_ID,
                    readonly=settings.IBKR_READONLY,
                    timeout=10,
                )
            except Exception as exc:
                self._state = IBKRConnectionState.FAILED
                self._last_error = str(exc)
                logger.error(
                    "IBKR connect failed (host=%s port=%s clientId=%s): %s",
                    settings.IBKR_HOST,
                    settings.IBKR_PORT,
                    settings.IBKR_CLIENT_ID,
                    exc,
                )
                raise IBKRConnectionError(
                    f"Could not connect to TWS / IB Gateway at "
                    f"{settings.IBKR_HOST}:{settings.IBKR_PORT}. "
                    "Verify TWS is running, 'Enable ActiveX and Socket Clients' is "
                    "on, the API port matches, and 127.0.0.1 is in Trusted IPs."
                ) from exc

            self._state = IBKRConnectionState.CONNECTED
            self._reconnect_attempts = 0
            self._last_error = None
            logger.info(
                "IBKR connected: host=%s port=%s clientId=%s account=%s",
                settings.IBKR_HOST,
                settings.IBKR_PORT,
                settings.IBKR_CLIENT_ID,
                settings.IBKR_ACCOUNT_ID or "<default>",
            )
            return self.status()

    async def disconnect(self) -> None:
        async with self._lock:
            if self._ib is not None and self._ib.isConnected():
                self._ib.disconnect()
                logger.info("IBKR disconnected")
            self._state = IBKRConnectionState.DISCONNECTED

    async def ensure_connected(self) -> Any:
        """
        Return a live `ib_async.IB` instance, reconnecting if needed.
        Backoff: linear up to `IBKR_MAX_RECONNECT_ATTEMPTS`.
        """
        if not settings.IBKR_ENABLED:
            raise IBKRNotAvailableError("IBKR integration is disabled.")

        if self._ib is not None and self._ib.isConnected():
            return self._ib

        for attempt in range(1, settings.IBKR_MAX_RECONNECT_ATTEMPTS + 1):
            self._reconnect_attempts = attempt
            self._state = IBKRConnectionState.RECONNECTING
            try:
                await self.connect()
                return self._ib
            except IBKRConnectionError as exc:
                self._last_error = str(exc)
                if attempt >= settings.IBKR_MAX_RECONNECT_ATTEMPTS:
                    self._state = IBKRConnectionState.FAILED
                    raise
                delay = settings.IBKR_RECONNECT_DELAY_SECONDS * attempt
                logger.warning(
                    "IBKR reconnect attempt %d/%d failed; sleeping %ds",
                    attempt,
                    settings.IBKR_MAX_RECONNECT_ATTEMPTS,
                    delay,
                )
                await asyncio.sleep(delay)
        raise IBKRConnectionError("Exhausted IBKR reconnect attempts")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _import_ib_async() -> Any:
        """Lazy import — raise a helpful error if ib_async is missing."""
        try:
            import ib_async  # type: ignore
        except ImportError as exc:
            raise IBKRNotAvailableError(
                "The `ib-async` package is not installed. Run:\n"
                "  pip install ib-async\n"
                "Or set IBKR_ENABLED=false to disable the integration."
            ) from exc
        return ib_async

    def _on_disconnect(self) -> None:
        logger.warning("IBKR disconnected event received")
        self._state = IBKRConnectionState.DISCONNECTED

    def _on_error(
        self, reqId: int, errorCode: int, errorString: str, contract: Any
    ) -> None:
        # IBKR error codes:
        # 1100/1101/1102 = connectivity events; 2104/2106/2158 = warnings.
        # Code < 1000 is usually a real error.
        info_codes = {2104, 2106, 2107, 2108, 2119, 2158, 2168, 2169}
        if errorCode in info_codes:
            logger.debug("IBKR info %d: %s", errorCode, errorString)
            return
        if errorCode in {1100, 1101, 1102}:
            logger.warning("IBKR connectivity event %d: %s", errorCode, errorString)
            return
        self._last_error = f"[{errorCode}] {errorString}"
        logger.error(
            "IBKR error reqId=%s code=%d msg=%s contract=%s",
            reqId,
            errorCode,
            errorString,
            contract,
        )


# Module-level singleton
ibkr_client = IBKRClient()
