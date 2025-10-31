"""
Yahoo Finance client for market data ingestion
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

import yfinance as yf
import pandas as pd


class YahooFinanceClient:
    """
    Yahoo Finance client for market data
    """
    
    def __init__(self):
        """Initialize Yahoo Finance client"""
        self.session = None
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive stock information
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Stock information dictionary
        """
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
            info = await loop.run_in_executor(None, lambda: ticker.info)
            
            if not info:
                return None
            
            # Transform to our format
            return {
                'symbol': info.get('symbol'),
                'short_name': info.get('shortName'),
                'long_name': info.get('longName'),
                'exchange': info.get('exchange'),
                'currency': info.get('currency'),
                'country': info.get('country'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'website': info.get('website'),
                'business_summary': info.get('businessSummary'),
                'full_time_employees': info.get('fullTimeEmployees'),
                'market_cap': info.get('marketCap'),
                'enterprise_value': info.get('enterpriseValue'),
                'shares_outstanding': info.get('sharesOutstanding'),
                'float_shares': info.get('floatShares'),
                'shares_short': info.get('sharesShort'),
                'shares_short_prior_month': info.get('sharesShortPriorMonth'),
                'shares_short_previous_month_date': info.get('sharesShortPreviousMonthDate'),
                'date_short_interest': info.get('dateShortInterest'),
                'shares_percent_shares_out': info.get('sharesPercentSharesOut'),
                'held_percent_insiders': info.get('heldPercentInsiders'),
                'held_percent_institutions': info.get('heldPercentInstitutions'),
                'short_ratio': info.get('shortRatio'),
                'short_percent_of_float': info.get('shortPercentOfFloat'),
                'beta': info.get('beta'),
                'price_hint': info.get('priceHint'),
                'previous_close': info.get('previousClose'),
                'open': info.get('open'),
                'day_low': info.get('dayLow'),
                'day_high': info.get('dayHigh'),
                'regular_market_previous_close': info.get('regularMarketPreviousClose'),
                'regular_market_open': info.get('regularMarketOpen'),
                'regular_market_day_low': info.get('regularMarketDayLow'),
                'regular_market_day_high': info.get('regularMarketDayHigh'),
                'dividend_rate': info.get('dividendRate'),
                'dividend_yield': info.get('dividendYield'),
                'ex_dividend_date': info.get('exDividendDate'),
                'payout_ratio': info.get('payoutRatio'),
                'five_year_avg_dividend_yield': info.get('fiveYearAvgDividendYield'),
                'beta': info.get('beta'),
                'trailing_pe': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'volume': info.get('volume'),
                'regular_market_volume': info.get('regularMarketVolume'),
                'average_volume': info.get('averageVolume'),
                'average_volume_10days': info.get('averageVolume10days'),
                'average_daily_volume_10day': info.get('averageDailyVolume10Day'),
                'bid': info.get('bid'),
                'ask': info.get('ask'),
                'bid_size': info.get('bidSize'),
                'ask_size': info.get('askSize'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'price_to_sales_trailing_12months': info.get('priceToSalesTrailing12Months'),
                'fifty_day_average': info.get('fiftyDayAverage'),
                'two_hundred_day_average': info.get('twoHundredDayAverage'),
                'trailing_annual_dividend_rate': info.get('trailingAnnualDividendRate'),
                'trailing_annual_dividend_yield': info.get('trailingAnnualDividendYield'),
                'enterprise_to_revenue': info.get('enterpriseToRevenue'),
                'enterprise_to_ebitda': info.get('enterpriseToEbitda'),
                'profit_margins': info.get('profitMargins'),
                'float_shares': info.get('floatShares'),
                'shares_outstanding': info.get('sharesOutstanding'),
                'book_value': info.get('bookValue'),
                'price_to_book': info.get('priceToBook'),
                'last_fiscal_year_end': info.get('lastFiscalYearEnd'),
                'next_fiscal_year_end': info.get('nextFiscalYearEnd'),
                'most_recent_quarter': info.get('mostRecentQuarter'),
                'earnings_quarterly_growth': info.get('earningsQuarterlyGrowth'),
                'net_income_to_common': info.get('netIncomeToCommon'),
                'trailing_eps': info.get('trailingEps'),
                'forward_eps': info.get('forwardEps'),
                'peg_ratio': info.get('pegRatio'),
                'last_split_factor': info.get('lastSplitFactor'),
                'last_split_date': info.get('lastSplitDate'),
                'earnings_growth': info.get('earningsGrowth'),
                'revenue_growth': info.get('revenueGrowth'),
                'gross_margins': info.get('grossMargins'),
                'ebitda_margins': info.get('ebitdaMargins'),
                'operating_margins': info.get('operatingMargins'),
                'financial_currency': info.get('financialCurrency'),
                'total_cash': info.get('totalCash'),
                'total_cash_per_share': info.get('totalCashPerShare'),
                'ebitda': info.get('ebitda'),
                'total_debt': info.get('totalDebt'),
                'quick_ratio': info.get('quickRatio'),
                'current_ratio': info.get('currentRatio'),
                'total_revenue': info.get('totalRevenue'),
                'debt_to_equity': info.get('debtToEquity'),
                'revenue_per_share': info.get('revenuePerShare'),
                'return_on_assets': info.get('returnOnAssets'),
                'return_on_equity': info.get('returnOnEquity'),
                'gross_profits': info.get('grossProfits'),
                'free_cashflow': info.get('freeCashflow'),
                'operating_cashflow': info.get('operatingCashflow'),
                'earnings_growth': info.get('earningsGrowth'),
                'revenue_growth': info.get('revenueGrowth'),
                'gross_margins': info.get('grossMargins'),
                'ebitda_margins': info.get('ebitdaMargins'),
                'operating_margins': info.get('operatingMargins'),
                'recommendation_mean': info.get('recommendationMean'),
                'recommendation_key': info.get('recommendationKey'),
                'number_of_analyst_opinions': info.get('numberOfAnalystOpinions'),
                'target_high_price': info.get('targetHighPrice'),
                'target_low_price': info.get('targetLowPrice'),
                'target_mean_price': info.get('targetMeanPrice'),
                'target_median_price': info.get('targetMedianPrice'),
            }
            
        except Exception as e:
            print(f"Error getting Yahoo Finance stock info for {symbol}: {e}")
            return None
    
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical price data
        
        Args:
            symbol: Stock symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            List of historical price records
        """
        try:
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
            hist = await loop.run_in_executor(
                None, 
                lambda: ticker.history(period=period, interval=interval)
            )
            
            if hist.empty:
                return None
            
            # Convert to list of dictionaries
            records = []
            for date, row in hist.iterrows():
                record = {
                    'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    'open': float(row['Open']) if pd.notna(row['Open']) else None,
                    'high': float(row['High']) if pd.notna(row['High']) else None,
                    'low': float(row['Low']) if pd.notna(row['Low']) else None,
                    'close': float(row['Close']) if pd.notna(row['Close']) else None,
                    'volume': int(row['Volume']) if pd.notna(row['Volume']) else None,
                }
                
                # Add dividends and stock splits if available
                if 'Dividends' in row and pd.notna(row['Dividends']):
                    record['dividends'] = float(row['Dividends'])
                
                if 'Stock Splits' in row and pd.notna(row['Stock Splits']):
                    record['stock_splits'] = float(row['Stock Splits'])
                
                records.append(record)
            
            return records
            
        except Exception as e:
            print(f"Error getting historical data for {symbol}: {e}")
            return None
    
    async def get_financials(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get financial statements from Yahoo Finance
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Financial statements data
        """
        try:
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
            
            # Get financial statements
            financials = await loop.run_in_executor(None, lambda: ticker.financials)
            balance_sheet = await loop.run_in_executor(None, lambda: ticker.balance_sheet)
            cashflow = await loop.run_in_executor(None, lambda: ticker.cashflow)
            
            result = {}
            
            # Process income statement
            if not financials.empty:
                income_statements = []
                for date, data in financials.items():
                    statement = {
                        'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                        'total_revenue': self._safe_float(data.get('Total Revenue')),
                        'cost_of_revenue': self._safe_float(data.get('Cost Of Revenue')),
                        'gross_profit': self._safe_float(data.get('Gross Profit')),
                        'operating_expense': self._safe_float(data.get('Operating Expense')),
                        'operating_income': self._safe_float(data.get('Operating Income')),
                        'net_non_operating_interest_income_expense': self._safe_float(data.get('Net Non Operating Interest Income Expense')),
                        'other_income_expense': self._safe_float(data.get('Other Income Expense')),
                        'pretax_income': self._safe_float(data.get('Pretax Income')),
                        'tax_provision': self._safe_float(data.get('Tax Provision')),
                        'net_income_common_stockholders': self._safe_float(data.get('Net Income Common Stockholders')),
                        'diluted_ni_available_to_com_stockholders': self._safe_float(data.get('Diluted NI Available to Com Stockholders')),
                        'basic_eps': self._safe_float(data.get('Basic EPS')),
                        'diluted_eps': self._safe_float(data.get('Diluted EPS')),
                        'basic_average_shares': self._safe_float(data.get('Basic Average Shares')),
                        'diluted_average_shares': self._safe_float(data.get('Diluted Average Shares')),
                        'total_operating_income_as_reported': self._safe_float(data.get('Total Operating Income As Reported')),
                        'total_expenses': self._safe_float(data.get('Total Expenses')),
                        'net_income_from_continuing_and_discontinued_operation': self._safe_float(data.get('Net Income From Continuing And Discontinued Operation')),
                        'normalized_income': self._safe_float(data.get('Normalized Income')),
                        'interest_income': self._safe_float(data.get('Interest Income')),
                        'interest_expense': self._safe_float(data.get('Interest Expense')),
                        'net_interest_income': self._safe_float(data.get('Net Interest Income')),
                        'ebit': self._safe_float(data.get('EBIT')),
                        'ebitda': self._safe_float(data.get('EBITDA')),
                        'reconciled_cost_of_revenue': self._safe_float(data.get('Reconciled Cost Of Revenue')),
                        'reconciled_depreciation': self._safe_float(data.get('Reconciled Depreciation')),
                        'net_income_including_noncontrolling_interests': self._safe_float(data.get('Net Income Including Noncontrolling Interests')),
                        'net_income_continuous_operations': self._safe_float(data.get('Net Income Continuous Operations')),
                        'tax_rate_for_calcs': self._safe_float(data.get('Tax Rate For Calcs')),
                        'tax_effect_of_unusual_items': self._safe_float(data.get('Tax Effect Of Unusual Items')),
                    }
                    income_statements.append(statement)
                result['income_statements'] = income_statements
            
            # Process balance sheet
            if not balance_sheet.empty:
                balance_sheets = []
                for date, data in balance_sheet.items():
                    bs = {
                        'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                        'total_assets': self._safe_float(data.get('Total Assets')),
                        'current_assets': self._safe_float(data.get('Current Assets')),
                        'cash_cash_equivalents_and_short_term_investments': self._safe_float(data.get('Cash Cash Equivalents And Short Term Investments')),
                        'cash_and_cash_equivalents': self._safe_float(data.get('Cash And Cash Equivalents')),
                        'other_short_term_investments': self._safe_float(data.get('Other Short Term Investments')),
                        'receivables': self._safe_float(data.get('Receivables')),
                        'inventory': self._safe_float(data.get('Inventory')),
                        'other_current_assets': self._safe_float(data.get('Other Current Assets')),
                        'total_non_current_assets': self._safe_float(data.get('Total Non Current Assets')),
                        'net_ppe': self._safe_float(data.get('Net PPE')),
                        'accumulated_depreciation': self._safe_float(data.get('Accumulated Depreciation')),
                        'gross_ppe': self._safe_float(data.get('Gross PPE')),
                        'goodwill': self._safe_float(data.get('Goodwill')),
                        'other_intangible_assets': self._safe_float(data.get('Other Intangible Assets')),
                        'investments_and_advances': self._safe_float(data.get('Investments And Advances')),
                        'other_non_current_assets': self._safe_float(data.get('Other Non Current Assets')),
                        'total_liabilities_net_minority_interest': self._safe_float(data.get('Total Liabilities Net Minority Interest')),
                        'current_liabilities': self._safe_float(data.get('Current Liabilities')),
                        'payables_and_accrued_expenses': self._safe_float(data.get('Payables And Accrued Expenses')),
                        'payables': self._safe_float(data.get('Payables')),
                        'current_debt_and_capital_lease_obligation': self._safe_float(data.get('Current Debt And Capital Lease Obligation')),
                        'current_debt': self._safe_float(data.get('Current Debt')),
                        'other_current_liabilities': self._safe_float(data.get('Other Current Liabilities')),
                        'total_non_current_liabilities_net_minority_interest': self._safe_float(data.get('Total Non Current Liabilities Net Minority Interest')),
                        'long_term_debt_and_capital_lease_obligation': self._safe_float(data.get('Long Term Debt And Capital Lease Obligation')),
                        'long_term_debt': self._safe_float(data.get('Long Term Debt')),
                        'other_non_current_liabilities': self._safe_float(data.get('Other Non Current Liabilities')),
                        'total_equity_gross_minority_interest': self._safe_float(data.get('Total Equity Gross Minority Interest')),
                        'stockholders_equity': self._safe_float(data.get('Stockholders Equity')),
                        'common_stock_equity': self._safe_float(data.get('Common Stock Equity')),
                        'common_stock': self._safe_float(data.get('Common Stock')),
                        'retained_earnings': self._safe_float(data.get('Retained Earnings')),
                        'gains_losses_not_affecting_retained_earnings': self._safe_float(data.get('Gains Losses Not Affecting Retained Earnings')),
                        'treasury_shares_number': self._safe_float(data.get('Treasury Shares Number')),
                        'ordinary_shares_number': self._safe_float(data.get('Ordinary Shares Number')),
                    }
                    balance_sheets.append(bs)
                result['balance_sheets'] = balance_sheets
            
            # Process cash flow
            if not cashflow.empty:
                cash_flows = []
                for date, data in cashflow.items():
                    cf = {
                        'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                        'operating_cash_flow': self._safe_float(data.get('Operating Cash Flow')),
                        'investing_cash_flow': self._safe_float(data.get('Investing Cash Flow')),
                        'financing_cash_flow': self._safe_float(data.get('Financing Cash Flow')),
                        'end_cash_position': self._safe_float(data.get('End Cash Position')),
                        'capital_expenditure': self._safe_float(data.get('Capital Expenditure')),
                        'issuance_of_capital_stock': self._safe_float(data.get('Issuance Of Capital Stock')),
                        'issuance_of_debt': self._safe_float(data.get('Issuance Of Debt')),
                        'repayment_of_debt': self._safe_float(data.get('Repayment Of Debt')),
                        'repurchase_of_capital_stock': self._safe_float(data.get('Repurchase Of Capital Stock')),
                        'free_cash_flow': self._safe_float(data.get('Free Cash Flow')),
                    }
                    cash_flows.append(cf)
                result['cash_flows'] = cash_flows
            
            return result if result else None
            
        except Exception as e:
            print(f"Error getting financials for {symbol}: {e}")
            return None
    
    async def get_analyst_recommendations(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get analyst recommendations
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of analyst recommendations
        """
        try:
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
            recommendations = await loop.run_in_executor(None, lambda: ticker.recommendations)
            
            if recommendations is None or recommendations.empty:
                return None
            
            recs = []
            for date, data in recommendations.iterrows():
                rec = {
                    'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    'firm': data.get('Firm'),
                    'to_grade': data.get('To Grade'),
                    'from_grade': data.get('From Grade'),
                    'action': data.get('Action'),
                }
                recs.append(rec)
            
            return recs
            
        except Exception as e:
            print(f"Error getting analyst recommendations for {symbol}: {e}")
            return None
    
    async def get_earnings_calendar(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get earnings calendar
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Earnings calendar data
        """
        try:
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
            calendar = await loop.run_in_executor(None, lambda: ticker.calendar)
            
            if calendar is None or calendar.empty:
                return None
            
            # Convert to dictionary format
            result = {}
            for date, data in calendar.items():
                result[date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)] = {
                    'earnings_estimate': self._safe_float(data.get('Earnings Estimate')),
                    'revenue_estimate': self._safe_float(data.get('Revenue Estimate')),
                    'earnings_date': data.get('Earnings Date'),
                }
            
            return result
            
        except Exception as e:
            print(f"Error getting earnings calendar for {symbol}: {e}")
            return None
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


# Global Yahoo Finance client instance
yahoo_finance_client = YahooFinanceClient()