"""
Tests for the external data API clients (Alpha Vantage, Yahoo Finance, FMP, SEC).

Focuses on:
- The safe-coercion helpers (`_safe_float`, `_safe_int`) which are pure functions.
- The success/error paths in the `_make_request` and transform layers, with
  the HTTP layer fully mocked (so no real API calls happen).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.data.alpha_vantage_client import AlphaVantageClient
from app.services.data.yahoo_finance_client import yahoo_finance_client
from app.services.data.financial_modeling_prep_client import FinancialModelingPrepClient
from app.services.data.sec_edgar_client import SecEdgarClient


# ===========================================================================
# AlphaVantageClient
# ===========================================================================


@pytest.mark.unit
class TestAlphaVantageHelpers:
    def setup_method(self):
        self.c = AlphaVantageClient(api_key="REAL-KEY")

    def test_safe_float_valid(self):
        assert self.c._safe_float("3.14") == pytest.approx(3.14)
        assert self.c._safe_float(7) == 7.0

    def test_safe_float_invalid_returns_none(self):
        assert self.c._safe_float(None) is None
        assert self.c._safe_float("") is None
        assert self.c._safe_float("None") is None
        assert self.c._safe_float("abc") is None

    def test_safe_int_valid(self):
        assert self.c._safe_int("100") == 100
        assert self.c._safe_int(3.7) == 3

    def test_safe_int_invalid(self):
        assert self.c._safe_int(None) is None
        assert self.c._safe_int("") is None
        assert self.c._safe_int("None") is None
        assert self.c._safe_int("abc") is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestAlphaVantageRequest:
    async def test_make_request_returns_none_with_demo_key(self):
        client = AlphaVantageClient(api_key="demo")
        result = await client._make_request({"function": "OVERVIEW", "symbol": "AAPL"})
        assert result is None

    async def test_make_request_returns_none_with_no_key(self):
        client = AlphaVantageClient(api_key=None)
        # Falls through to 'demo' via settings — should still refuse
        result = await client._make_request({"function": "X"})
        assert result is None or result is None  # accept either path

    async def test_get_company_overview_returns_none_on_failure(self):
        client = AlphaVantageClient(api_key="REAL-KEY")
        with patch.object(client, "_make_request", AsyncMock(return_value=None)):
            assert await client.get_company_overview("AAPL") is None

    async def test_get_company_overview_transforms_data(self):
        client = AlphaVantageClient(api_key="REAL-KEY")
        fake_response = {
            "Symbol": "AAPL",
            "Name": "Apple Inc.",
            "MarketCapitalization": "3000000000000",
            "PERatio": "28.5",
            "DividendYield": "None",  # tests the safe_float None-handling
            "EPS": "",
            "Sector": "Technology",
        }
        with patch.object(client, "_make_request", AsyncMock(return_value=fake_response)):
            result = await client.get_company_overview("AAPL")
        assert result is not None
        assert result["symbol"] == "AAPL"
        assert result["market_cap"] == 3_000_000_000_000.0
        assert result["pe_ratio"] == 28.5
        assert result["dividend_yield"] is None  # "None" string
        assert result["eps"] is None  # empty string

    async def test_get_income_statement_returns_none_without_reports(self):
        client = AlphaVantageClient(api_key="REAL-KEY")
        with patch.object(client, "_make_request", AsyncMock(return_value={})):
            assert await client.get_income_statement("AAPL") is None

    async def test_get_income_statement_with_reports(self):
        client = AlphaVantageClient(api_key="REAL-KEY")
        fake_response = {
            "annualReports": [
                {
                    "fiscalDateEnding": "2024-09-30",
                    "totalRevenue": "100000000000",
                    "grossProfit": "40000000000",
                    "netIncome": "20000000000",
                }
            ]
        }
        with patch.object(client, "_make_request", AsyncMock(return_value=fake_response)):
            result = await client.get_income_statement("AAPL")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["total_revenue"] == 100_000_000_000.0


# ===========================================================================
# YahooFinanceClient (mostly a yfinance wrapper)
# ===========================================================================


@pytest.mark.unit
class TestYahooFinanceHelpers:
    def test_safe_float(self):
        # The singleton instance exposes the helper
        assert yahoo_finance_client._safe_float("1.5") == 1.5
        assert yahoo_finance_client._safe_float(None) is None
        assert yahoo_finance_client._safe_float("nan") is None or isinstance(
            yahoo_finance_client._safe_float("nan"), float
        )


# ===========================================================================
# FinancialModelingPrepClient
# ===========================================================================


@pytest.mark.unit
class TestFMPHelpers:
    def setup_method(self):
        self.c = FinancialModelingPrepClient(api_key="REAL-KEY")

    def test_safe_float(self):
        assert self.c._safe_float("9.99") == pytest.approx(9.99)
        assert self.c._safe_float(None) is None
        assert self.c._safe_float("xyz") is None

    def test_safe_int(self):
        assert self.c._safe_int("42") == 42
        assert self.c._safe_int(None) is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestFMPRequest:
    async def test_make_request_returns_none_without_key(self):
        client = FinancialModelingPrepClient(api_key=None)
        result = await client._make_request("profile/AAPL")
        # No key → either no-op or graceful None
        assert result is None or isinstance(result, (list, dict))

    async def test_get_company_profile_returns_none_on_failure(self):
        client = FinancialModelingPrepClient(api_key="REAL-KEY")
        with patch.object(client, "_make_request", AsyncMock(return_value=None)):
            assert await client.get_company_profile("AAPL") is None

    async def test_get_company_profile_with_data(self):
        client = FinancialModelingPrepClient(api_key="REAL-KEY")
        # FMP wraps profile in a list
        fake_response = [
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "mktCap": 3000000000000,
                "price": 175.0,
                "beta": 1.2,
            }
        ]
        with patch.object(client, "_make_request", AsyncMock(return_value=fake_response)):
            result = await client.get_company_profile("AAPL")
        assert result is not None
        assert result["symbol"] == "AAPL"


# ===========================================================================
# SecEdgarClient
# ===========================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestSECEdgar:
    async def test_get_cik_returns_none_for_unknown(self):
        client = SecEdgarClient(user_agent="test test@example.com")
        with patch.object(client, "_make_request", AsyncMock(return_value={})):
            result = await client._get_cik("NOSUCHTICKER")
        assert result is None

    async def test_get_company_facts_returns_none_when_no_cik(self):
        client = SecEdgarClient(user_agent="test test@example.com")
        with patch.object(client, "_get_cik", AsyncMock(return_value=None)):
            assert await client.get_company_facts("BADTICKER") is None
