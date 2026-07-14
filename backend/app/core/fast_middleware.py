"""
Consolidated performance middleware — merges request logging,
timing, and security headers into a single middleware layer to
avoid the overhead of N stacked BaseHTTPMiddleware instances.
"""
import time
import uuid
from typing import Set

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.logging import get_logger, request_id_var, user_id_var
from app.core.security import CSRFProtection
from app.core.config import settings

perf_logger = get_logger("app.performance")
mw_logger = get_logger("app.middleware")

# Paths that skip auth
PUBLIC_PATHS: Set[str] = {
    "/", "/health", "/health/database",
    "/api/v1/health", "/api/v1/status",
    "/docs", "/redoc", "/openapi.json",
    "/api/v1/openapi.json",
    "/api/v1/auth/login", "/api/v1/auth/register",
}

SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Permissions-Policy": (
        "geolocation=(), microphone=(), camera=(), payment=(), "
        "usb=(), magnetometer=(), gyroscope=(), speaker=()"
    ),
    "Server": "RNR-Financial-Analysis-Platform",
}


class ConsolidatedMiddleware(BaseHTTPMiddleware):
    """Single middleware that handles timing, logging, security headers, and auth."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)

        start = time.perf_counter()

        # --- Authentication (fast path for public endpoints) ---
        if request.url.path not in PUBLIC_PATHS:
            auth = request.headers.get("authorization")
            if not auth or not auth.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"error": "Missing or invalid authorization header"},
                )
            try:
                token = auth.split(" ")[1]
                from app.services.auth.jwt_handler import jwt_handler
                payload = jwt_handler.verify_token(token)
                if not payload:
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Invalid or expired token"},
                    )
                uid = payload.get("sub")
                if uid:
                    user_id_var.set(uid)
            except Exception:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Token verification failed"},
                )

        # --- Execute request ---
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            perf_logger.logger.error(
                "Unhandled exception %s %s %.1fms",
                request.method, request.url.path, elapsed_ms,
                exc_info=True,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000

        # --- Timing / request-id headers ---
        response.headers["X-Process-Time"] = f"{elapsed_ms:.1f}"
        response.headers["X-Request-ID"] = request_id

        # --- Security headers ---
        for k, v in SECURITY_HEADERS.items():
            response.headers[k] = v

        # CSRF token for API paths
        if request.url.path.startswith("/api/"):
            response.headers["X-CSRF-Token"] = CSRFProtection.generate_csrf_token()

        # --- Slow request logging ---
        if elapsed_ms > settings.PERFORMANCE_TARGET_MS * 2:
            perf_logger.logger.warning(
                "Slow request: %s %s %.1fms (target: %dms)",
                request.method, request.url.path, elapsed_ms,
                settings.PERFORMANCE_TARGET_MS,
            )

        return response
