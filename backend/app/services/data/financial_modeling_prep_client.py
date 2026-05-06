"""
Financial Modeling Prep API client for financial data ingestion
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

import aiohttp

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.services.data.financial_modeling_prep")

FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


class FinancialModelingPrepClient:
    """
    Financial Modeling Prep API client
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "FINANCIAL_MODELING_PREP_API_KEY", "")
        self.base_url = FMP_BASE_URL
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _make_request(self, path: str, params: Optional[Dict] = None) -> Optional[Any]:
        if not self.api_key:
            logger.error("FMP: No API key configured. Set FINANCIAL_MODELING_PREP_API_KEY in your .env file.")
            return None

        params = params or {}
        params["apikey"] = self.api_key
        url = f"{self.base_url}/{path}"

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict) and 'Error Message' in data:
                        logger.error("FMP API error for %s: %s", path, data['Error Message'])
                        return None
                    return data
                logger.error("FMP request failed with status %s for %s", response.status, url)
                return None
        except Exception as e:
            logger.error("FMP request error: %s", e, exc_info=True)
            return None

    def _safe_float(self, value: Any) -> Optional[float]:
        if value is None or value == "None" or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> Optional[int]:
        if value is None or value == "None" or value == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    async def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get company profile data

        Args:
            symbol: Stock symbol

        Returns:
            Company profile data
        """
        data = await self._make_request(f"profile/{symbol}")
        if not data or not isinstance(data, list) or not data:
            return None

        profile = data[0]
        return {
            "symbol": profile.get("symbol"),
            "name": profile.get("companyName"),
            "description": profile.get("description"),
            "exchange": profile.get("exchangeShortName"),
            "currency": profile.get("currency"),
            "cik": profile.get("cik"),
            "isin": profile.get("isin"),
            "cusip": profile.get("cusip"),
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "website": profile.get("website"),
            "headquarters": profile.get("address"),
            "market_cap": self._safe_float(profile.get("mktCap")),
            "employees": self._safe_int(profile.get("fullTimeEmployees")),
            "ceo": profile.get("ceo"),
            "country": profile.get("country"),
            "phone": profile.get("phone"),
            "ipo_date": profile.get("ipoDate"),
            "price": self._safe_float(profile.get("price")),
            "beta": self._safe_float(profile.get("beta")),
            "vol_avg": self._safe_float(profile.get("volAvg")),
            "last_div": self._safe_float(profile.get("lastDiv")),
            "range": profile.get("range"),
            "changes": self._safe_float(profile.get("changes")),
            "dcf": self._safe_float(profile.get("dcf")),
            "image": profile.get("image"),
            "default_image": profile.get("defaultImage"),
            "is_etf": profile.get("isEtf"),
            "is_actively_trading": profile.get("isActivelyTrading"),
        }

    async def get_income_statements(
        self, symbol: str, period: str = "annual", limit: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get income statements

        Args:
            symbol: Stock symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to retrieve

        Returns:
            List of income statement dicts
        """
        data = await self._make_request(f"income-statement/{symbol}", {"period": period, "limit": limit})
        if not data or not isinstance(data, list):
            return None

        statements = []
        for stmt in data:
            statements.append({
                "fiscal_date_ending": stmt.get("date"),
                "reported_currency": stmt.get("reportedCurrency"),
                "period": stmt.get("period"),
                "revenue": self._safe_float(stmt.get("revenue")),
                "cost_of_revenue": self._safe_float(stmt.get("costOfRevenue")),
                "gross_profit": self._safe_float(stmt.get("grossProfit")),
                "gross_profit_ratio": self._safe_float(stmt.get("grossProfitRatio")),
                "rd_expenses": self._safe_float(stmt.get("researchAndDevelopmentExpenses")),
                "sga_expenses": self._safe_float(stmt.get("generalAndAdministrativeExpenses")),
                "selling_and_marketing_expenses": self._safe_float(stmt.get("sellingAndMarketingExpenses")),
                "operating_expenses": self._safe_float(stmt.get("operatingExpenses")),
                "operating_income": self._safe_float(stmt.get("operatingIncome")),
                "operating_income_ratio": self._safe_float(stmt.get("operatingIncomeRatio")),
                "interest_income": self._safe_float(stmt.get("interestIncome")),
                "interest_expense": self._safe_float(stmt.get("interestExpense")),
                "depreciation_and_amortization": self._safe_float(stmt.get("depreciationAndAmortization")),
                "ebitda": self._safe_float(stmt.get("ebitda")),
                "ebitda_ratio": self._safe_float(stmt.get("ebitdaratio")),
                "income_before_tax": self._safe_float(stmt.get("incomeBeforeTax")),
                "income_tax_expense": self._safe_float(stmt.get("incomeTaxExpense")),
                "net_income": self._safe_float(stmt.get("netIncome")),
                "net_income_ratio": self._safe_float(stmt.get("netIncomeRatio")),
                "eps": self._safe_float(stmt.get("eps")),
                "eps_diluted": self._safe_float(stmt.get("epsdiluted")),
                "weighted_average_shs_out": self._safe_float(stmt.get("weightedAverageShsOut")),
                "weighted_average_shs_out_dil": self._safe_float(stmt.get("weightedAverageShsOutDil")),
                "link": stmt.get("link"),
                "final_link": stmt.get("finalLink"),
            })

        return statements

    async def get_balance_sheets(
        self, symbol: str, period: str = "annual", limit: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get balance sheets

        Args:
            symbol: Stock symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to retrieve

        Returns:
            List of balance sheet dicts
        """
        data = await self._make_request(f"balance-sheet-statement/{symbol}", {"period": period, "limit": limit})
        if not data or not isinstance(data, list):
            return None

        sheets = []
        for bs in data:
            sheets.append({
                "fiscal_date_ending": bs.get("date"),
                "reported_currency": bs.get("reportedCurrency"),
                "cash_and_cash_equivalents": self._safe_float(bs.get("cashAndCashEquivalents")),
                "short_term_investments": self._safe_float(bs.get("shortTermInvestments")),
                "cash_and_short_term_investments": self._safe_float(bs.get("cashAndShortTermInvestments")),
                "net_receivables": self._safe_float(bs.get("netReceivables")),
                "inventory": self._safe_float(bs.get("inventory")),
                "total_current_assets": self._safe_float(bs.get("totalCurrentAssets")),
                "property_plant_equipment_net": self._safe_float(bs.get("propertyPlantEquipmentNet")),
                "goodwill": self._safe_float(bs.get("goodwill")),
                "intangible_assets": self._safe_float(bs.get("intangibleAssets")),
                "goodwill_and_intangible_assets": self._safe_float(bs.get("goodwillAndIntangibleAssets")),
                "long_term_investments": self._safe_float(bs.get("longTermInvestments")),
                "total_non_current_assets": self._safe_float(bs.get("totalNonCurrentAssets")),
                "total_assets": self._safe_float(bs.get("totalAssets")),
                "accounts_payable": self._safe_float(bs.get("accountPayables")),
                "short_term_debt": self._safe_float(bs.get("shortTermDebt")),
                "total_current_liabilities": self._safe_float(bs.get("totalCurrentLiabilities")),
                "long_term_debt": self._safe_float(bs.get("longTermDebt")),
                "total_non_current_liabilities": self._safe_float(bs.get("totalNonCurrentLiabilities")),
                "total_liabilities": self._safe_float(bs.get("totalLiabilities")),
                "common_stock": self._safe_float(bs.get("commonStock")),
                "retained_earnings": self._safe_float(bs.get("retainedEarnings")),
                "total_shareholder_equity": self._safe_float(bs.get("totalStockholdersEquity")),
                "total_liabilities_and_shareholder_equity": self._safe_float(bs.get("totalLiabilitiesAndStockholdersEquity")),
                "total_investments": self._safe_float(bs.get("totalInvestments")),
                "total_debt": self._safe_float(bs.get("totalDebt")),
                "net_debt": self._safe_float(bs.get("netDebt")),
                "link": bs.get("link"),
                "final_link": bs.get("finalLink"),
            })

        return sheets

    async def get_cash_flows(
        self, symbol: str, period: str = "annual", limit: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cash flow statements

        Args:
            symbol: Stock symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to retrieve

        Returns:
            List of cash flow dicts
        """
        data = await self._make_request(f"cash-flow-statement/{symbol}", {"period": period, "limit": limit})
        if not data or not isinstance(data, list):
            return None

        flows = []
        for cf in data:
            flows.append({
                "fiscal_date_ending": cf.get("date"),
                "reported_currency": cf.get("reportedCurrency"),
                "operating_cash_flow": self._safe_float(cf.get("operatingCashFlow")),
                "depreciation_and_amortization": self._safe_float(cf.get("depreciationAndAmortization")),
                "stock_based_compensation": self._safe_float(cf.get("stockBasedCompensation")),
                "change_in_working_capital": self._safe_float(cf.get("changeInWorkingCapital")),
                "accounts_receivables": self._safe_float(cf.get("accountsReceivables")),
                "inventory": self._safe_float(cf.get("inventory")),
                "accounts_payables": self._safe_float(cf.get("accountsPayables")),
                "other_working_capital": self._safe_float(cf.get("otherWorkingCapital")),
                "capital_expenditure": self._safe_float(cf.get("capitalExpenditure")),
                "acquisitions_net": self._safe_float(cf.get("acquisitionsNet")),
                "investments_in_property_plant_equipment": self._safe_float(cf.get("investmentsInPropertyPlantAndEquipment")),
                "purchases_of_investments": self._safe_float(cf.get("purchasesOfInvestments")),
                "sales_maturities_of_investments": self._safe_float(cf.get("salesMaturitiesOfInvestments")),
                "cash_flow_from_investment": self._safe_float(cf.get("netCashUsedForInvestingActivites")),
                "debt_repayment": self._safe_float(cf.get("debtRepayment")),
                "common_stock_issued": self._safe_float(cf.get("commonStockIssued")),
                "common_stock_repurchased": self._safe_float(cf.get("commonStockRepurchased")),
                "dividends_paid": self._safe_float(cf.get("dividendsPaid")),
                "cash_flow_from_financing": self._safe_float(cf.get("netCashUsedProvidedByFinancingActivities")),
                "net_change_in_cash": self._safe_float(cf.get("netChangeInCash")),
                "free_cash_flow": self._safe_float(cf.get("freeCashFlow")),
                "link": cf.get("link"),
                "final_link": cf.get("finalLink"),
            })

        return flows

    async def get_key_metrics(
        self, symbol: str, period: str = "annual", limit: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get key financial metrics/ratios

        Args:
            symbol: Stock symbol
            period: 'annual' or 'quarter'
            limit: Number of periods

        Returns:
            List of key metrics dicts
        """
        data = await self._make_request(f"key-metrics/{symbol}", {"period": period, "limit": limit})
        if not data or not isinstance(data, list):
            return None
        return data

    async def get_ratios(
        self, symbol: str, period: str = "annual", limit: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get financial ratios

        Args:
            symbol: Stock symbol
            period: 'annual' or 'quarter'
            limit: Number of periods

        Returns:
            List of ratio dicts
        """
        data = await self._make_request(f"ratios/{symbol}", {"period": period, "limit": limit})
        if not data or not isinstance(data, list):
            return None
        return data

    async def get_historical_prices(
        self, symbol: str, from_date: Optional[str] = None, to_date: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical daily price data

        Args:
            symbol: Stock symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of daily price records
        """
        path = f"historical-price-full/{symbol}"
        params = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        data = await self._make_request(path, params)
        if not data or "historical" not in data:
            return None

        prices = []
        for record in data["historical"]:
            prices.append({
                "date": record.get("date"),
                "open": self._safe_float(record.get("open")),
                "high": self._safe_float(record.get("high")),
                "low": self._safe_float(record.get("low")),
                "close": self._safe_float(record.get("close")),
                "adj_close": self._safe_float(record.get("adjClose")),
                "volume": self._safe_int(record.get("volume")),
                "unadjusted_volume": self._safe_int(record.get("unadjustedVolume")),
                "change": self._safe_float(record.get("change")),
                "change_percent": self._safe_float(record.get("changePercent")),
                "vwap": self._safe_float(record.get("vwap")),
            })

        return prices

    async def get_market_cap(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current market capitalization

        Args:
            symbol: Stock symbol

        Returns:
            Market cap data
        """
        data = await self._make_request(f"market-capitalization/{symbol}")
        if not data or not isinstance(data, list) or not data:
            return None
        return data[0]


# Global FMP client instance
financial_modeling_prep_client = FinancialModelingPrepClient()
