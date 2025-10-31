"""
Unit tests for Financial Calculator Service
"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from app.services.calculator.financial_calculator import FinancialCalculator
from app.services.calculator.ratio_calculator import RatioCalculator
from app.services.calculator.valuation_calculator import ValuationCalculator


class TestFinancialCalculator:
    """Unit tests for FinancialCalculator class"""
    
    @pytest.fixture
    def financial_calculator(self):
        """Create FinancialCalculator instance for testing"""
        return FinancialCalculator()
    
    @pytest.fixture
    def sample_financial_data(self):
        """Sample financial data for testing"""
        return {
            'revenue': 1000000000,
            'gross_profit': 400000000,
            'operating_income': 200000000,
            'net_income': 150000000,
            'total_assets': 2000000000,
            'current_assets': 800000000,
            'cash_and_equivalents': 200000000,
            'current_liabilities': 400000000,
            'total_debt': 600000000,
            'shareholders_equity': 1000000000,
            'shares_outstanding': 100000000,
            'stock_price': 50.0
        }
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_get_company_financial_data_success(self, financial_calculator):
        """Test successful retrieval of company financial data"""
        # Mock database session
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = Mock(
            id=uuid4(),
            symbol='AAPL',
            name='Apple Inc.'
        )
        mock_db.execute.return_value = mock_result
        
        company_id = uuid4()
        
        with patch.object(financial_calculator, '_fetch_financial_statements') as mock_fetch:
            mock_fetch.return_value = {
                'revenue': 1000000000,
                'net_income': 150000000
            }
            
            result = await financial_calculator.get_company_financial_data(
                company_id=company_id,
                period_type='annual',
                fiscal_year=2023,
                db=mock_db
            )
            
            assert result is not None
            assert 'revenue' in result
            assert result['revenue'] == 1000000000
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_calculate_financial_ratios_success(self, financial_calculator, sample_financial_data):
        """Test successful financial ratios calculation"""
        mock_db = AsyncMock()
        company_id = uuid4()
        
        with patch.object(financial_calculator, 'get_company_financial_data') as mock_get_data:
            mock_get_data.return_value = sample_financial_data
            
            result = await financial_calculator.calculate_financial_ratios(
                company_id=company_id,
                period_type='annual',
                fiscal_year=2023,
                db=mock_db
            )
            
            assert result is not None
            assert 'company_id' in result
            assert 'ratios' in result
            assert result['company_id'] == company_id
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_calculate_financial_ratios_no_data(self, financial_calculator):
        """Test financial ratios calculation with no data"""
        mock_db = AsyncMock()
        company_id = uuid4()
        
        with patch.object(financial_calculator, 'get_company_financial_data') as mock_get_data:
            mock_get_data.return_value = None
            
            result = await financial_calculator.calculate_financial_ratios(
                company_id=company_id,
                period_type='annual',
                fiscal_year=2023,
                db=mock_db
            )
            
            assert result is None
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_calculate_company_valuation_success(self, financial_calculator, sample_financial_data):
        """Test successful company valuation calculation"""
        mock_db = AsyncMock()
        company_id = uuid4()
        
        valuation_assumptions = {
            'free_cash_flows': [180000000, 200000000, 220000000, 240000000, 260000000],
            'terminal_growth_rate': 0.03,
            'discount_rate': 0.10,
            'shares_outstanding': 100000000
        }
        
        with patch.object(financial_calculator, 'get_company_financial_data') as mock_get_data:
            mock_get_data.return_value = sample_financial_data
            
            result = await financial_calculator.calculate_company_valuation(
                company_id=company_id,
                valuation_assumptions=valuation_assumptions,
                db=mock_db
            )
            
            assert result is not None
            assert 'company_id' in result
            assert 'fair_value_estimates' in result
            assert result['company_id'] == company_id
    
    @pytest.mark.unit
    @pytest.mark.fast
    async def test_save_calculated_ratios_success(self, financial_calculator):
        """Test successful saving of calculated ratios"""
        mock_db = AsyncMock()
        
        ratios_data = {
            'company_id': uuid4(),
            'period_type': 'annual',
            'fiscal_year': 2023,
            'ratios': {
                'current_ratio': Decimal('2.0'),
                'quick_ratio': Decimal('1.5')
            }
        }
        
        # Mock the database operations
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        await financial_calculator.save_calculated_ratios(ratios_data, mock_db)
        
        # Verify database operations were called
        assert mock_db.add.called
        assert mock_db.flush.called


class TestRatioCalculator:
    """Unit tests for RatioCalculator class"""
    
    @pytest.fixture
    def ratio_calculator(self):
        """Create RatioCalculator instance for testing"""
        return RatioCalculator()
    
    @pytest.fixture
    def sample_data(self):
        """Sample financial data for ratio calculations"""
        return {
            'current_assets': 800000000,
            'current_liabilities': 400000000,
            'cash_and_equivalents': 200000000,
            'inventory': 100000000,
            'revenue': 1000000000,
            'net_income': 150000000,
            'total_assets': 2000000000,
            'shareholders_equity': 1000000000
        }
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_calculate_liquidity_ratios(self, ratio_calculator, sample_data):
        """Test liquidity ratios calculation"""
        ratios = ratio_calculator.calculate_liquidity_ratios(sample_data)
        
        assert 'current_ratio' in ratios
        assert 'quick_ratio' in ratios
        assert 'cash_ratio' in ratios
        
        # Verify calculations
        assert ratios['current_ratio'] == Decimal('2.000000')  # 800M / 400M
        assert ratios['quick_ratio'] == Decimal('1.750000')    # (800M - 100M) / 400M
        assert ratios['cash_ratio'] == Decimal('0.500000')     # 200M / 400M
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_calculate_profitability_ratios(self, ratio_calculator, sample_data):
        """Test profitability ratios calculation"""
        ratios = ratio_calculator.calculate_profitability_ratios(sample_data)
        
        assert 'net_profit_margin' in ratios
        assert 'roa' in ratios
        assert 'roe' in ratios
        
        # Verify calculations
        assert ratios['net_profit_margin'] == Decimal('0.150000')  # 150M / 1000M
        assert ratios['roa'] == Decimal('0.075000')               # 150M / 2000M
        assert ratios['roe'] == Decimal('0.150000')               # 150M / 1000M
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_safe_divide_normal_case(self, ratio_calculator):
        """Test safe_divide with normal values"""
        result = ratio_calculator.safe_divide(100, 50)
        assert result == Decimal('2.000000')
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_safe_divide_zero_denominator(self, ratio_calculator):
        """Test safe_divide with zero denominator"""
        result = ratio_calculator.safe_divide(100, 0)
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_safe_divide_none_values(self, ratio_calculator):
        """Test safe_divide with None values"""
        result = ratio_calculator.safe_divide(None, 50)
        assert result is None
        
        result = ratio_calculator.safe_divide(100, None)
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.monitoring
    def test_calculate_piotroski_score(self, ratio_calculator, sample_data):
        """Test Piotroski F-Score calculation for monitoring"""
        # Add required data for Piotroski score
        extended_data = {
            **sample_data,
            'operating_cash_flow': 180000000,
            'long_term_debt': 300000000,
            'gross_profit': 400000000,
            'cost_of_goods_sold': 600000000,
            'shares_outstanding': 100000000
        }
        
        score = ratio_calculator.calculate_piotroski_score(extended_data)
        
        assert score is not None
        assert isinstance(score, (int, Decimal))
        assert 0 <= score <= 9


class TestValuationCalculator:
    """Unit tests for ValuationCalculator class"""
    
    @pytest.fixture
    def valuation_calculator(self):
        """Create ValuationCalculator instance for testing"""
        return ValuationCalculator()
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_calculate_dcf_value_success(self, valuation_calculator):
        """Test DCF valuation calculation"""
        free_cash_flows = [180000000, 200000000, 220000000, 240000000, 260000000]
        terminal_growth_rate = 0.03
        discount_rate = 0.10
        shares_outstanding = 100000000
        
        dcf_value = valuation_calculator.calculate_dcf_value(
            free_cash_flows=free_cash_flows,
            terminal_growth_rate=terminal_growth_rate,
            discount_rate=discount_rate,
            shares_outstanding=shares_outstanding
        )
        
        assert dcf_value is not None
        assert isinstance(dcf_value, Decimal)
        assert dcf_value > 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_calculate_graham_number_success(self, valuation_calculator):
        """Test Graham Number calculation"""
        eps = 1.50
        book_value_per_share = 10.00
        
        graham_number = valuation_calculator.calculate_graham_number(
            earnings_per_share=eps,
            book_value_per_share=book_value_per_share
        )
        
        assert graham_number is not None
        assert isinstance(graham_number, Decimal)
        assert graham_number > 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_calculate_peg_ratio_success(self, valuation_calculator):
        """Test PEG ratio calculation"""
        pe_ratio = 20.0
        earnings_growth_rate = 15.0
        
        peg_ratio = valuation_calculator.calculate_peg_ratio(
            pe_ratio=pe_ratio,
            earnings_growth_rate=earnings_growth_rate
        )
        
        assert peg_ratio is not None
        assert isinstance(peg_ratio, Decimal)
        assert peg_ratio > 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_calculate_altman_z_score_success(self, valuation_calculator):
        """Test Altman Z-Score calculation"""
        z_score = valuation_calculator.calculate_altman_z_score(
            working_capital=400000000,
            total_assets=2000000000,
            retained_earnings=500000000,
            ebit=200000000,
            market_value_equity=5000000000,
            total_liabilities=1000000000,
            sales=1000000000
        )
        
        assert z_score is not None
        assert isinstance(z_score, Decimal)
        assert z_score > 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_safe_calculate_normal_case(self, valuation_calculator):
        """Test safe_calculate with normal function"""
        def test_func():
            return 42.0
        
        result = valuation_calculator.safe_calculate(test_func)
        assert result == Decimal('42.0')
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_safe_calculate_exception(self, valuation_calculator):
        """Test safe_calculate with exception"""
        def test_func():
            raise ValueError("Test exception")
        
        result = valuation_calculator.safe_calculate(test_func)
        assert result is None
    
    @pytest.mark.unit
    @pytest.mark.autoscaling
    def test_calculate_fair_value_estimate(self, valuation_calculator):
        """Test fair value estimation for autoscaling validation"""
        financial_data = {
            'free_cash_flows': [180000000, 200000000, 220000000, 240000000, 260000000],
            'terminal_growth_rate': 0.03,
            'discount_rate': 0.10,
            'shares_outstanding': 100000000,
            'earnings_per_share': 1.50,
            'book_value_per_share': 10.00,
            'pe_ratio': 20.0,
            'earnings_growth_rate': 15.0
        }
        
        estimates = valuation_calculator.calculate_fair_value_estimate(financial_data)
        
        assert estimates is not None
        assert isinstance(estimates, dict)
        assert 'dcf_value' in estimates or 'graham_number' in estimates


# Performance benchmarks for monitoring
class TestPerformanceBenchmarks:
    """Performance benchmarks for financial calculations"""
    
    @pytest.mark.unit
    @pytest.mark.monitoring
    @pytest.mark.benchmark
    def test_ratio_calculation_performance(self, benchmark):
        """Benchmark ratio calculation performance"""
        ratio_calculator = RatioCalculator()
        
        sample_data = {
            'current_assets': 800000000,
            'current_liabilities': 400000000,
            'revenue': 1000000000,
            'net_income': 150000000,
            'total_assets': 2000000000,
            'shareholders_equity': 1000000000
        }
        
        def calculate_all_ratios():
            liquidity = ratio_calculator.calculate_liquidity_ratios(sample_data)
            profitability = ratio_calculator.calculate_profitability_ratios(sample_data)
            return {**liquidity, **profitability}
        
        result = benchmark(calculate_all_ratios)
        assert result is not None
    
    @pytest.mark.unit
    @pytest.mark.monitoring
    @pytest.mark.benchmark
    def test_valuation_calculation_performance(self, benchmark):
        """Benchmark valuation calculation performance"""
        valuation_calculator = ValuationCalculator()
        
        def calculate_dcf():
            return valuation_calculator.calculate_dcf_value(
                free_cash_flows=[180000000, 200000000, 220000000, 240000000, 260000000],
                terminal_growth_rate=0.03,
                discount_rate=0.10,
                shares_outstanding=100000000
            )
        
        result = benchmark(calculate_dcf)
        assert result is not None