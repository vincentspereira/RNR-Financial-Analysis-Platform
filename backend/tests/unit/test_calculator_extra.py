"""
Extra unit tests for the financial calculator stack.

Complements the existing `test_financial_calculator.py` with edge-case and
numerical-correctness coverage for the most-used ratio and valuation methods.
"""
from __future__ import annotations

from decimal import Decimal
import math

import pytest

from app.services.calculator.ratio_calculator import RatioCalculator
from app.services.calculator.valuation_calculator import ValuationCalculator


# ---------------------------------------------------------------------------
# RatioCalculator.safe_divide
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.financial
class TestSafeDivide:
    def setup_method(self):
        self.r = RatioCalculator()

    def test_safe_divide_returns_decimal_for_valid_input(self):
        result = self.r.safe_divide(10.0, 4.0)
        assert result is not None
        assert isinstance(result, Decimal)
        assert result == Decimal("2.500000")

    def test_safe_divide_returns_none_when_numerator_is_none(self):
        assert self.r.safe_divide(None, 1.0) is None

    def test_safe_divide_returns_none_when_denominator_is_none(self):
        assert self.r.safe_divide(1.0, None) is None

    def test_safe_divide_returns_none_when_denominator_is_zero(self):
        assert self.r.safe_divide(1.0, 0.0) is None
        assert self.r.safe_divide(1.0, 0) is None

    def test_safe_divide_handles_negative_numbers(self):
        assert self.r.safe_divide(-10.0, 2.0) == Decimal("-5.000000")


# ---------------------------------------------------------------------------
# RatioCalculator ratio bundles
# ---------------------------------------------------------------------------

@pytest.fixture
def basic_financials():
    """Reasonably realistic numbers for a healthy mid-cap."""
    return {
        "current_assets": 200_000_000,
        "current_liabilities": 100_000_000,
        "cash_and_equivalents": 50_000_000,
        "short_term_investments": 20_000_000,
        "inventory": 60_000_000,
        "accounts_receivable": 40_000_000,
        "operating_cash_flow": 80_000_000,
        "revenue": 500_000_000,
        "gross_profit": 200_000_000,
        "operating_income": 100_000_000,
        "net_income": 60_000_000,
        "ebitda": 130_000_000,
        "total_assets": 800_000_000,
        "shareholders_equity": 400_000_000,
        "invested_capital": 500_000_000,
        "total_debt": 200_000_000,
        "long_term_debt": 150_000_000,
        "short_term_debt": 50_000_000,
        "interest_expense": 10_000_000,
        "total_debt_service": 30_000_000,
    }


@pytest.mark.unit
@pytest.mark.financial
class TestLiquidityRatios:
    def test_current_ratio_is_assets_over_liabilities(self, basic_financials):
        r = RatioCalculator().calculate_liquidity_ratios(basic_financials)
        # 200M / 100M = 2.0
        assert r["current_ratio"] == Decimal("2.000000")

    def test_quick_ratio_excludes_inventory(self, basic_financials):
        r = RatioCalculator().calculate_liquidity_ratios(basic_financials)
        # (200M - 60M) / 100M = 1.4
        assert r["quick_ratio"] == Decimal("1.400000")

    def test_cash_ratio_uses_cash_plus_short_term_investments(self, basic_financials):
        r = RatioCalculator().calculate_liquidity_ratios(basic_financials)
        # (50M + 20M) / 100M = 0.7
        assert r["cash_ratio"] == Decimal("0.700000")

    def test_liquidity_returns_none_when_inputs_missing(self):
        r = RatioCalculator().calculate_liquidity_ratios({})
        assert r["current_ratio"] is None
        assert r["quick_ratio"] is None
        assert r["cash_ratio"] is None


@pytest.mark.unit
@pytest.mark.financial
class TestProfitabilityRatios:
    def test_margins_correct(self, basic_financials):
        r = RatioCalculator().calculate_profitability_ratios(basic_financials)
        # 200M / 500M = 0.4
        assert r["gross_profit_margin"] == Decimal("0.400000")
        # 100M / 500M = 0.2
        assert r["operating_margin"] == Decimal("0.200000")
        # 60M / 500M = 0.12
        assert r["net_profit_margin"] == Decimal("0.120000")

    def test_roa_uses_total_assets_when_avg_missing(self, basic_financials):
        r = RatioCalculator().calculate_profitability_ratios(basic_financials)
        # 60M / 800M = 0.075
        assert r["roa"] == Decimal("0.075000")

    def test_roe_correct(self, basic_financials):
        r = RatioCalculator().calculate_profitability_ratios(basic_financials)
        # 60M / 400M = 0.15
        assert r["roe"] == Decimal("0.150000")


@pytest.mark.unit
@pytest.mark.financial
class TestLeverageRatios:
    def test_debt_to_equity_correct(self, basic_financials):
        r = RatioCalculator().calculate_leverage_ratios(basic_financials)
        # 200M / 400M = 0.5
        assert r["debt_to_equity"] == Decimal("0.500000")

    def test_debt_to_assets_correct(self, basic_financials):
        r = RatioCalculator().calculate_leverage_ratios(basic_financials)
        # 200M / 800M = 0.25
        assert r["debt_to_assets"] == Decimal("0.250000")

    def test_interest_coverage_correct(self, basic_financials):
        r = RatioCalculator().calculate_leverage_ratios(basic_financials)
        # 100M / 10M = 10
        assert r["interest_coverage_ratio"] == Decimal("10.000000")


