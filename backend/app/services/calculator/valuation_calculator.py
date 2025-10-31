"""
Valuation calculator with DCF, DDM, and other valuation models
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
import math


class ValuationCalculator:
    """
    Comprehensive valuation calculator with multiple models
    """
    
    def __init__(self):
        """Initialize valuation calculator"""
        self.precision = Decimal('0.01')  # 2 decimal places for currency
    
    def safe_calculate(self, calculation_func, *args, **kwargs) -> Optional[Decimal]:
        """
        Safely perform calculations with error handling
        
        Args:
            calculation_func: Function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Decimal result or None if calculation fails
        """
        try:
            result = calculation_func(*args, **kwargs)
            if result is None or math.isnan(float(result)) or math.isinf(float(result)):
                return None
            return Decimal(str(result)).quantize(self.precision, rounding=ROUND_HALF_UP)
        except (ValueError, TypeError, ZeroDivisionError, OverflowError):
            return None
    
    def calculate_dcf_value(
        self,
        free_cash_flows: List[float],
        terminal_growth_rate: float,
        discount_rate: float,
        shares_outstanding: float
    ) -> Optional[Decimal]:
        """
        Calculate Discounted Cash Flow (DCF) valuation
        
        Args:
            free_cash_flows: List of projected free cash flows
            terminal_growth_rate: Terminal growth rate (as decimal, e.g., 0.03 for 3%)
            discount_rate: Discount rate/WACC (as decimal, e.g., 0.10 for 10%)
            shares_outstanding: Number of shares outstanding
            
        Returns:
            DCF value per share or None if calculation fails
        """
        def _calculate_dcf():
            if not free_cash_flows or discount_rate <= 0 or shares_outstanding <= 0:
                return None
            
            # Present value of projected cash flows
            pv_cash_flows = 0
            for i, fcf in enumerate(free_cash_flows, 1):
                pv_cash_flows += fcf / ((1 + discount_rate) ** i)
            
            # Terminal value calculation
            if len(free_cash_flows) > 0:
                terminal_fcf = free_cash_flows[-1] * (1 + terminal_growth_rate)
                terminal_value = terminal_fcf / (discount_rate - terminal_growth_rate)
                
                # Present value of terminal value
                pv_terminal_value = terminal_value / ((1 + discount_rate) ** len(free_cash_flows))
            else:
                pv_terminal_value = 0
            
            # Enterprise value
            enterprise_value = pv_cash_flows + pv_terminal_value
            
            # Value per share
            value_per_share = enterprise_value / shares_outstanding
            
            return value_per_share
        
        return self.safe_calculate(_calculate_dcf)
    
    def calculate_ddm_value(
        self,
        current_dividend: float,
        growth_rate: float,
        required_return: float
    ) -> Optional[Decimal]:
        """
        Calculate Dividend Discount Model (DDM) valuation
        
        Args:
            current_dividend: Current annual dividend per share
            growth_rate: Expected dividend growth rate (as decimal)
            required_return: Required rate of return (as decimal)
            
        Returns:
            DDM value per share or None if calculation fails
        """
        def _calculate_ddm():
            if required_return <= growth_rate or required_return <= 0:
                return None
            
            next_dividend = current_dividend * (1 + growth_rate)
            value = next_dividend / (required_return - growth_rate)
            
            return value
        
        return self.safe_calculate(_calculate_ddm)
    
    def calculate_two_stage_ddm(
        self,
        current_dividend: float,
        high_growth_rate: float,
        stable_growth_rate: float,
        required_return: float,
        high_growth_years: int
    ) -> Optional[Decimal]:
        """
        Calculate Two-Stage Dividend Discount Model
        
        Args:
            current_dividend: Current annual dividend per share
            high_growth_rate: High growth rate for initial years (as decimal)
            stable_growth_rate: Stable growth rate for terminal years (as decimal)
            required_return: Required rate of return (as decimal)
            high_growth_years: Number of high growth years
            
        Returns:
            Two-stage DDM value per share or None if calculation fails
        """
        def _calculate_two_stage_ddm():
            if required_return <= 0 or high_growth_years <= 0:
                return None
            
            # Stage 1: High growth period
            pv_high_growth = 0
            dividend = current_dividend
            
            for year in range(1, high_growth_years + 1):
                dividend *= (1 + high_growth_rate)
                pv_high_growth += dividend / ((1 + required_return) ** year)
            
            # Stage 2: Stable growth period
            terminal_dividend = dividend * (1 + stable_growth_rate)
            
            if required_return <= stable_growth_rate:
                return None
            
            terminal_value = terminal_dividend / (required_return - stable_growth_rate)
            pv_terminal_value = terminal_value / ((1 + required_return) ** high_growth_years)
            
            total_value = pv_high_growth + pv_terminal_value
            
            return total_value
        
        return self.safe_calculate(_calculate_two_stage_ddm)
    
    def calculate_graham_number(
        self,
        earnings_per_share: float,
        book_value_per_share: float
    ) -> Optional[Decimal]:
        """
        Calculate Benjamin Graham's intrinsic value formula
        
        Args:
            earnings_per_share: Earnings per share
            book_value_per_share: Book value per share
            
        Returns:
            Graham number or None if calculation fails
        """
        def _calculate_graham():
            if earnings_per_share <= 0 or book_value_per_share <= 0:
                return None
            
            # Graham Number = √(22.5 × EPS × BVPS)
            graham_number = math.sqrt(22.5 * earnings_per_share * book_value_per_share)
            
            return graham_number
        
        return self.safe_calculate(_calculate_graham)
    
    def calculate_peg_ratio(
        self,
        pe_ratio: float,
        earnings_growth_rate: float
    ) -> Optional[Decimal]:
        """
        Calculate Price/Earnings to Growth (PEG) ratio
        
        Args:
            pe_ratio: Price-to-earnings ratio
            earnings_growth_rate: Earnings growth rate (as percentage, e.g., 15 for 15%)
            
        Returns:
            PEG ratio or None if calculation fails
        """
        def _calculate_peg():
            if earnings_growth_rate <= 0 or pe_ratio <= 0:
                return None
            
            peg_ratio = pe_ratio / earnings_growth_rate
            
            return peg_ratio
        
        return self.safe_calculate(_calculate_peg)
    
    def calculate_ev_multiples(
        self,
        enterprise_value: float,
        ebitda: float,
        revenue: float,
        free_cash_flow: float
    ) -> Dict[str, Optional[Decimal]]:
        """
        Calculate Enterprise Value multiples
        
        Args:
            enterprise_value: Enterprise value
            ebitda: EBITDA
            revenue: Revenue
            free_cash_flow: Free cash flow
            
        Returns:
            Dictionary of EV multiples
        """
        def safe_divide(numerator, denominator):
            if denominator <= 0:
                return None
            return numerator / denominator
        
        return {
            'ev_ebitda': self.safe_calculate(safe_divide, enterprise_value, ebitda),
            'ev_revenue': self.safe_calculate(safe_divide, enterprise_value, revenue),
            'ev_fcf': self.safe_calculate(safe_divide, enterprise_value, free_cash_flow),
        }
    
    def calculate_altman_z_score(
        self,
        working_capital: float,
        total_assets: float,
        retained_earnings: float,
        ebit: float,
        market_value_equity: float,
        total_liabilities: float,
        sales: float
    ) -> Optional[Decimal]:
        """
        Calculate Altman Z-Score for bankruptcy prediction
        
        Args:
            working_capital: Working capital
            total_assets: Total assets
            retained_earnings: Retained earnings
            ebit: Earnings before interest and taxes
            market_value_equity: Market value of equity
            total_liabilities: Total liabilities
            sales: Sales/Revenue
            
        Returns:
            Altman Z-Score or None if calculation fails
        """
        def _calculate_altman_z():
            if total_assets <= 0:
                return None
            
            # Z = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
            # A = Working Capital / Total Assets
            # B = Retained Earnings / Total Assets
            # C = EBIT / Total Assets
            # D = Market Value of Equity / Total Liabilities
            # E = Sales / Total Assets
            
            a = working_capital / total_assets
            b = retained_earnings / total_assets
            c = ebit / total_assets
            d = market_value_equity / total_liabilities if total_liabilities > 0 else 0
            e = sales / total_assets
            
            z_score = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e
            
            return z_score
        
        return self.safe_calculate(_calculate_altman_z)
    
    def calculate_beneish_m_score(
        self,
        financial_data: Dict[str, float],
        previous_data: Dict[str, float]
    ) -> Optional[Decimal]:
        """
        Calculate Beneish M-Score for earnings manipulation detection
        
        Args:
            financial_data: Current period financial data
            previous_data: Previous period financial data
            
        Returns:
            Beneish M-Score or None if calculation fails
        """
        def _calculate_beneish_m():
            # Extract current period data
            receivables = financial_data.get('accounts_receivable', 0)
            sales = financial_data.get('revenue', 0)
            gross_profit = financial_data.get('gross_profit', 0)
            sga = financial_data.get('sga_expenses', 0)
            depreciation = financial_data.get('depreciation', 0)
            total_assets = financial_data.get('total_assets', 0)
            
            # Extract previous period data
            prev_receivables = previous_data.get('accounts_receivable', 0)
            prev_sales = previous_data.get('revenue', 0)
            prev_gross_profit = previous_data.get('gross_profit', 0)
            prev_sga = previous_data.get('sga_expenses', 0)
            prev_depreciation = previous_data.get('depreciation', 0)
            prev_total_assets = previous_data.get('total_assets', 0)
            
            if any(x <= 0 for x in [sales, prev_sales, total_assets, prev_total_assets]):
                return None
            
            # Calculate ratios
            dsri = (receivables / sales) / (prev_receivables / prev_sales) if prev_receivables > 0 and prev_sales > 0 else 1
            gmi = (prev_gross_profit / prev_sales) / (gross_profit / sales) if gross_profit > 0 and sales > 0 else 1
            aqi = 1  # Asset Quality Index (simplified)
            sgi = sales / prev_sales
            depi = (prev_depreciation / (prev_depreciation + prev_total_assets)) / (depreciation / (depreciation + total_assets)) if depreciation > 0 else 1
            sgai = (sga / sales) / (prev_sga / prev_sales) if prev_sga > 0 and prev_sales > 0 else 1
            lvgi = 1  # Leverage Index (simplified)
            tata = 0  # Total Accruals to Total Assets (simplified)
            
            # M-Score calculation
            m_score = (-4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 
                      0.892 * sgi + 0.115 * depi - 0.172 * sgai + 
                      4.679 * tata - 0.327 * lvgi)
            
            return m_score
        
        return self.safe_calculate(_calculate_beneish_m)
    
    def calculate_fair_value_estimate(
        self,
        financial_data: Dict[str, Any],
        market_data: Dict[str, Any],
        assumptions: Dict[str, float]
    ) -> Dict[str, Optional[Decimal]]:
        """
        Calculate comprehensive fair value estimate using multiple methods
        
        Args:
            financial_data: Financial statement data
            market_data: Market data
            assumptions: Valuation assumptions
            
        Returns:
            Dictionary of fair value estimates from different methods
        """
        estimates = {}
        
        # DCF Valuation
        if all(key in assumptions for key in ['free_cash_flows', 'terminal_growth_rate', 'discount_rate']):
            estimates['dcf_value'] = self.calculate_dcf_value(
                assumptions['free_cash_flows'],
                assumptions['terminal_growth_rate'],
                assumptions['discount_rate'],
                market_data.get('shares_outstanding', 1)
            )
        
        # DDM Valuation
        if all(key in financial_data for key in ['dividend_per_share']) and \
           all(key in assumptions for key in ['dividend_growth_rate', 'required_return']):
            estimates['ddm_value'] = self.calculate_ddm_value(
                financial_data['dividend_per_share'],
                assumptions['dividend_growth_rate'],
                assumptions['required_return']
            )
        
        # Graham Number
        if all(key in financial_data for key in ['earnings_per_share', 'book_value_per_share']):
            estimates['graham_number'] = self.calculate_graham_number(
                financial_data['earnings_per_share'],
                financial_data['book_value_per_share']
            )
        
        # PEG Ratio
        if all(key in market_data for key in ['pe_ratio']) and \
           all(key in assumptions for key in ['earnings_growth_rate']):
            estimates['peg_ratio'] = self.calculate_peg_ratio(
                market_data['pe_ratio'],
                assumptions['earnings_growth_rate']
            )
        
        # EV Multiples
        if all(key in market_data for key in ['enterprise_value']) and \
           all(key in financial_data for key in ['ebitda', 'revenue', 'free_cash_flow']):
            ev_multiples = self.calculate_ev_multiples(
                market_data['enterprise_value'],
                financial_data['ebitda'],
                financial_data['revenue'],
                financial_data['free_cash_flow']
            )
            estimates.update(ev_multiples)
        
        return estimates


# Global valuation calculator instance
valuation_calculator = ValuationCalculator()