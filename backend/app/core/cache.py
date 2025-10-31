"""
Redis caching layer for the Financial Analysis Platform
"""
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from functools import wraps
import hashlib

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import get_logger

# Get cache logger
cache_logger = get_logger("app.cache")


class CacheManager:
    """Redis cache manager with advanced features"""
    
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self._connected = False
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,  # We'll handle encoding ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            cache_logger.logger.info("Redis connection established")
            
        except Exception as e:
            cache_logger.logger.error(f"Failed to connect to Redis: {str(e)}")
            self._connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self._connected = False
            cache_logger.logger.info("Redis connection closed")
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value).encode('utf-8')
        else:
            return pickle.dumps(value)
    
    def _deserialize_value(self, value: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            # Try JSON first (for simple types)
            return json.loads(value.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle for complex objects
            return pickle.loads(value)
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))
        
        # Add keyword arguments (sorted for consistency)
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        # Create hash for very long keys
        key = ":".join(key_parts)
        if len(key) > 200:  # Redis key length limit consideration
            key_hash = hashlib.md5(key.encode()).hexdigest()
            key = f"{prefix}:hash:{key_hash}"
        
        return key
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._connected:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value is None:
                cache_logger.logger.debug(f"Cache miss: {key}")
                return None
            
            cache_logger.logger.debug(f"Cache hit: {key}")
            return self._deserialize_value(value)
            
        except Exception as e:
            cache_logger.logger.error(f"Cache get error for key {key}: {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """Set value in cache"""
        if not self._connected:
            return False
        
        try:
            serialized_value = self._serialize_value(value)
            
            result = await self.redis_client.set(
                key,
                serialized_value,
                ex=expire or settings.CACHE_EXPIRE_SECONDS,
                nx=nx,
                xx=xx
            )
            
            if result:
                cache_logger.logger.debug(f"Cache set: {key} (expire: {expire or settings.CACHE_EXPIRE_SECONDS}s)")
            
            return bool(result)
            
        except Exception as e:
            cache_logger.logger.error(f"Cache set error for key {key}: {str(e)}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """Delete keys from cache"""
        if not self._connected or not keys:
            return 0
        
        try:
            result = await self.redis_client.delete(*keys)
            cache_logger.logger.debug(f"Cache delete: {keys} (deleted: {result})")
            return result
            
        except Exception as e:
            cache_logger.logger.error(f"Cache delete error for keys {keys}: {str(e)}")
            return 0
    
    async def exists(self, *keys: str) -> int:
        """Check if keys exist in cache"""
        if not self._connected or not keys:
            return 0
        
        try:
            return await self.redis_client.exists(*keys)
        except Exception as e:
            cache_logger.logger.error(f"Cache exists error for keys {keys}: {str(e)}")
            return 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key"""
        if not self._connected:
            return False
        
        try:
            result = await self.redis_client.expire(key, seconds)
            return bool(result)
        except Exception as e:
            cache_logger.logger.error(f"Cache expire error for key {key}: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        if not self._connected:
            return -1
        
        try:
            return await self.redis_client.ttl(key)
        except Exception as e:
            cache_logger.logger.error(f"Cache TTL error for key {key}: {str(e)}")
            return -1
    
    async def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self._connected:
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                result = await self.redis_client.delete(*keys)
                cache_logger.logger.info(f"Flushed {result} keys matching pattern: {pattern}")
                return result
            return 0
        except Exception as e:
            cache_logger.logger.error(f"Cache flush pattern error for {pattern}: {str(e)}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._connected:
            return {"connected": False}
        
        try:
            info = await self.redis_client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }
        except Exception as e:
            cache_logger.logger.error(f"Cache stats error: {str(e)}")
            return {"connected": False, "error": str(e)}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate"""
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0


# Global cache manager instance
cache_manager = CacheManager()


class CacheStrategies:
    """Predefined caching strategies for different data types"""
    
    # Financial data caching (longer TTL for historical data)
    FINANCIAL_DATA = {
        "expire": 3600,  # 1 hour
        "prefix": "financial_data"
    }
    
    # Company information (medium TTL)
    COMPANY_INFO = {
        "expire": 1800,  # 30 minutes
        "prefix": "company_info"
    }
    
    # Market data (short TTL for real-time data)
    MARKET_DATA = {
        "expire": 300,  # 5 minutes
        "prefix": "market_data"
    }
    
    # User sessions (custom TTL)
    USER_SESSION = {
        "expire": 1800,  # 30 minutes
        "prefix": "user_session"
    }
    
    # API responses (very short TTL)
    API_RESPONSE = {
        "expire": 60,  # 1 minute
        "prefix": "api_response"
    }
    
    # Calculation results (medium TTL)
    CALCULATIONS = {
        "expire": 900,  # 15 minutes
        "prefix": "calculations"
    }


def cached(
    strategy: Dict[str, Any] = None,
    key_prefix: str = None,
    expire: int = None,
    skip_cache: bool = False
):
    """
    Decorator for caching function results
    
    Args:
        strategy: Predefined caching strategy
        key_prefix: Custom key prefix
        expire: Custom expiration time
        skip_cache: Skip caching (useful for debugging)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if skip_cache or not cache_manager._connected:
                return await func(*args, **kwargs)
            
            # Determine cache settings
            if strategy:
                cache_prefix = strategy["prefix"]
                cache_expire = strategy["expire"]
            else:
                cache_prefix = key_prefix or func.__name__
                cache_expire = expire or settings.CACHE_EXPIRE_SECONDS
            
            # Generate cache key
            cache_key = cache_manager._generate_key(cache_prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                await cache_manager.set(cache_key, result, expire=cache_expire)
            
            return result
        
        return wrapper
    return decorator


# Convenience functions for common caching patterns
async def cache_financial_data(key: str, data: Any, expire: int = None) -> bool:
    """Cache financial data with appropriate TTL"""
    return await cache_manager.set(
        cache_manager._generate_key(CacheStrategies.FINANCIAL_DATA["prefix"], key),
        data,
        expire=expire or CacheStrategies.FINANCIAL_DATA["expire"]
    )


async def get_cached_financial_data(key: str) -> Optional[Any]:
    """Get cached financial data"""
    return await cache_manager.get(
        cache_manager._generate_key(CacheStrategies.FINANCIAL_DATA["prefix"], key)
    )


async def cache_company_info(symbol: str, data: Any) -> bool:
    """Cache company information"""
    return await cache_manager.set(
        cache_manager._generate_key(CacheStrategies.COMPANY_INFO["prefix"], symbol),
        data,
        expire=CacheStrategies.COMPANY_INFO["expire"]
    )


async def get_cached_company_info(symbol: str) -> Optional[Any]:
    """Get cached company information"""
    return await cache_manager.get(
        cache_manager._generate_key(CacheStrategies.COMPANY_INFO["prefix"], symbol)
    )


async def invalidate_company_cache(symbol: str) -> int:
    """Invalidate all cache entries for a company"""
    patterns = [
        f"{CacheStrategies.COMPANY_INFO['prefix']}:{symbol}*",
        f"{CacheStrategies.FINANCIAL_DATA['prefix']}:{symbol}*",
        f"{CacheStrategies.MARKET_DATA['prefix']}:{symbol}*",
        f"{CacheStrategies.CALCULATIONS['prefix']}:{symbol}*"
    ]
    
    total_deleted = 0
    for pattern in patterns:
        deleted = await cache_manager.flush_pattern(pattern)
        total_deleted += deleted
    
    cache_logger.logger.info(f"Invalidated {total_deleted} cache entries for {symbol}")
    return total_deleted


# Initialize cache connection on module import
async def init_cache():
    """Initialize cache connection"""
    try:
        await cache_manager.connect()
    except Exception as e:
        cache_logger.logger.warning(f"Cache initialization failed: {str(e)}")


# Cleanup function
async def cleanup_cache():
    """Cleanup cache connection"""
    await cache_manager.disconnect()
