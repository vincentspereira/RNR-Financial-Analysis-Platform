"""Report Generator Service - Generate various types of reports"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO

from app.core.logging import get_logger

logger = get_logger("app.reports.pdf_generator")


class ReportType(Enum):
    """Available report types"""
    PORTFOLIO_SUMMARY = "portfolio_summary"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    COMPREHENSIVE = "comprehensive"


class ChartType(Enum):
    """Available chart types"""
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    AREA_CHART = "area_chart"


@dataclass
class ReportConfig:
    """Report configuration"""
    title: str
    subtitle: Optional[str] = None
    report_type: str = "comprehensive"
    sections: Optional[List[str]] = None


@dataclass
class ReportSection:
    """Report section configuration"""
    title: str
    content_type: str
    content: Any


@dataclass
class ChartConfig:
    """Chart configuration"""
    chart_type: ChartType
    title: str
    data: Dict[str, Any]


class ReportGenerator:
    """Service for generating various types of reports"""

    async def generate_portfolio_report(self, portfolio_id: str, report_type: str = "comprehensive") -> Dict[str, Any]:
        """Generate portfolio report metadata"""
        return {
            "report_id": f"report_{portfolio_id}_{int(datetime.now(timezone.utc).timestamp())}",
            "portfolio_id": portfolio_id,
            "report_type": report_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "file_path": f"/reports/portfolio_{portfolio_id}_{report_type}.pdf",
            "file_size": 1024000,
            "sections": [
                "executive_summary",
                "performance_analysis",
                "risk_assessment",
                "holdings_breakdown",
                "recommendations",
            ],
        }

    async def generate_performance_report(self, portfolio_id: str, period: str = "1y") -> Dict[str, Any]:
        """Generate performance report metadata"""
        return {
            "report_id": f"perf_report_{portfolio_id}_{period}",
            "portfolio_id": portfolio_id,
            "period": period,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "total_return": 15.5,
                "annualized_return": 12.3,
                "volatility": 18.2,
                "sharpe_ratio": 0.85,
                "max_drawdown": -8.5,
            },
            "status": "completed",
        }

    async def generate_risk_report(self, portfolio_id: str) -> Dict[str, Any]:
        """Generate risk assessment report metadata"""
        return {
            "report_id": f"risk_report_{portfolio_id}",
            "portfolio_id": portfolio_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "risk_metrics": {
                "var_95": -5.2,
                "cvar_95": -7.8,
                "volatility": 18.2,
                "beta": 1.1,
                "risk_score": 65,
            },
            "recommendations": [
                "Consider diversifying across more sectors",
                "Reduce exposure to high-volatility assets",
                "Add defensive positions to reduce overall risk",
            ],
            "status": "completed",
        }


class ReportBuilder:
    """Builder class for creating PDF reports using reportlab"""

    async def build_portfolio_summary_report(
        self, portfolio_data: Dict[str, Any], user_info: Dict[str, Any]
    ) -> bytes:
        """Build portfolio summary PDF report"""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        )
        from reportlab.lib import colors

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=letter,
            topMargin=0.75 * inch, bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        )
        styles = getSampleStyleSheet()
        elements = []

        # Title
        title = portfolio_data.get("name", "Portfolio Summary Report")
        elements.append(Paragraph(title, styles["Title"]))
        elements.append(Spacer(1, 12))

        # Report metadata
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        elements.append(Paragraph(f"Generated: {generated_at}", styles["Normal"]))
        if user_info.get("email"):
            elements.append(Paragraph(f"Prepared for: {user_info['email']}", styles["Normal"]))
        elements.append(Spacer(1, 20))

        # Executive Summary
        elements.append(Paragraph("Executive Summary", styles["Heading2"]))
        elements.append(Spacer(1, 6))

        total_value = portfolio_data.get("total_value", 0)
        cash_balance = portfolio_data.get("cash_balance", 0)
        holdings_count = portfolio_data.get("holdings_count", 0)
        gain_loss = portfolio_data.get("gain_loss", 0)
        gain_loss_pct = portfolio_data.get("gain_loss_percentage", 0)

        summary_data = [
            ["Metric", "Value"],
            ["Total Portfolio Value", f"${total_value:,.2f}"],
            ["Cash Balance", f"${cash_balance:,.2f}"],
            ["Number of Holdings", str(holdings_count)],
            ["Total Gain/Loss", f"${gain_loss:,.2f} ({gain_loss_pct:+.2f}%)"],
        ]
        summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Holdings Breakdown
        holdings = portfolio_data.get("holdings", [])
        if holdings:
            elements.append(Paragraph("Holdings Breakdown", styles["Heading2"]))
            elements.append(Spacer(1, 6))

            holdings_header = ["Symbol", "Shares", "Avg Cost", "Current Price", "Market Value", "Gain/Loss"]
            holdings_rows = [holdings_header]
            for h in holdings:
                shares = h.get("shares", h.get("quantity", 0))
                avg_cost = h.get("average_cost", h.get("purchase_price", 0))
                current = h.get("current_price", avg_cost)
                market_val = shares * current
                cost_basis = shares * avg_cost
                gl = market_val - cost_basis
                gl_pct = (gl / cost_basis * 100) if cost_basis else 0
                holdings_rows.append([
                    h.get("symbol", ""),
                    f"{shares:.4f}",
                    f"${avg_cost:,.2f}",
                    f"${current:,.2f}",
                    f"${market_val:,.2f}",
                    f"${gl:,.2f} ({gl_pct:+.1f}%)",
                ])

            holdings_table = Table(
                holdings_rows,
                colWidths=[0.8 * inch, 0.8 * inch, 0.9 * inch, 1 * inch, 1.1 * inch, 1.4 * inch],
            )
            holdings_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ]))
            elements.append(holdings_table)
            elements.append(Spacer(1, 20))

        # Footer disclaimer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            "This report is generated for informational purposes only and does not constitute "
            "financial advice. Past performance is not indicative of future results.",
            styles["Italic"],
        ))

        doc.build(elements)
        return buffer.getvalue()

    async def build_performance_analysis_report(
        self, performance_data: Dict[str, Any]
    ) -> bytes:
        """Build performance analysis PDF report"""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        )
        from reportlab.lib import colors

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=letter,
            topMargin=0.75 * inch, bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        )
        styles = getSampleStyleSheet()
        elements = []

        # Title
        portfolio_id = performance_data.get("portfolio_id", "N/A")
        elements.append(Paragraph(f"Performance Analysis Report", styles["Title"]))
        elements.append(Paragraph(f"Portfolio: {portfolio_id}", styles["Heading2"]))
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        elements.append(Paragraph(f"Generated: {generated_at}", styles["Normal"]))
        elements.append(Spacer(1, 20))

        # Performance Metrics
        elements.append(Paragraph("Performance Metrics", styles["Heading2"]))
        elements.append(Spacer(1, 6))

        metrics = performance_data.get("metrics", {})
        metrics_data = [
            ["Metric", "Value"],
            ["Total Return", f"{metrics.get('total_return', 0):+.2f}%"],
            ["Annualized Return", f"{metrics.get('annualized_return', 0):+.2f}%"],
            ["Volatility", f"{metrics.get('volatility', 0):.2f}%"],
            ["Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.3f}"],
            ["Max Drawdown", f"{metrics.get('max_drawdown', 0):.2f}%"],
        ]
        metrics_table = Table(metrics_data, colWidths=[3 * inch, 3 * inch])
        metrics_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ]))
        elements.append(metrics_table)
        elements.append(Spacer(1, 20))

        # Period analysis sections
        period = performance_data.get("period", "1y")
        elements.append(Paragraph(f"Analysis Period: {period}", styles["Heading2"]))
        elements.append(Spacer(1, 6))

        monthly_returns = performance_data.get("monthly_returns", [])
        if monthly_returns:
            elements.append(Paragraph("Monthly Returns", styles["Heading3"]))
            mr_header = ["Month", "Return (%)"]
            mr_rows = [mr_header] + [
                [mr.get("month", ""), f"{mr.get('return', 0):+.2f}%"]
                for mr in monthly_returns
            ]
            mr_table = Table(mr_rows, colWidths=[3 * inch, 3 * inch])
            mr_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ]))
            elements.append(mr_table)

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            "Past performance is not indicative of future results.",
            styles["Italic"],
        ))

        doc.build(elements)
        return buffer.getvalue()

    async def build_risk_assessment_report(
        self, risk_data: Dict[str, Any]
    ) -> bytes:
        """Build risk assessment PDF report"""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        )
        from reportlab.lib import colors

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=letter,
            topMargin=0.75 * inch, bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        )
        styles = getSampleStyleSheet()
        elements = []

        # Title
        portfolio_id = risk_data.get("portfolio_id", "N/A")
        elements.append(Paragraph("Risk Assessment Report", styles["Title"]))
        elements.append(Paragraph(f"Portfolio: {portfolio_id}", styles["Heading2"]))
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        elements.append(Paragraph(f"Generated: {generated_at}", styles["Normal"]))
        elements.append(Spacer(1, 20))

        # Risk Metrics
        elements.append(Paragraph("Risk Metrics", styles["Heading2"]))
        elements.append(Spacer(1, 6))

        metrics = risk_data.get("risk_metrics", {})
        risk_data_rows = [
            ["Risk Metric", "Value"],
            ["Value at Risk (95%)", f"{metrics.get('var_95', 0):.2f}%"],
            ["Conditional VaR (95%)", f"{metrics.get('cvar_95', 0):.2f}%"],
            ["Volatility", f"{metrics.get('volatility', 0):.2f}%"],
            ["Beta", f"{metrics.get('beta', 0):.2f}"],
            ["Risk Score", f"{metrics.get('risk_score', 0)}/100"],
        ]
        risk_table = Table(risk_data_rows, colWidths=[3 * inch, 3 * inch])
        risk_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b71c1c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ffebee")]),
        ]))
        elements.append(risk_table)
        elements.append(Spacer(1, 20))

        # Recommendations
        recommendations = risk_data.get("recommendations", [])
        if recommendations:
            elements.append(Paragraph("Recommendations", styles["Heading2"]))
            elements.append(Spacer(1, 6))
            for rec in recommendations:
                elements.append(Paragraph(f"• {rec}", styles["Normal"]))
                elements.append(Spacer(1, 4))

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            "Risk metrics are estimates based on historical data and do not guarantee future outcomes.",
            styles["Italic"],
        ))

        doc.build(elements)
        return buffer.getvalue()


# Global instances
report_generator = ReportGenerator()
report_builder = ReportBuilder()

# Module-level functions for backward compatibility
async def generate_portfolio_report(portfolio_id: str, report_type: str = "comprehensive") -> Dict[str, Any]:
    """Generate portfolio report"""
    return await report_generator.generate_portfolio_report(portfolio_id, report_type)

async def generate_performance_report(portfolio_id: str, period: str = "1y") -> Dict[str, Any]:
    """Generate performance report"""
    return await report_generator.generate_performance_report(portfolio_id, period)

async def generate_risk_report(portfolio_id: str) -> Dict[str, Any]:
    """Generate risk assessment report"""
    return await report_generator.generate_risk_report(portfolio_id)
