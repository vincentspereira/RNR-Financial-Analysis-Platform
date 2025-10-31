"""
Caching middleware for automatic API response caching
"""
import json
import hashlib
from typing import Dict, List, Optional, Set
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.cache import cache_manager
from app.core.logging import get_logger

cache_logger = get_logger("cache.middleware")


class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic API response caching"""
    
    def __init__(
        self,
        app,
        cache_ttl: int = 300,  # 5 minutes default
        cacheable_methods: List[str] = None,
        cacheable_paths: List[str] = None,
        excluded_paths: List[str] = None,
        cache_headers: bool = True
    ):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.cacheable_methods = cacheable_methods or ["GET"]
        self.cacheable_paths = cacheable_paths or ["/api/v1/"]
        self.excluded_paths = excluded_paths or [
            "/api/v1/auth/",
            "/api/v1/users/me",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        self.cache_headers = cache_headers
        
        # Cache invalidation patterns
        self.invalidation_patterns = {
            "companies": ["companies", "market-data", "financial-statements"],
            "portfolios": ["portfolios", "transactions", "positions"],
            "users": ["users", "sessions"],
            "market-data": ["market-data", "companies"],
            "financial-statements": ["financial-statements", "companies"]
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check if request should be cached
        if not self._should_cache_request(request):
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try to get cached response
        try:
            cached_response = await cache_manager.get(cache_key)
            if cached_response:
                cache_logger.debug(f"Cache hit for key: {cache_key}")
                
                # Parse cached response
                cached_data = json.loads(cached_response)
                response = JSONResponse(
                    content=cached_data["content"],
                    status_code=cached_data["status_code"],
                    headers=cached_data.get("headers", {})
                )
                
                # Add cache headers
                if self.cache_headers:
                    response.headers["X-Cache"] = "HIT"
                    response.headers["X-Cache-Key"] = cache_key
                
                return response
                
        except Exception as e:
            cache_logger.warning(f"Cache retrieval failed for key {cache_key}: {str(e)}")
        
        # Execute request
        response = await call_next(request)
        
        # Cache successful responses
        if self._should_cache_response(response):
            try:
                await self._cache_response(cache_key, response, request)
                cache_logger.debug(f"Cached response for key: {cache_key}")
                
                # Add cache headers
                if self.cache_headers:
                    response.headers["X-Cache"] = "MISS"
                    response.headers["X-Cache-Key"] = cache_key
                    
            except Exception as e:
                cache_logger.warning(f"Cache storage failed for key {cache_key}: {str(e)}")
        
        return response
    
    def _should_cache_request(self, request: Request) -> bool:
        """Determine if request should be cached"""
        # Check HTTP method
        if request.method not in self.cacheable_methods:
            return False
        
        # Check if path is excluded
        for excluded_path in self.excluded_paths:
            if request.url.path.startswith(excluded_path):
                return False
        
        # Check if path is cacheable
        for cacheable_path in self.cacheable_paths:
            if request.url.path.startswith(cacheable_path):
                return True
        
        return False
    
    def _should_cache_response(self, response: Response) -> bool:
        """Determine if response should be cached"""
        # Only cache successful responses
        if response.status_code not in [200, 201]:
            return False
        
        # Don't cache responses with certain headers
        if "no-cache" in response.headers.get("cache-control", "").lower():
            return False
        
        return True
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key for request"""
        # Include path, query parameters, and user context
        key_components = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items())),
        ]
        
        # Include user ID if available (for user-specific caching)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            key_components.append(f"user:{user_id}")
        
        # Create hash of components
        key_string = "|".join(key_components)
        cache_key = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"api_cache:{cache_key}"
    
    async def _cache_response(self, cache_key: str, response: Response, request: Request):
        """Cache response data"""
        # Read response body
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        
        # Parse response content
        try:
            content = json.loads(response_body.decode())
        except json.JSONDecodeError:
            content = response_body.decode()
        
        # Prepare cache data
        cache_data = {
            "content": content,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "cached_at": cache_manager._get_current_timestamp(),
            "request_path": request.url.path
        }
        
        # Determine TTL based on endpoint
        ttl = self._get_cache_ttl(request.url.path)
        
        # Store in cache
        await cache_manager.set(
            cache_key,
            json.dumps(cache_data, default=str),
            expire=ttl
        )
        
        # Create new response with same content
        response.body_iterator = self._create_body_iterator(response_body)
    
    def _create_body_iterator(self, body: bytes):
        """Create body iterator for response"""
        async def generate():
            yield body
        return generate()
    
    def _get_cache_ttl(self, path: str) -> int:
        """Get cache TTL based on endpoint"""
        # Different TTLs for different types of data
        if "/companies" in path:
            return 3600  # 1 hour for company data
        elif "/market-data" in path:
            return 300   # 5 minutes for market data
        elif "/financial-statements" in path:
            return 1800  # 30 minutes for financial statements
        elif "/portfolios" in path:
            return 60    # 1 minute for portfolio data
        else:
            return self.cache_ttl


