"""
Deep tests for IBKR client lifecycle, contract resolution, and error paths.
`ib_async` is fully mocked.
"""
from __future__ import annotations

import asyncio
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ibkr.client import (
    IBKRClient,
    IBKRConnectionError,
    IBKRConnectionState,
    IBKRNotAvailableError,
)
from app.services.ibkr.contracts import ContractResolver


def _fake_ib_async_module() -> types.ModuleType:
    mod = types.ModuleType("ib_async")
    mod.IB = MagicMock(return_value=MagicMock())

    def _Stock(*args, **kwargs):
        return SimpleNamespace(symbol=args[0] if args else None, conId=0)

    def _Forex(*args, **kwargs):
        return SimpleNamespace(symbol=kwargs.get("pair"), conId=0)

    mod.Stock = _Stock
    mod.Forex = _Forex
    mod.Option = lambda *a, **kw: SimpleNamespace(conId=0)
    mod.Future = lambda *a, **kw: SimpleNamespace(conId=0)
    return mod


# ---------------------------------------------------------------------------
# IBKRClient lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestIBKRClient:
    async def test_disabled_state_when_settings_disabled(self):
        with patch("app.services.ibkr.client.settings.IBKR_ENABLED", False):
            client = IBKRClient()
            assert client.state == IBKRConnectionState.DISABLED

    async def test_connect_raises_when_disabled(self):
        with patch("app.services.ibkr.client.settings.IBKR_ENABLED", False):
            client = IBKRClient()
            with pytest.raises(IBKRNotAvailableError):
                await client.connect()

    async def test_ensure_connected_raises_when_disabled(self):
        with patch("app.services.ibkr.client.settings.IBKR_ENABLED", False):
            client = IBKRClient()
            with pytest.raises(IBKRNotAvailableError):
                await client.ensure_connected()

    async def test_status_reports_disabled(self):
        with patch("app.services.ibkr.client.settings.IBKR_ENABLED", False):
            client = IBKRClient()
            s = client.status()
            assert s.state == IBKRConnectionState.DISABLED

    async def test_ib_property_raises_when_uninitialized(self):
        with patch("app.services.ibkr.client.settings.IBKR_ENABLED", True):
            client = IBKRClient()
            with pytest.raises(IBKRNotAvailableError):
                _ = client.ib

    async def test_lazy_import_raises_helpful_error(self):
        # Force ImportError on ib_async
        with patch.dict("sys.modules", {"ib_async": None}):
            with pytest.raises(IBKRNotAvailableError) as exc_info:
                IBKRClient._import_ib_async()
            # Error message references pip install
            assert "pip install" in str(exc_info.value)

    async def test_on_disconnect_handler_changes_state(self):
        with patch("app.services.ibkr.client.settings.IBKR_ENABLED", True):
            client = IBKRClient()
            client._on_disconnect()
            assert client.state == IBKRConnectionState.DISCONNECTED

    async def test_on_error_handler_skips_info_codes(self):
        with patch("app.services.ibkr.client.settings.IBKR_ENABLED", True):
            client = IBKRClient()
            client._on_error(reqId=1, errorCode=2104, errorString="Market data farm", contract=None)
            # Info codes don't set last_error
            assert client._last_error is None

    async def test_on_error_handler_captures_real_errors(self):
        with patch("app.services.ibkr.client.settings.IBKR_ENABLED", True):
            client = IBKRClient()
            client._on_error(reqId=1, errorCode=200, errorString="No security", contract=None)
            assert client._last_error is not None
            assert "200" in client._last_error

    async def test_disconnect_with_no_ib_is_safe(self):
        with patch("app.services.ibkr.client.settings.IBKR_ENABLED", True):
            client = IBKRClient()
            client._ib = None
            await client.disconnect()
            assert client.state == IBKRConnectionState.DISCONNECTED


# ---------------------------------------------------------------------------
# ContractResolver
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestContractResolver:
    async def test_unsupported_sec_type_raises(self):
        resolver = ContractResolver()
        with patch(
            "app.services.ibkr.contracts.ibkr_client.ensure_connected",
            AsyncMock(return_value=MagicMock()),
        ), patch(
            "app.services.ibkr.contracts._lazy_import", _fake_ib_async_module
        ):
            with pytest.raises(ValueError, match="Unsupported sec_type"):
                await resolver.resolve("AAPL", sec_type="BOND")

    async def test_stock_resolution_caches_result(self):
        resolver = ContractResolver()
        mock_ib = MagicMock()
        contract = SimpleNamespace(symbol="AAPL", conId=12345)
        mock_ib.qualifyContractsAsync = AsyncMock(return_value=[contract])
        with patch(
            "app.services.ibkr.contracts.ibkr_client.ensure_connected",
            AsyncMock(return_value=mock_ib),
        ), patch(
            "app.services.ibkr.contracts._lazy_import", _fake_ib_async_module
        ):
            first = await resolver.resolve("AAPL")
            assert first is contract
            # Second call should return cached value (no new qualifyContractsAsync)
            mock_ib.qualifyContractsAsync.reset_mock()
            second = await resolver.resolve("AAPL")
            assert second is contract
            mock_ib.qualifyContractsAsync.assert_not_called()

    async def test_resolution_failure_raises(self):
        resolver = ContractResolver()
        mock_ib = MagicMock()
        # qualifyContractsAsync returns empty list
        mock_ib.qualifyContractsAsync = AsyncMock(return_value=[])
        with patch(
            "app.services.ibkr.contracts.ibkr_client.ensure_connected",
            AsyncMock(return_value=mock_ib),
        ), patch(
            "app.services.ibkr.contracts._lazy_import", _fake_ib_async_module
        ):
            with pytest.raises(ValueError, match="could not resolve"):
                await resolver.resolve("BADTICKER")

    async def test_resolution_with_invalid_conid_raises(self):
        resolver = ContractResolver()
        mock_ib = MagicMock()
        # Returns a contract with conId=0 (not resolved)
        mock_ib.qualifyContractsAsync = AsyncMock(
            return_value=[SimpleNamespace(symbol="X", conId=0)]
        )
        with patch(
            "app.services.ibkr.contracts.ibkr_client.ensure_connected",
            AsyncMock(return_value=mock_ib),
        ), patch(
            "app.services.ibkr.contracts._lazy_import", _fake_ib_async_module
        ):
            with pytest.raises(ValueError):
                await resolver.resolve("UNKNOWN")
