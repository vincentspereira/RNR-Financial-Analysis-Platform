"""
SEC EDGAR API client for financial data ingestion

Uses the SEC EDGAR full-text search and company filings APIs.
No API key required, but requires a proper User-Agent header per SEC policy.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

import aiohttp

from app.core.logging import get_logger

logger = get_logger("app.services.data.sec_edgar")

SEC_EDGAR_BASE_URL = "https://efts.sec.gov/LATEST/search-index?q=%3F"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/{cik}.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

# Required by SEC policy - identifies the requesting application
USER_AGENT = "Financial Analysis Platform (contact@example.com)"


class SecEdgarClient:
    """
    SEC EDGAR client for company filings and XBRL financial data
    """

    def __init__(self, user_agent: Optional[str] = None):
        self.user_agent = user_agent or USER_AGENT
        self.session = None
        self._ticker_cache: Optional[Dict[str, str]] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _make_request(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
                )
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                logger.error("SEC EDGAR request failed with status %s for %s", response.status, url)
                return None
        except Exception as e:
            logger.error("SEC EDGAR request error: %s", e, exc_info=True)
            return None

    async def _get_cik(self, symbol: str) -> Optional[str]:
        """Look up CIK number for a ticker symbol"""
        if self._ticker_cache is None:
            data = await self._make_request(SEC_COMPANY_TICKERS_URL)
            if not data:
                return None
            self._ticker_cache = {}
            for entry in data.values():
                ticker = entry.get("ticker", "").upper()
                cik = str(entry.get("cik_str", "")).zfill(10)
                self._ticker_cache[ticker] = cik

        return self._ticker_cache.get(symbol.upper())

    async def get_company_facts(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get XBRL company facts (financial data) from SEC EDGAR

        Args:
            symbol: Stock ticker symbol

        Returns:
            Company facts data including financials by concept
        """
        cik = await self._get_cik(symbol)
        if not cik:
            return None

        url = SEC_COMPANY_FACTS_URL.format(cik=cik)
        data = await self._make_request(url)
        if not data:
            return None

        us_gaap = data.get("facts", {}).get("us-gaap", {})
        result = {"symbol": symbol, "cik": cik, "entity_name": data.get("entityName", ""), "facts": {}}

        key_concepts = {
            "Revenues": "revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue_from_contract",
            "CostOfRevenue": "cost_of_revenue",
            "GrossProfit": "gross_profit",
            "OperatingIncomeLoss": "operating_income",
            "NetIncomeLoss": "net_income",
            "NetIncomeLossAttributableToCommonStockholdersBasic": "net_income_to_common",
            "EarningsPerShareBasic": "eps_basic",
            "EarningsPerShareDiluted": "eps_diluted",
            "TotalAssets": "total_assets",
            "TotalLiabilities": "total_liabilities",
            "StockholdersEquity": "stockholders_equity",
            "CashAndCashEquivalentsAtCarryingValue": "cash_and_equivalents",
            "InventoryNet": "inventory",
            "PropertyPlantAndEquipmentNet": "ppe_net",
            "Goodwill": "goodwill",
            "LongTermDebt": "long_term_debt",
            "ShortTermBorrowings": "short_term_debt",
            "OperatingCashFlow": "operating_cash_flow" if "OperatingCashFlow" in us_gaap else None,
            "CashFlowFromOperatingActivities": "operating_cash_flow",
            "CashFlowFromInvestingActivities": "investing_cash_flow",
            "CashFlowFromFinancingActivities": "financing_cash_flow",
            "CommonStockSharesOutstanding": "shares_outstanding",
            "WeightedAverageNumberOfSharesOutstandingBasic": "weighted_avg_shares_basic",
            "WeightedAverageNumberOfDilutedSharesOutstanding": "weighted_avg_shares_diluted",
            "DividendsPaid": "dividends_paid",
            "ResearchAndDevelopmentExpense": "rd_expense",
            "SellingGeneralAndAdministrativeExpense": "sga_expense",
            "InterestExpense": "interest_expense",
            "IncomeTaxExpenseBenefit": "income_tax_expense",
        }

        for concept, alias in key_concepts.items():
            if concept in us_gaap:
                units = us_gaap[concept].get("units", {})
                for unit_key, entries in units.items():
                    annual = [e for e in entries if e.get("form") == "10-K"]
                    if annual:
                        result["facts"][alias] = [
                            {
                                "value": e.get("val"),
                                "fiscal_year": e.get("fy"),
                                "fiscal_period": e.get("fp"),
                                "filed": e.get("filed"),
                                "form": e.get("form"),
                            }
                            for e in annual
                        ]

        return result

    async def get_company_submissions(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get recent SEC filings/submissions for a company

        Args:
            symbol: Stock ticker symbol

        Returns:
            Recent filings data
        """
        cik = await self._get_cik(symbol)
        if not cik:
            return None

        url = SEC_SUBMISSIONS_URL.format(cik=cik)
        data = await self._make_request(url)
        if not data:
            return None

        recent = data.get("filings", {}).get("recent", {})
        result = {
            "symbol": symbol,
            "cik": cik,
            "name": data.get("name", ""),
            "sic": data.get("sic", ""),
            "sic_description": data.get("sicDescription", ""),
            "tickers": data.get("tickers", []),
            "exchanges": data.get("exchanges", []),
            "ein": data.get("ein", ""),
            "state_of_incorporation": data.get("stateOfIncorporation", ""),
            "filings": [],
        }

        filing_types = ["10-K", "10-Q", "8-K", "DEF 14A", "20-F"]
        accessions = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        forms = recent.get("form", [])
        primary_docs = recent.get("primaryDocument", [])

        for i in range(min(len(accessions), 50)):
            if forms[i] in filing_types if i < len(forms) else False:
                accession = accessions[i].replace("-", "")
                result["filings"].append({
                    "accession_number": accessions[i],
                    "filing_date": filing_dates[i] if i < len(filing_dates) else None,
                    "form": forms[i] if i < len(forms) else None,
                    "primary_document": primary_docs[i] if i < len(primary_docs) else None,
                    "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/",
                })

        return result

    async def get_income_statements(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get annual income statement data from SEC EDGAR XBRL

        Args:
            symbol: Stock ticker symbol

        Returns:
            List of annual income statement dicts
        """
        facts = await self.get_company_facts(symbol)
        if not facts:
            return None

        income_concepts = [
            "revenues", "cost_of_revenue", "gross_profit",
            "operating_income", "net_income", "eps_basic", "eps_diluted",
            "rd_expense", "sga_expense", "interest_expense", "income_tax_expense",
        ]

        years = set()
        for concept in income_concepts:
            for entry in facts.get("facts", {}).get(concept, []):
                fy = entry.get("fiscal_year")
                if fy:
                    years.add(fy)

        statements = []
        for year in sorted(years, reverse=True):
            stmt = {"fiscal_year": year}
            for concept in income_concepts:
                for entry in facts.get("facts", {}).get(concept, []):
                    if entry.get("fiscal_year") == year and entry.get("fiscal_period") == "FY":
                        stmt[concept] = entry.get("value")
                        break
            stmt["fiscal_date_ending"] = f"{year}-12-31"
            statements.append(stmt)

        return statements if statements else None

    async def get_balance_sheets(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get annual balance sheet data from SEC EDGAR XBRL

        Args:
            symbol: Stock ticker symbol

        Returns:
            List of annual balance sheet dicts
        """
        facts = await self.get_company_facts(symbol)
        if not facts:
            return None

        bs_concepts = [
            "total_assets", "total_liabilities", "stockholders_equity",
            "cash_and_equivalents", "inventory", "ppe_net", "goodwill",
            "long_term_debt", "short_term_debt",
        ]

        years = set()
        for concept in bs_concepts:
            for entry in facts.get("facts", {}).get(concept, []):
                fy = entry.get("fiscal_year")
                if fy:
                    years.add(fy)

        sheets = []
        for year in sorted(years, reverse=True):
            sheet = {"fiscal_year": year}
            for concept in bs_concepts:
                for entry in facts.get("facts", {}).get(concept, []):
                    if entry.get("fiscal_year") == year and entry.get("fiscal_period") == "FY":
                        sheet[concept] = entry.get("value")
                        break
            sheet["fiscal_date_ending"] = f"{year}-12-31"
            sheets.append(sheet)

        return sheets if sheets else None

    async def get_company_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get company overview from SEC EDGAR submissions

        Args:
            symbol: Stock ticker symbol

        Returns:
            Company info dict
        """
        sub = await self.get_company_submissions(symbol)
        if not sub:
            return None

        return {
            "symbol": symbol,
            "cik": sub.get("cik"),
            "name": sub.get("name"),
            "sic": sub.get("sic"),
            "sic_description": sub.get("sic_description"),
            "exchanges": sub.get("exchanges"),
            "ein": sub.get("ein"),
            "state_of_incorporation": sub.get("state_of_incorporation"),
        }


# Global SEC EDGAR client instance
sec_edgar_client = SecEdgarClient()