class CacheInvalidationManager:
    """Manages cache invalidation strategies"""
    
    def __init__(self):
        self.invalidation_patterns = {
            # When companies are updated, invalidate related caches
            "companies": [
                "api_cache:*companies*",
                "api_cache:*market-data*",
                "api_cache:*financial-statements*"
            ],
            # When portfolios are updated, invalidate portfolio caches
            "portfolios": [
                "api_cache:*portfolios*",
                "api_cache:*transactions*",
                "api_cache:*positions*"
            ],
            # When market data is updated, invalidate market and company caches
            "market-data": [
                "api_cache:*market-data*",
                "api_cache:*companies*"
            ],
            # When financial statements are updated
            "financial-statements": [
                "api_cache:*financial-statements*",
                "api_cache:*companies*"
            ]
        }
    
    async def invalidate_cache_patterns(self, resource_type: str, resource_id: Optional[str] = None):
        """Invalidate cache patterns for a resource type"""
        try:
            patterns = self.invalidation_patterns.get(resource_type, [])
            
            for pattern in patterns:
                # If resource_id is provided, create more specific pattern
                if resource_id:
                    specific_pattern = pattern.replace("*", f"*{resource_id}*")
                    await cache_manager.flush_pattern(specific_pattern)
                
                # Always invalidate general pattern
                await cache_manager.flush_pattern(pattern)
            
            cache_logger.info(f"Invalidated cache patterns for {resource_type}")
            
        except Exception as e:
            cache_logger.error(f"Failed to invalidate cache patterns for {resource_type}: {str(e)}")
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a specific user"""
        try:
            pattern = f"api_cache:*user:{user_id}*"
            await cache_manager.flush_pattern(pattern)
            cache_logger.info(f"Invalidated cache for user {user_id}")
            
        except Exception as e:
            cache_logger.error(f"Failed to invalidate user cache for {user_id}: {str(e)}")
    
    async def invalidate_all_cache(self):
        """Invalidate all API cache entries"""
        try:
            await cache_manager.flush_pattern("api_cache:*")
            cache_logger.info("Invalidated all API cache entries")
            
        except Exception as e:
            cache_logger.error(f"Failed to invalidate all cache: {str(e)}")


# Global cache invalidation manager
cache_invalidation_manager = CacheInvalidationManager()


# Decorator for automatic cache invalidation
def invalidate_cache(resource_type: str):
    """Decorator to automatically invalidate cache after function execution"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Invalidate cache patterns
            await cache_invalidation_manager.invalidate_cache_patterns(resource_type)
            
            return result
        return wrapper
    return decorator


# Cache warming utilities
class CacheWarmer:
    """Utilities for cache warming"""
    
    @staticmethod
    async def warm_company_cache(company_symbols: List[str]):
        """Pre-warm cache for company data"""
        try:
            from app.services.data.company_service import CompanyService
            
            company_service = CompanyService()
            
            for symbol in company_symbols:
                # Warm basic company data
                await company_service.get_company_by_symbol(symbol)
                
                # Warm market data
                await company_service.get_latest_market_data(symbol)
                
                # Warm financial statements
                await company_service.get_latest_financial_statements(symbol)
            
            cache_logger.info(f"Warmed cache for {len(company_symbols)} companies")
            
        except Exception as e:
            cache_logger.error(f"Failed to warm company cache: {str(e)}")
    
    @staticmethod
    async def warm_user_portfolio_cache(user_id: str):
        """Pre-warm cache for user portfolio data"""
        try:
            from app.services.portfolio.portfolio_service import PortfolioService
            
            portfolio_service = PortfolioService()
            
            # Warm user portfolios
            await portfolio_service.get_user_portfolios(user_id)
            
            # Warm portfolio positions
            portfolios = await portfolio_service.get_user_portfolios(user_id)
            for portfolio in portfolios:
                await portfolio_service.get_portfolio_positions(portfolio.id)
            
            cache_logger.info(f"Warmed cache for user {user_id} portfolios")
            
        except Exception as e:
            cache_logger.error(f"Failed to warm user portfolio cache: {str(e)}")


# Global cache warmer
cache_warmer = CacheWarmer()