# ---------------------------------------------------------------------------
# ValuationCalculator
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.financial
class TestDCF:
    def setup_method(self):
        self.v = ValuationCalculator()

    def test_dcf_with_zero_growth_equals_perpetuity_minus_discounting(self):
        # 5 years of flat $100M FCF, 0% terminal growth, 10% discount, 10M shares
        fcfs = [100_000_000] * 5
        result = self.v.calculate_dcf_value(
            free_cash_flows=fcfs,
            terminal_growth_rate=0.0,
            discount_rate=0.10,
            shares_outstanding=10_000_000,
        )
        assert result is not None
        # Sanity: with 0% perpetual growth and 10% discount, TV = FCF/r
        # = 100M / 0.10 = 1B. Plus PV of 5 yrs of explicit FCFs (~380M).
        # Total EV ~ 1.0B + PV(TV)=1B/(1.1**5)~620M => ~1B / 10M = ~$100
        assert Decimal("50") < result < Decimal("200")

    def test_dcf_returns_none_when_discount_rate_zero(self):
        result = self.v.calculate_dcf_value(
            free_cash_flows=[100, 200],
            terminal_growth_rate=0.02,
            discount_rate=0.0,
            shares_outstanding=100,
        )
        assert result is None

    def test_dcf_returns_none_when_shares_zero(self):
        result = self.v.calculate_dcf_value(
            free_cash_flows=[100, 200],
            terminal_growth_rate=0.02,
            discount_rate=0.10,
            shares_outstanding=0,
        )
        assert result is None

    def test_dcf_returns_none_when_fcfs_empty(self):
        result = self.v.calculate_dcf_value(
            free_cash_flows=[],
            terminal_growth_rate=0.02,
            discount_rate=0.10,
            shares_outstanding=100,
        )
        assert result is None


@pytest.mark.unit
@pytest.mark.financial
class TestDDM:
    def setup_method(self):
        self.v = ValuationCalculator()

    def test_gordon_growth_formula(self):
        # D0 = $1, g = 5%, r = 10%
        # V = D0*(1+g) / (r - g) = 1.05 / 0.05 = $21.00
        result = self.v.calculate_ddm_value(
            current_dividend=1.0, growth_rate=0.05, required_return=0.10
        )
        assert result == Decimal("21.00")

    def test_ddm_returns_none_when_growth_exceeds_required_return(self):
        # Otherwise denominator goes negative or zero
        assert (
            self.v.calculate_ddm_value(
                current_dividend=1.0, growth_rate=0.12, required_return=0.10
            )
            is None
        )
        assert (
            self.v.calculate_ddm_value(
                current_dividend=1.0, growth_rate=0.10, required_return=0.10
            )
            is None
        )

    def test_ddm_returns_none_for_zero_required_return(self):
        assert (
            self.v.calculate_ddm_value(
                current_dividend=1.0, growth_rate=0.05, required_return=0.0
            )
            is None
        )


@pytest.mark.unit
@pytest.mark.financial
class TestGrahamNumber:
    def setup_method(self):
        self.v = ValuationCalculator()

    def test_graham_number_correct(self):
        # √(22.5 * 5 * 20) = √2250 ≈ 47.43
        result = self.v.calculate_graham_number(
            earnings_per_share=5.0, book_value_per_share=20.0
        )
        assert result is not None
        expected = Decimal(str(math.sqrt(22.5 * 5.0 * 20.0))).quantize(Decimal("0.01"))
        assert result == expected

    def test_graham_rejects_negative_eps(self):
        assert self.v.calculate_graham_number(-1.0, 20.0) is None

    def test_graham_rejects_negative_book_value(self):
        assert self.v.calculate_graham_number(5.0, -1.0) is None

    def test_graham_rejects_zero_inputs(self):
        assert self.v.calculate_graham_number(0.0, 20.0) is None
        assert self.v.calculate_graham_number(5.0, 0.0) is None


@pytest.mark.unit
@pytest.mark.financial
class TestAltmanZ:
    def test_altman_z_known_healthy_company(self):
        # Z = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E
        # Pick values so Z = 1.2*0.1 + 1.4*0.2 + 3.3*0.15 + 0.6*2.0 + 1.0*1.5
        #             = 0.12 + 0.28 + 0.495 + 1.2 + 1.5 = 3.595
        v = ValuationCalculator()
        result = v.calculate_altman_z_score(
            working_capital=10,
            total_assets=100,
            retained_earnings=20,
            ebit=15,
            market_value_equity=200,
            total_liabilities=100,
            sales=150,
        )
        assert result is not None
        assert abs(float(result) - 3.595) < 0.01

    def test_altman_z_returns_none_when_total_assets_zero(self):
        v = ValuationCalculator()
        assert (
            v.calculate_altman_z_score(
                working_capital=10,
                total_assets=0,
                retained_earnings=20,
                ebit=15,
                market_value_equity=200,
                total_liabilities=100,
                sales=150,
            )
            is None
        )
