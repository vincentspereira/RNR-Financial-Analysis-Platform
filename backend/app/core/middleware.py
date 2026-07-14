"""Middleware for the RNR Financial Analysis Platform"""
import time
import uuid
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.core.security import SecurityHeaders, RateLimiter
from app.core.logging import get_logger, request_id_var, user_id_var
from app.core.exceptions import RateLimitError, ErrorCode

# Initialize loggers
middleware_logger = get_logger("app.middleware")
security_logger = get_logger("app.security")
performance_logger = get_logger("app.performance")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""
    
    def __init__(self, app):
        super().__init__(app)
        self.security_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # HTTPS enforcement (only in production)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https: wss:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            # Permissions Policy (formerly Feature Policy)
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            ),
            # Hide server information
            "Server": "RNR-Financial-Analysis-Platform",
            # Prevent caching of sensitive data
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        # Add CSRF token header for API responses
        if request.url.path.startswith("/api/"):
            from app.core.security import CSRFProtection
            csrf_token = CSRFProtection.generate_csrf_token()
            response.headers["X-CSRF-Token"] = csrf_token
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging and timing"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        # Get client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        middleware_logger.logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "event_type": "request_start",
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "request_id": request_id
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            # Log request completion
            middleware_logger.log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                response_time_ms=process_time,
                ip_address=client_ip
            )
            
            # Log slow requests
            if process_time > 1000:  # Log requests slower than 1 second
                performance_logger.log_performance_issue(
                    operation=f"{request.method} {request.url.path}",
                    duration_ms=process_time,
                    threshold_ms=1000,
                    additional_data={
                        "client_ip": client_ip,
                        "user_agent": user_agent
                    }
                )
            
            return response
            
        except Exception as e:
            # Calculate response time for failed requests
            process_time = (time.time() - start_time) * 1000
            
            # Log error
            middleware_logger.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "event_type": "request_error",
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": client_ip,
                    "response_time_ms": process_time,
                    "error": str(e)
                },
                exc_info=True
            )
            
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers (when behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests"""
    
    def __init__(self, app, requests_per_minute: int = 60, burst_limit: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.rate_limiter = RateLimiter()
        
        # Track burst requests (short-term rate limiting)
        self.burst_tracker = defaultdict(list)
        self.burst_window_seconds = 10
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Get client identifier
        client_ip = self._get_client_ip(request)
        
        # Check burst limit (short-term)
        if self._is_burst_limited(client_ip):
            security_logger.log_security_event(
                event_type="rate_limit_burst",
                message=f"Burst rate limit exceeded for IP: {client_ip}",
                ip_address=client_ip,
                additional_data={
                    "path": request.url.path,
                    "method": request.method
                }
            )
            
            raise RateLimitError(
                message="Too many requests in short time period",
                retry_after=self.burst_window_seconds
            ).to_http_exception()
        
        # Check standard rate limit (per minute)
        if self.rate_limiter.is_rate_limited(client_ip, self.requests_per_minute, 1):
            security_logger.log_security_event(
                event_type="rate_limit_exceeded",
                message=f"Rate limit exceeded for IP: {client_ip}",
                ip_address=client_ip,
                additional_data={
                    "path": request.url.path,
                    "method": request.method,
                    "limit": self.requests_per_minute
                }
            )
            
            raise RateLimitError(
                message="Rate limit exceeded",
                retry_after=60
            ).to_http_exception()
        
        # Update burst tracker
        self._update_burst_tracker(client_ip)
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_burst_limited(self, client_ip: str) -> bool:
        """Check if client is burst limited"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.burst_window_seconds)
        
        # Clean old entries
        self.burst_tracker[client_ip] = [
            req_time for req_time in self.burst_tracker[client_ip]
            if req_time > window_start
        ]
        
        return len(self.burst_tracker[client_ip]) >= self.burst_limit
    
    def _update_burst_tracker(self, client_ip: str):
        """Update burst tracker with current request"""
        now = datetime.now(timezone.utc)
        self.burst_tracker[client_ip].append(now)


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with security considerations"""
    
    def __init__(
        self,
        app,
        allowed_origins: list = None,
        allowed_methods: list = None,
        allowed_headers: list = None,
        allow_credentials: bool = True,
        max_age: int = 86400
    ):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["http://localhost:3030"]
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = allowed_headers or [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-CSRF-Token"
        ]
        self.allow_credentials = allow_credentials
        self.max_age = max_age
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response, origin)
            return response
        
        # Process normal request
        response = await call_next(request)
        self._add_cors_headers(response, origin)
        
        return response
    
    def _add_cors_headers(self, response: Response, origin: Optional[str]):
        """Add CORS headers to response"""
        if origin and self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
        # For same-origin requests (no origin header), CORS headers are not needed
        # and must not be set to a wildcard value
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
        response.headers["Access-Control-Max-Age"] = str(self.max_age)
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed"""
        return origin in self.allowed_origins


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise
        except Exception as e:
            # Log unexpected errors
            middleware_logger.logger.error(
                f"Unhandled exception in {request.method} {request.url.path}",
                extra={
                    "event_type": "unhandled_exception",
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
            
            # Return generic error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "SYS_005",
                        "message": "An internal server error occurred",
                        "details": {}
                    }
                }
            )


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication context"""
    
    def __init__(self, app, excluded_paths: list = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/",
            "/health",
            "/api/v1/health",
            "/api/v1/status", 
            "/api/v1/openapi.json",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register"
        ]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip authentication for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Extract and verify JWT token
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Missing or invalid authorization header"}
            )
        
        try:
            token = auth_header.split(" ")[1]
            
            # Import here to avoid circular imports
            from app.services.auth.jwt_handler import jwt_handler
            
            # Verify the token
            payload = jwt_handler.verify_token(token)
            if not payload:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"error": "Invalid or expired token"}
                )
            
            # Set user context
            user_id = payload.get("sub")
            if user_id:
                user_id_var.set(user_id)
                
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Token verification failed"}
            )
        
        return await call_next(request)
