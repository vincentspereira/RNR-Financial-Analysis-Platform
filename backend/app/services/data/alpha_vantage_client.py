"""
Alpha Vantage API client for financial data ingestion
"""
import asyncio
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import json

import aiohttp
from requests_ratelimiter import LimiterSession

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.services.data.alpha_vantage")


class AlphaVantageClient:
    """
    Alpha Vantage API client for financial data
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Alpha Vantage client
        
        Args:
            api_key: Alpha Vantage API key
        """
        self.api_key = api_key or getattr(settings, 'ALPHA_VANTAGE_API_KEY', 'demo')
        self.base_url = "https://www.alphavantage.co/query"
        self.session = None
        
        # Rate limiting: 5 requests per minute for free tier
        self.rate_limiter = LimiterSession(per_minute=5)
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Make API request to Alpha Vantage
        
        Args:
            params: Request parameters
            
        Returns:
            API response data or None if failed
        """
        params['apikey'] = self.api_key
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check for API errors
                    if 'Error Message' in data:
                        logger.warning("Alpha Vantage API error: %s", data['Error Message'])
                        return None
                    
                    if 'Note' in data:
                        logger.warning("Alpha Vantage API note: %s", data['Note'])
                        return None
                    
                    return data
                else:
                    logger.error("Alpha Vantage API request failed with status: %s", response.status)
                    return None
                    
        except Exception as e:
            logger.error("Alpha Vantage API request error: %s", e, exc_info=True)
            return None
    
    async def get_company_overview(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get company overview data
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Company overview data
        """
        params = {
            'function': 'OVERVIEW',
            'symbol': symbol
        }
        
        data = await self._make_request(params)
        if not data:
            return None
        
        # Transform data to our format
        try:
            return {
                'symbol': data.get('Symbol'),
                'name': data.get('Name'),
                'description': data.get('Description'),
                'cik': data.get('CIK'),
                'exchange': data.get('Exchange'),
                'currency': data.get('Currency'),
                'country': data.get('Country'),
                'sector': data.get('Sector'),
                'industry': data.get('Industry'),
                'address': data.get('Address'),
                'fiscal_year_end': data.get('FiscalYearEnd'),
                'latest_quarter': data.get('LatestQuarter'),
                'market_cap': self._safe_float(data.get('MarketCapitalization')),
                'ebitda': self._safe_float(data.get('EBITDA')),
                'pe_ratio': self._safe_float(data.get('PERatio')),
                'peg_ratio': self._safe_float(data.get('PEGRatio')),
                'book_value': self._safe_float(data.get('BookValue')),
                'dividend_per_share': self._safe_float(data.get('DividendPerShare')),
                'dividend_yield': self._safe_float(data.get('DividendYield')),
                'eps': self._safe_float(data.get('EPS')),
                'revenue_per_share_ttm': self._safe_float(data.get('RevenuePerShareTTM')),
                'profit_margin': self._safe_float(data.get('ProfitMargin')),
                'operating_margin_ttm': self._safe_float(data.get('OperatingMarginTTM')),
                'return_on_assets_ttm': self._safe_float(data.get('ReturnOnAssetsTTM')),
                'return_on_equity_ttm': self._safe_float(data.get('ReturnOnEquityTTM')),
                'revenue_ttm': self._safe_float(data.get('RevenueTTM')),
                'gross_profit_ttm': self._safe_float(data.get('GrossProfitTTM')),
                'diluted_eps_ttm': self._safe_float(data.get('DilutedEPSTTM')),
                'quarterly_earnings_growth_yoy': self._safe_float(data.get('QuarterlyEarningsGrowthYOY')),
                'quarterly_revenue_growth_yoy': self._safe_float(data.get('QuarterlyRevenueGrowthYOY')),
                'analyst_target_price': self._safe_float(data.get('AnalystTargetPrice')),
                'trailing_pe': self._safe_float(data.get('TrailingPE')),
                'forward_pe': self._safe_float(data.get('ForwardPE')),
                'price_to_sales_ratio_ttm': self._safe_float(data.get('PriceToSalesRatioTTM')),
                'price_to_book_ratio': self._safe_float(data.get('PriceToBookRatio')),
                'ev_to_revenue': self._safe_float(data.get('EVToRevenue')),
                'ev_to_ebitda': self._safe_float(data.get('EVToEBITDA')),
                'beta': self._safe_float(data.get('Beta')),
                '52_week_high': self._safe_float(data.get('52WeekHigh')),
                '52_week_low': self._safe_float(data.get('52WeekLow')),
                '50_day_moving_average': self._safe_float(data.get('50DayMovingAverage')),
                '200_day_moving_average': self._safe_float(data.get('200DayMovingAverage')),
                'shares_outstanding': self._safe_float(data.get('SharesOutstanding')),
                'dividend_date': data.get('DividendDate'),
                'ex_dividend_date': data.get('ExDividendDate'),
            }
        except Exception as e:
            logger.error("Error transforming company overview data: %s", e, exc_info=True)
            return None
    
    async def get_income_statement(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get annual income statements
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of annual income statements
        """
        params = {
            'function': 'INCOME_STATEMENT',
            'symbol': symbol
        }
        
        data = await self._make_request(params)
        if not data or 'annualReports' not in data:
            return None
        
        statements = []
        for report in data['annualReports']:
            try:
                statement = {
                    'fiscal_date_ending': report.get('fiscalDateEnding'),
                    'reported_currency': report.get('reportedCurrency'),
                    'gross_profit': self._safe_float(report.get('grossProfit')),
                    'total_revenue': self._safe_float(report.get('totalRevenue')),
                    'cost_of_revenue': self._safe_float(report.get('costOfRevenue')),
                    'cost_of_goods_and_services_sold': self._safe_float(report.get('costofGoodsAndServicesSold')),
                    'operating_income': self._safe_float(report.get('operatingIncome')),
                    'selling_general_administrative': self._safe_float(report.get('sellingGeneralAndAdministrative')),
                    'research_and_development': self._safe_float(report.get('researchAndDevelopment')),
                    'operating_expenses': self._safe_float(report.get('operatingExpenses')),
                    'investment_income_net': self._safe_float(report.get('investmentIncomeNet')),
                    'net_interest_income': self._safe_float(report.get('netInterestIncome')),
                    'interest_income': self._safe_float(report.get('interestIncome')),
                    'interest_expense': self._safe_float(report.get('interestExpense')),
                    'non_interest_income': self._safe_float(report.get('nonInterestIncome')),
                    'other_non_operating_income': self._safe_float(report.get('otherNonOperatingIncome')),
                    'depreciation': self._safe_float(report.get('depreciation')),
                    'depreciation_and_amortization': self._safe_float(report.get('depreciationAndAmortization')),
                    'income_before_tax': self._safe_float(report.get('incomeBeforeTax')),
                    'income_tax_expense': self._safe_float(report.get('incomeTaxExpense')),
                    'interest_and_debt_expense': self._safe_float(report.get('interestAndDebtExpense')),
                    'net_income_from_continuing_operations': self._safe_float(report.get('netIncomeFromContinuingOperations')),
                    'comprehensive_income_net_of_tax': self._safe_float(report.get('comprehensiveIncomeNetOfTax')),
                    'ebit': self._safe_float(report.get('ebit')),
                    'ebitda': self._safe_float(report.get('ebitda')),
                    'net_income': self._safe_float(report.get('netIncome')),
                }
                statements.append(statement)
            except Exception as e:
                logger.error("Error processing income statement: %s", e, exc_info=True)
                continue
        
        return statements
    
    async def get_balance_sheet(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get annual balance sheets
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of annual balance sheets
        """
        params = {
            'function': 'BALANCE_SHEET',
            'symbol': symbol
        }
        
        data = await self._make_request(params)
        if not data or 'annualReports' not in data:
            return None
        
        balance_sheets = []
        for report in data['annualReports']:
            try:
                balance_sheet = {
                    'fiscal_date_ending': report.get('fiscalDateEnding'),
                    'reported_currency': report.get('reportedCurrency'),
                    'total_assets': self._safe_float(report.get('totalAssets')),
                    'total_current_assets': self._safe_float(report.get('totalCurrentAssets')),
                    'cash_and_cash_equivalents_at_carrying_value': self._safe_float(report.get('cashAndCashEquivalentsAtCarryingValue')),
                    'cash_and_short_term_investments': self._safe_float(report.get('cashAndShortTermInvestments')),
                    'inventory': self._safe_float(report.get('inventory')),
                    'current_net_receivables': self._safe_float(report.get('currentNetReceivables')),
                    'total_non_current_assets': self._safe_float(report.get('totalNonCurrentAssets')),
                    'property_plant_equipment': self._safe_float(report.get('propertyPlantEquipment')),
                    'accumulated_depreciation_amortization_ppe': self._safe_float(report.get('accumulatedDepreciationAmortizationPPE')),
                    'intangible_assets': self._safe_float(report.get('intangibleAssets')),
                    'intangible_assets_excluding_goodwill': self._safe_float(report.get('intangibleAssetsExcludingGoodwill')),
                    'goodwill': self._safe_float(report.get('goodwill')),
                    'investments': self._safe_float(report.get('investments')),
                    'long_term_investments': self._safe_float(report.get('longTermInvestments')),
                    'short_term_investments': self._safe_float(report.get('shortTermInvestments')),
                    'other_current_assets': self._safe_float(report.get('otherCurrentAssets')),
                    'other_non_current_assets': self._safe_float(report.get('otherNonCurrentAssets')),
                    'total_liabilities': self._safe_float(report.get('totalLiabilities')),
                    'total_current_liabilities': self._safe_float(report.get('totalCurrentLiabilities')),
                    'current_accounts_payable': self._safe_float(report.get('currentAccountsPayable')),
                    'deferred_revenue': self._safe_float(report.get('deferredRevenue')),
                    'current_debt': self._safe_float(report.get('currentDebt')),
                    'short_term_debt': self._safe_float(report.get('shortTermDebt')),
                    'total_non_current_liabilities': self._safe_float(report.get('totalNonCurrentLiabilities')),
                    'capital_lease_obligations': self._safe_float(report.get('capitalLeaseObligations')),
                    'long_term_debt': self._safe_float(report.get('longTermDebt')),
                    'current_long_term_debt': self._safe_float(report.get('currentLongTermDebt')),
                    'long_term_debt_noncurrent': self._safe_float(report.get('longTermDebtNoncurrent')),
                    'short_long_term_debt_total': self._safe_float(report.get('shortLongTermDebtTotal')),
                    'other_current_liabilities': self._safe_float(report.get('otherCurrentLiabilities')),
                    'other_non_current_liabilities': self._safe_float(report.get('otherNonCurrentLiabilities')),
                    'total_shareholder_equity': self._safe_float(report.get('totalShareholderEquity')),
                    'treasury_stock': self._safe_float(report.get('treasuryStock')),
                    'retained_earnings': self._safe_float(report.get('retainedEarnings')),
                    'common_stock': self._safe_float(report.get('commonStock')),
                    'common_stock_shares_outstanding': self._safe_float(report.get('commonStockSharesOutstanding')),
                }
                balance_sheets.append(balance_sheet)
            except Exception as e:
                logger.error("Error processing balance sheet: %s", e, exc_info=True)
                continue
        
        return balance_sheets
    
    async def get_cash_flow(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get annual cash flow statements
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of annual cash flow statements
        """
        params = {
            'function': 'CASH_FLOW',
            'symbol': symbol
        }
        
        data = await self._make_request(params)
        if not data or 'annualReports' not in data:
            return None
        
        cash_flows = []
        for report in data['annualReports']:
            try:
                cash_flow = {
                    'fiscal_date_ending': report.get('fiscalDateEnding'),
                    'reported_currency': report.get('reportedCurrency'),
                    'operating_cashflow': self._safe_float(report.get('operatingCashflow')),
                    'payments_for_operating_activities': self._safe_float(report.get('paymentsForOperatingActivities')),
                    'proceeds_from_operating_activities': self._safe_float(report.get('proceedsFromOperatingActivities')),
                    'change_in_operating_liabilities': self._safe_float(report.get('changeInOperatingLiabilities')),
                    'change_in_operating_assets': self._safe_float(report.get('changeInOperatingAssets')),
                    'depreciation_depletion_amortization': self._safe_float(report.get('depreciationDepletionAndAmortization')),
                    'capital_expenditures': self._safe_float(report.get('capitalExpenditures')),
                    'change_in_receivables': self._safe_float(report.get('changeInReceivables')),
                    'change_in_inventory': self._safe_float(report.get('changeInInventory')),
                    'profit_loss': self._safe_float(report.get('profitLoss')),
                    'cashflow_from_investment': self._safe_float(report.get('cashflowFromInvestment')),
                    'cashflow_from_financing': self._safe_float(report.get('cashflowFromFinancing')),
                    'proceeds_from_repayments_of_short_term_debt': self._safe_float(report.get('proceedsFromRepaymentsOfShortTermDebt')),
                    'payments_for_repurchase_of_common_stock': self._safe_float(report.get('paymentsForRepurchaseOfCommonStock')),
                    'payments_for_repurchase_of_equity': self._safe_float(report.get('paymentsForRepurchaseOfEquity')),
                    'payments_for_repurchase_of_preferred_stock': self._safe_float(report.get('paymentsForRepurchaseOfPreferredStock')),
                    'dividend_payout': self._safe_float(report.get('dividendPayout')),
                    'dividend_payout_common_stock': self._safe_float(report.get('dividendPayoutCommonStock')),
                    'dividend_payout_preferred_stock': self._safe_float(report.get('dividendPayoutPreferredStock')),
                    'proceeds_from_issuance_of_common_stock': self._safe_float(report.get('proceedsFromIssuanceOfCommonStock')),
                    'proceeds_from_issuance_of_long_term_debt_and_capital_securities_net': self._safe_float(report.get('proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet')),
                    'proceeds_from_issuance_of_preferred_stock': self._safe_float(report.get('proceedsFromIssuanceOfPreferredStock')),
                    'proceeds_from_repurchase_of_equity': self._safe_float(report.get('proceedsFromRepurchaseOfEquity')),
                    'proceeds_from_sale_of_treasury_stock': self._safe_float(report.get('proceedsFromSaleOfTreasuryStock')),
                    'change_in_cash_and_cash_equivalents': self._safe_float(report.get('changeInCashAndCashEquivalents')),
                    'change_in_exchange_rate': self._safe_float(report.get('changeInExchangeRate')),
                    'net_income': self._safe_float(report.get('netIncome')),
                }
                cash_flows.append(cash_flow)
            except Exception as e:
                logger.error("Error processing cash flow: %s", e, exc_info=True)
                continue
        
        return cash_flows
    
    async def get_daily_prices(self, symbol: str, outputsize: str = 'compact') -> Optional[Dict[str, Any]]:
        """
        Get daily price data
        
        Args:
            symbol: Stock symbol
            outputsize: 'compact' (100 days) or 'full' (20+ years)
            
        Returns:
            Daily price data
        """
        params = {
            'function': 'TIME_SERIES_DAILY_ADJUSTED',
            'symbol': symbol,
            'outputsize': outputsize
        }
        
        data = await self._make_request(params)
        if not data or 'Time Series (Daily)' not in data:
            return None
        
        time_series = data['Time Series (Daily)']
        prices = []
        
        for date_str, price_data in time_series.items():
            try:
                price_record = {
                    'date': date_str,
                    'open': self._safe_float(price_data.get('1. open')),
                    'high': self._safe_float(price_data.get('2. high')),
                    'low': self._safe_float(price_data.get('3. low')),
                    'close': self._safe_float(price_data.get('4. close')),
                    'adjusted_close': self._safe_float(price_data.get('5. adjusted close')),
                    'volume': self._safe_int(price_data.get('6. volume')),
                    'dividend_amount': self._safe_float(price_data.get('7. dividend amount')),
                    'split_coefficient': self._safe_float(price_data.get('8. split coefficient')),
                }
                prices.append(price_record)
            except Exception as e:
                logger.error("Error processing price data for %s: %s", date_str, e, exc_info=True)
                continue
        
        return {
            'symbol': symbol,
            'metadata': data.get('Meta Data', {}),
            'prices': prices
        }
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None or value == 'None' or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int"""
        if value is None or value == 'None' or value == '':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None


# Global Alpha Vantage client instance
alpha_vantage_client = AlphaVantageClient()