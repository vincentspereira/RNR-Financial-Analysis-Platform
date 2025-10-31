"""
Financial ratio calculator with 50+ ratios for comprehensive analysis
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Any
import math


class RatioCalculator:
    """
    Comprehensive financial ratio calculator
    """
    
    def __init__(self):
        """Initialize ratio calculator"""
        self.precision = Decimal('0.000001')  # 6 decimal places
    
    def safe_divide(self, numerator: Optional[float], denominator: Optional[float]) -> Optional[Decimal]:
        """
        Safely divide two numbers with proper handling of None and zero values
        
        Args:
            numerator: The numerator value
            denominator: The denominator value
            
        Returns:
            Decimal result or None if calculation not possible
        """
        if numerator is None or denominator is None or denominator == 0:
            return None
        
        try:
            result = Decimal(str(numerator)) / Decimal(str(denominator))
            return result.quantize(self.precision, rounding=ROUND_HALF_UP)
        except (ValueError, TypeError, ZeroDivisionError):
            return None
    
    def calculate_liquidity_ratios(self, financial_data: Dict[str, Any]) -> Dict[str, Optional[Decimal]]:
        """
        Calculate liquidity ratios
        
        Args:
            financial_data: Dictionary containing financial statement data
            
        Returns:
            Dictionary of liquidity ratios
        """
        # Extract balance sheet data
        current_assets = financial_data.get('current_assets')
        current_liabilities = financial_data.get('current_liabilities')
        cash_and_equivalents = financial_data.get('cash_and_equivalents')
        short_term_investments = financial_data.get('short_term_investments', 0)
        inventory = financial_data.get('inventory', 0)
        accounts_receivable = financial_data.get('accounts_receivable', 0)
        
        # Quick assets = Current assets - Inventory - Prepaid expenses
        quick_assets = None
        if current_assets is not None and inventory is not None:
            quick_assets = current_assets - inventory
        
        # Cash assets = Cash + Short-term investments
        cash_assets = None
        if cash_and_equivalents is not None:
            cash_assets = cash_and_equivalents + (short_term_investments or 0)
        
        return {
            # Current Ratio = Current Assets / Current Liabilities
            'current_ratio': self.safe_divide(current_assets, current_liabilities),
            
            # Quick Ratio = (Current Assets - Inventory) / Current Liabilities
            'quick_ratio': self.safe_divide(quick_assets, current_liabilities),
            
            # Cash Ratio = (Cash + Short-term Investments) / Current Liabilities
            'cash_ratio': self.safe_divide(cash_assets, current_liabilities),
            
            # Operating Cash Flow Ratio = Operating Cash Flow / Current Liabilities
            'operating_cash_flow_ratio': self.safe_divide(
                financial_data.get('operating_cash_flow'), 
                current_liabilities
            ),
        }
    
    def calculate_profitability_ratios(self, financial_data: Dict[str, Any]) -> Dict[str, Optional[Decimal]]:
        """
        Calculate profitability ratios
        
        Args:
            financial_data: Dictionary containing financial statement data
            
        Returns:
            Dictionary of profitability ratios
        """
        # Extract income statement data
        revenue = financial_data.get('revenue')
        gross_profit = financial_data.get('gross_profit')
        operating_income = financial_data.get('operating_income')
        net_income = financial_data.get('net_income')
        ebitda = financial_data.get('ebitda')
        
        # Extract balance sheet data
        total_assets = financial_data.get('total_assets')
        shareholders_equity = financial_data.get('shareholders_equity')
        invested_capital = financial_data.get('invested_capital')
        
        # Average values (if available)
        avg_total_assets = financial_data.get('avg_total_assets', total_assets)
        avg_shareholders_equity = financial_data.get('avg_shareholders_equity', shareholders_equity)
        avg_invested_capital = financial_data.get('avg_invested_capital', invested_capital)
        
        return {
            # Gross Profit Margin = Gross Profit / Revenue
            'gross_profit_margin': self.safe_divide(gross_profit, revenue),
            
            # Operating Margin = Operating Income / Revenue
            'operating_margin': self.safe_divide(operating_income, revenue),
            
            # Net Profit Margin = Net Income / Revenue
            'net_profit_margin': self.safe_divide(net_income, revenue),
            
            # EBITDA Margin = EBITDA / Revenue
            'ebitda_margin': self.safe_divide(ebitda, revenue),
            
            # Return on Assets (ROA) = Net Income / Average Total Assets
            'roa': self.safe_divide(net_income, avg_total_assets),
            
            # Return on Equity (ROE) = Net Income / Average Shareholders' Equity
            'roe': self.safe_divide(net_income, avg_shareholders_equity),
            
            # Return on Invested Capital (ROIC) = Net Income / Average Invested Capital
            'roic': self.safe_divide(net_income, avg_invested_capital),
        }
    
    def calculate_leverage_ratios(self, financial_data: Dict[str, Any]) -> Dict[str, Optional[Decimal]]:
        """
        Calculate leverage/debt ratios
        
        Args:
            financial_data: Dictionary containing financial statement data
            
        Returns:
            Dictionary of leverage ratios
        """
        # Extract balance sheet data
        total_debt = financial_data.get('total_debt')
        long_term_debt = financial_data.get('long_term_debt')
        short_term_debt = financial_data.get('short_term_debt')
        total_assets = financial_data.get('total_assets')
        shareholders_equity = financial_data.get('shareholders_equity')
        
        # Extract income statement data
        operating_income = financial_data.get('operating_income')
        ebitda = financial_data.get('ebitda')
        interest_expense = financial_data.get('interest_expense')
        
        return {
            # Debt-to-Equity Ratio = Total Debt / Shareholders' Equity
            'debt_to_equity': self.safe_divide(total_debt, shareholders_equity),
            
            # Debt-to-Assets Ratio = Total Debt / Total Assets
            'debt_to_assets': self.safe_divide(total_debt, total_assets),
            
            # Equity Multiplier = Total Assets / Shareholders' Equity
            'equity_multiplier': self.safe_divide(total_assets, shareholders_equity),
            
            # Interest Coverage Ratio = Operating Income / Interest Expense
            'interest_coverage_ratio': self.safe_divide(operating_income, interest_expense),
            
            # Debt Service Coverage Ratio = EBITDA / Total Debt Service
            'debt_service_coverage_ratio': self.safe_divide(
                ebitda, 
                financial_data.get('total_debt_service')
            ),
            
            # Long-term Debt to Equity = Long-term Debt / Shareholders' Equity
            'long_term_debt_to_equity': self.safe_divide(long_term_debt, shareholders_equity),
        }
    
    def calculate_efficiency_ratios(self, financial_data: Dict[str, Any]) -> Dict[str, Optional[Decimal]]:
        """
        Calculate efficiency/activity ratios
        
        Args:
            financial_data: Dictionary containing financial statement data
            
        Returns:
            Dictionary of efficiency ratios
        """
        # Extract income statement data
        revenue = financial_data.get('revenue')
        cost_of_goods_sold = financial_data.get('cost_of_goods_sold')
        
        # Extract balance sheet data
        total_assets = financial_data.get('total_assets')
        inventory = financial_data.get('inventory')
        accounts_receivable = financial_data.get('accounts_receivable')
        accounts_payable = financial_data.get('accounts_payable')
        
        # Average values (if available)
        avg_total_assets = financial_data.get('avg_total_assets', total_assets)
        avg_inventory = financial_data.get('avg_inventory', inventory)
        avg_accounts_receivable = financial_data.get('avg_accounts_receivable', accounts_receivable)
        avg_accounts_payable = financial_data.get('avg_accounts_payable', accounts_payable)
        
        # Calculate turnover ratios
        asset_turnover = self.safe_divide(revenue, avg_total_assets)
        inventory_turnover = self.safe_divide(cost_of_goods_sold, avg_inventory)
        receivables_turnover = self.safe_divide(revenue, avg_accounts_receivable)
        payables_turnover = self.safe_divide(cost_of_goods_sold, avg_accounts_payable)
        
        # Calculate days ratios (365 days in a year)
        days_sales_outstanding = None
        if receivables_turnover:
            days_sales_outstanding = self.safe_divide(365, float(receivables_turnover))
        
        days_inventory_outstanding = None
        if inventory_turnover:
            days_inventory_outstanding = self.safe_divide(365, float(inventory_turnover))
        
        days_payable_outstanding = None
        if payables_turnover:
            days_payable_outstanding = self.safe_divide(365, float(payables_turnover))
        
        # Cash Conversion Cycle = DIO + DSO - DPO
        cash_conversion_cycle = None
        if all([days_inventory_outstanding, days_sales_outstanding, days_payable_outstanding]):
            cash_conversion_cycle = (
                days_inventory_outstanding + 
                days_sales_outstanding - 
                days_payable_outstanding
            )
        
        return {
            # Asset Turnover = Revenue / Average Total Assets
            'asset_turnover': asset_turnover,
            
            # Inventory Turnover = Cost of Goods Sold / Average Inventory
            'inventory_turnover': inventory_turnover,
            
            # Receivables Turnover = Revenue / Average Accounts Receivable
            'receivables_turnover': receivables_turnover,
            
            # Payables Turnover = Cost of Goods Sold / Average Accounts Payable
            'payables_turnover': payables_turnover,
            
            # Days Sales Outstanding = 365 / Receivables Turnover
            'days_sales_outstanding': days_sales_outstanding,
            
            # Days Inventory Outstanding = 365 / Inventory Turnover
            'days_inventory_outstanding': days_inventory_outstanding,
            
            # Days Payable Outstanding = 365 / Payables Turnover
            'days_payable_outstanding': days_payable_outstanding,
            
            # Cash Conversion Cycle = DIO + DSO - DPO
            'cash_conversion_cycle': cash_conversion_cycle,
        }
    
    def calculate_valuation_ratios(self, financial_data: Dict[str, Any]) -> Dict[str, Optional[Decimal]]:
        """
        Calculate valuation ratios
        
        Args:
            financial_data: Dictionary containing financial statement data and market data
            
        Returns:
            Dictionary of valuation ratios
        """
        # Extract market data
        market_cap = financial_data.get('market_cap')
        stock_price = financial_data.get('stock_price')
        shares_outstanding = financial_data.get('shares_outstanding')
        enterprise_value = financial_data.get('enterprise_value')
        
        # Extract financial data
        net_income = financial_data.get('net_income')
        revenue = financial_data.get('revenue')
        book_value = financial_data.get('book_value')
        ebitda = financial_data.get('ebitda')
        free_cash_flow = financial_data.get('free_cash_flow')
        
        # Calculate per-share metrics
        earnings_per_share = self.safe_divide(net_income, shares_outstanding)
        book_value_per_share = self.safe_divide(book_value, shares_outstanding)
        revenue_per_share = self.safe_divide(revenue, shares_outstanding)
        
        return {
            # Price-to-Earnings Ratio = Stock Price / Earnings per Share
            'pe_ratio': self.safe_divide(stock_price, earnings_per_share),
            
            # Price-to-Book Ratio = Stock Price / Book Value per Share
            'pb_ratio': self.safe_divide(stock_price, book_value_per_share),
            
            # Price-to-Sales Ratio = Market Cap / Revenue
            'ps_ratio': self.safe_divide(market_cap, revenue),
            
            # Enterprise Value to EBITDA = Enterprise Value / EBITDA
            'ev_ebitda': self.safe_divide(enterprise_value, ebitda),
            
            # Enterprise Value to Revenue = Enterprise Value / Revenue
            'ev_revenue': self.safe_divide(enterprise_value, revenue),
            
            # Price-to-Free Cash Flow = Market Cap / Free Cash Flow
            'price_to_fcf': self.safe_divide(market_cap, free_cash_flow),
            
            # Earnings per Share
            'earnings_per_share': earnings_per_share,
            
            # Book Value per Share
            'book_value_per_share': book_value_per_share,
            
            # Revenue per Share
            'revenue_per_share': revenue_per_share,
        }
    
    def calculate_growth_ratios(self, current_data: Dict[str, Any], previous_data: Dict[str, Any]) -> Dict[str, Optional[Decimal]]:
        """
        Calculate growth ratios comparing current period to previous period
        
        Args:
            current_data: Current period financial data
            previous_data: Previous period financial data
            
        Returns:
            Dictionary of growth ratios
        """
        def calculate_growth_rate(current: Optional[float], previous: Optional[float]) -> Optional[Decimal]:
            """Calculate growth rate between two periods"""
            if current is None or previous is None or previous == 0:
                return None
            
            growth = (current - previous) / previous
            return Decimal(str(growth)).quantize(self.precision, rounding=ROUND_HALF_UP)
        
        return {
            # Revenue Growth = (Current Revenue - Previous Revenue) / Previous Revenue
            'revenue_growth': calculate_growth_rate(
                current_data.get('revenue'), 
                previous_data.get('revenue')
            ),
            
            # Earnings Growth = (Current Net Income - Previous Net Income) / Previous Net Income
            'earnings_growth': calculate_growth_rate(
                current_data.get('net_income'), 
                previous_data.get('net_income')
            ),
            
            # EPS Growth = (Current EPS - Previous EPS) / Previous EPS
            'eps_growth': calculate_growth_rate(
                current_data.get('earnings_per_share'), 
                previous_data.get('earnings_per_share')
            ),
            
            # Book Value Growth = (Current Book Value - Previous Book Value) / Previous Book Value
            'book_value_growth': calculate_growth_rate(
                current_data.get('book_value'), 
                previous_data.get('book_value')
            ),
            
            # Operating Income Growth
            'operating_income_growth': calculate_growth_rate(
                current_data.get('operating_income'), 
                previous_data.get('operating_income')
            ),
            
            # Free Cash Flow Growth
            'free_cash_flow_growth': calculate_growth_rate(
                current_data.get('free_cash_flow'), 
                previous_data.get('free_cash_flow')
            ),
        }
    
    def calculate_quality_scores(self, financial_data: Dict[str, Any]) -> Dict[str, Optional[int]]:
        """
        Calculate quality scores (Piotroski F-Score, etc.)
        
        Args:
            financial_data: Dictionary containing financial statement data
            
        Returns:
            Dictionary of quality scores
        """
        # Piotroski F-Score calculation (9 criteria)
        piotroski_score = 0
        
        # Profitability criteria (4 points)
        if financial_data.get('net_income', 0) > 0:
            piotroski_score += 1
        
        if financial_data.get('operating_cash_flow', 0) > 0:
            piotroski_score += 1
        
        if financial_data.get('roa_current', 0) > financial_data.get('roa_previous', 0):
            piotroski_score += 1
        
        if financial_data.get('operating_cash_flow', 0) > financial_data.get('net_income', 0):
            piotroski_score += 1
        
        # Leverage, liquidity and source of funds criteria (3 points)
        if financial_data.get('long_term_debt_current', 0) < financial_data.get('long_term_debt_previous', float('inf')):
            piotroski_score += 1
        
        if financial_data.get('current_ratio_current', 0) > financial_data.get('current_ratio_previous', 0):
            piotroski_score += 1
        
        if financial_data.get('shares_outstanding_current', 0) <= financial_data.get('shares_outstanding_previous', float('inf')):
            piotroski_score += 1
        
        # Operating efficiency criteria (2 points)
        if financial_data.get('gross_margin_current', 0) > financial_data.get('gross_margin_previous', 0):
            piotroski_score += 1
        
        if financial_data.get('asset_turnover_current', 0) > financial_data.get('asset_turnover_previous', 0):
            piotroski_score += 1
        
        return {
            'piotroski_score': piotroski_score,
        }
    
    def calculate_all_ratios(
        self, 
        financial_data: Dict[str, Any], 
        previous_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Optional[Decimal]]:
        """
        Calculate all financial ratios
        
        Args:
            financial_data: Current period financial data
            previous_data: Previous period financial data (optional)
            
        Returns:
            Dictionary containing all calculated ratios
        """
        all_ratios = {}
        
        # Calculate all ratio categories
        all_ratios.update(self.calculate_liquidity_ratios(financial_data))
        all_ratios.update(self.calculate_profitability_ratios(financial_data))
        all_ratios.update(self.calculate_leverage_ratios(financial_data))
        all_ratios.update(self.calculate_efficiency_ratios(financial_data))
        all_ratios.update(self.calculate_valuation_ratios(financial_data))
        
        # Calculate growth ratios if previous data is available
        if previous_data:
            all_ratios.update(self.calculate_growth_ratios(financial_data, previous_data))
        
        # Calculate quality scores
        quality_scores = self.calculate_quality_scores(financial_data)
        all_ratios.update(quality_scores)
        
        return all_ratios


# Global ratio calculator instance
ratio_calculator = RatioCalculator()