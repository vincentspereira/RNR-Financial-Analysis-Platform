"""
Main API v1 router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    financial,
    data,
    monitoring,
    websocket,
    analytics,
    reports,
    # Phase 4 endpoints
    market_data,
    technical_analysis,
    portfolio_optimization,
    backtesting,
    sentiment,
    billing,
    # Phase 5 endpoints
    risk,
    screener,
    notifications,
    paper_trading,
    admin,
)

api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(auth.router)

# Include financial calculation endpoints
api_router.include_router(financial.router)

# Include data ingestion endpoints
api_router.include_router(data.router)

# Include monitoring endpoints
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])

# Include WebSocket endpoints
api_router.include_router(websocket.router, prefix="/websocket", tags=["websocket"])

# Include analytics endpoints
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

# Include reports endpoints
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

# Phase 4: World-Class Features
api_router.include_router(market_data.router)
api_router.include_router(technical_analysis.router)
api_router.include_router(portfolio_optimization.router)
api_router.include_router(backtesting.router)
api_router.include_router(sentiment.router)
api_router.include_router(billing.router)

# Phase 5: Advanced Intelligence & Platform Maturity
api_router.include_router(risk.router)
api_router.include_router(screener.router)
api_router.include_router(notifications.router)
api_router.include_router(paper_trading.router)
api_router.include_router(admin.router)

# Health check endpoint
@api_router.get("/health")
async def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "Financial Analysis Platform API",
        "features": [
            "Authentication & Authorization",
            "Financial Ratio Calculations (50+ ratios)",
            "Company Valuation Models (DCF, DDM, Graham Number)",
            "Peer Comparison Analysis",
            "Batch Processing",
            "Quality Scores (Piotroski, Altman Z-Score)",
            "External Data Integration (Alpha Vantage, Yahoo Finance)",
            "Real-time Market Data Streaming (Polygon.io)",
            "Technical Analysis Engine (50+ indicators)",
            "Portfolio Optimization (Monte Carlo, VaR/CVaR, Efficient Frontier)",
            "Backtesting Framework (6 strategy types)",
            "Sentiment Analysis (NewsAPI, Finnhub)",
            "Billing & Subscriptions (Stripe)",
            "Risk Management (VaR, Stress Testing, Risk Scoring)",
            "Stock Screener (50+ stocks, 6 preset screeners)",
            "Notifications & Alerts (Price, Portfolio, Volume)",
            "Paper Trading Simulator (Virtual portfolios)",
            "Admin Dashboard (User management, Analytics)",
        ]
    }