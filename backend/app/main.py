"""
Main FastAPI application for the RNR Financial Analysis Platform
"""
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import logger_manager, get_logger
from app.core.middleware import (
    RateLimitingMiddleware,
    ErrorHandlingMiddleware,
)
from app.core.cache_middleware import CacheMiddleware
from app.core.compression import CompressionMiddleware
from app.core.fast_middleware import ConsolidatedMiddleware
from app.core.exceptions import BaseAPIException

# Initialize logging
logger_manager.configure_logging(
    log_level=settings.LOG_LEVEL,
    log_file=settings.LOG_FILE
)

# Get application logger
app_logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    app_logger.logger.info("Starting RNR Financial Analysis Platform API")
    app_logger.logger.info(f"Environment: {settings.ENVIRONMENT}")
    app_logger.logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize database performance monitoring
    try:
        from app.core.database_performance import initialize_database_performance
        await initialize_database_performance()
        app_logger.logger.info("Database performance monitoring initialized")
    except Exception as e:
        app_logger.logger.error(f"Failed to initialize database performance monitoring: {str(e)}")

    # Warm connection pool
    try:
        from app.core.performance import warm_connection_pool
        await warm_connection_pool()
        app_logger.logger.info("Connection pool warmed")
    except Exception as e:
        app_logger.logger.error(f"Failed to warm connection pool: {str(e)}")
    
    # Initialize Redis caching
    try:
        from app.core.cache import cache_manager
        await cache_manager.connect()
        app_logger.logger.info("Redis caching initialized")
    except Exception as e:
        app_logger.logger.error(f"Failed to initialize Redis caching: {str(e)}")
    
    # Initialize monitoring and error tracking
    try:
        from app.core.monitoring import performance_monitor
        from app.core.error_tracking import error_tracker
        
        # Start performance monitoring
        await performance_monitor.start_monitoring()
        app_logger.logger.info("Performance monitoring started")
        
        # Initialize error tracking
        app_logger.logger.info("Error tracking initialized")
        
    except Exception as e:
        app_logger.logger.error(f"Failed to initialize monitoring: {str(e)}")
    
    yield
    
    # Shutdown
    try:
        from app.core.monitoring import performance_monitor
        await performance_monitor.stop_monitoring()
        app_logger.logger.info("Performance monitoring stopped")
    except Exception as e:
        app_logger.logger.error(f"Failed to stop monitoring: {str(e)}")
    
    try:
        from app.core.cache import cache_manager
        await cache_manager.disconnect()
        app_logger.logger.info("Redis caching disconnected")
    except Exception as e:
        app_logger.logger.error(f"Failed to disconnect Redis caching: {str(e)}")
    
    app_logger.logger.info("Shutting down RNR Financial Analysis Platform API")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="A comprehensive financial analysis platform for fundamental analysis, portfolio management, and market screening",
    lifespan=lifespan
)

# Add middleware (order matters — outermost first):
# 1. Error handling (outermost — catches everything)
# 2. Rate limiting
# 3. Consolidated (auth + timing + security headers)
# 4. Response compression
# 5. API response caching
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(
    RateLimitingMiddleware,
    requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    burst_limit=settings.RATE_LIMIT_BURST,
)
app.add_middleware(ConsolidatedMiddleware)
app.add_middleware(CompressionMiddleware)
app.add_middleware(
    CacheMiddleware,
    cache_ttl=300,
    cacheable_methods=["GET"],
    cacheable_paths=["/api/v1/companies", "/api/v1/market-data", "/api/v1/financial-statements"],
    excluded_paths=["/api/v1/auth/", "/api/v1/users/me", "/health"],
)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Global exception handler for BaseAPIException
@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    """Handle custom API exceptions"""
    app_logger.logger.warning(
        f"API Exception: {exc.error_code.value} - {exc.message}",
        extra={
            "error_code": exc.error_code.value,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers=exc.headers
    )

# Global exception handler for HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions"""
    app_logger.logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": {}
            }
        }
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to RNR Financial Analysis Platform API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs",
        "api_url": settings.API_V1_STR,
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    from app.core.database_performance import db_health_checker
    
    try:
        # Basic health check
        basic_health = {
            "status": "healthy",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Database health check
        db_health = await db_health_checker.check_database_health()
        
        # Combine health checks
        overall_status = "healthy"
        if db_health["status"] in ["unhealthy", "degraded"]:
            overall_status = db_health["status"]
        
        return {
            **basic_health,
            "status": overall_status,
            "services": {
                "api": "operational",
                "database": db_health["status"],
                "cache": "operational"  # Will be updated when Redis is implemented
            },
            "database_health": db_health
        }
        
    except Exception as e:
        app_logger.logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": "Health check failed"
        }


@app.get("/health/database")
async def database_health():
    """Detailed database health check"""
    from app.core.database_performance import db_health_checker, db_performance_monitor

    try:
        health_status = await db_health_checker.check_database_health()
        query_stats = await db_performance_monitor.get_query_statistics()
        pool_stats = await db_performance_monitor.get_connection_pool_stats()

        return {
            **health_status,
            "performance_metrics": {
                "query_statistics": query_stats,
                "connection_pool": pool_stats
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Database health check failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@app.get("/health/performance")
async def performance_stats():
    """Performance optimization statistics"""
    from app.core.performance import get_performance_stats
    return await get_performance_stats()


if __name__ == "__main__":
    import uvicorn
    import ssl

    # HTTPS configuration for production
    ssl_context = None
    if settings.ENVIRONMENT == "production":
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(
            certfile=settings.SSL_CERT_FILE,
            keyfile=settings.SSL_KEY_FILE
        )

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000 if settings.ENVIRONMENT != "production" else 443,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
        ssl_keyfile=settings.SSL_KEY_FILE if settings.ENVIRONMENT == "production" else None,
        ssl_certfile=settings.SSL_CERT_FILE if settings.ENVIRONMENT == "production" else None,
        ssl_version=ssl.PROTOCOL_TLS_SERVER if settings.ENVIRONMENT == "production" else None,
    )