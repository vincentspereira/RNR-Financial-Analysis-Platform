"""
Main API v1 router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, financial, data, monitoring, websocket, analytics, reports

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
            "Real-time Market Data",
            "Comprehensive Audit Logging"
        ]
    }