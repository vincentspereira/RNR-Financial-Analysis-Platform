"""
Tests for PDF report generation (Phase 2, Task 2.4)
"""
import pytest
from app.services.report.pdf_generator import (
    ReportGenerator,
    ReportBuilder,
    ReportType,
)


@pytest.fixture
def generator():
    return ReportGenerator()


@pytest.fixture
def builder():
    return ReportBuilder()


class TestReportGenerator:
    """Test report metadata generation"""

    @pytest.mark.asyncio
    async def test_generate_portfolio_report(self, generator):
        result = await generator.generate_portfolio_report("port-123")
        assert result["portfolio_id"] == "port-123"
        assert result["status"] == "completed"
        assert "sections" in result
        assert result["report_type"] == "comprehensive"

    @pytest.mark.asyncio
    async def test_generate_performance_report(self, generator):
        result = await generator.generate_performance_report("port-123", period="6m")
        assert result["period"] == "6m"
        assert "metrics" in result
        assert "sharpe_ratio" in result["metrics"]

    @pytest.mark.asyncio
    async def test_generate_risk_report(self, generator):
        result = await generator.generate_risk_report("port-123")
        assert "risk_metrics" in result
        assert "var_95" in result["risk_metrics"]
        assert "recommendations" in result


class TestReportBuilder:
    """Test actual PDF generation"""

    @pytest.mark.asyncio
    async def test_build_portfolio_summary_report(self, builder):
        """PDF report should contain actual content, not mock data"""
        portfolio_data = {
            "name": "Test Portfolio",
            "total_value": 50000.00,
            "cash_balance": 10000.00,
            "holdings_count": 5,
            "gain_loss": 5000.00,
            "gain_loss_percentage": 11.11,
            "holdings": [
                {
                    "symbol": "AAPL",
                    "shares": 100,
                    "average_cost": 150.00,
                    "current_price": 175.00,
                },
                {
                    "symbol": "MSFT",
                    "shares": 50,
                    "average_cost": 300.00,
                    "current_price": 350.00,
                },
            ],
        }
        user_info = {"email": "test@example.com"}

        pdf_bytes = await builder.build_portfolio_summary_report(portfolio_data, user_info)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 100  # Should be a real PDF, not just "Mock PDF content"
        assert pdf_bytes.startswith(b"%PDF")  # Valid PDF header

    @pytest.mark.asyncio
    async def test_build_performance_report(self, builder):
        performance_data = {
            "portfolio_id": "port-123",
            "period": "1y",
            "metrics": {
                "total_return": 15.5,
                "annualized_return": 12.3,
                "volatility": 18.2,
                "sharpe_ratio": 0.85,
                "max_drawdown": -8.5,
            },
        }

        pdf_bytes = await builder.build_performance_analysis_report(performance_data)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_build_risk_report(self, builder):
        risk_data = {
            "portfolio_id": "port-123",
            "risk_metrics": {
                "var_95": -5.2,
                "cvar_95": -7.8,
                "volatility": 18.2,
                "beta": 1.1,
                "risk_score": 65,
            },
            "recommendations": [
                "Diversify across sectors",
                "Reduce high-volatility exposure",
            ],
        }

        pdf_bytes = await builder.build_risk_assessment_report(risk_data)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_build_empty_portfolio_report(self, builder):
        """Should handle empty portfolio gracefully"""
        pdf_bytes = await builder.build_portfolio_summary_report({}, {})
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")

    def test_report_types_enum(self):
        assert ReportType.PORTFOLIO_SUMMARY.value == "portfolio_summary"
        assert ReportType.COMPREHENSIVE.value == "comprehensive"
