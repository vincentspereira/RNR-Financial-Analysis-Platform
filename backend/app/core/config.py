"""
Configuration settings for the Financial Analysis Platform
"""
import os
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, field_validator, ConfigDict, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Basic settings
    PROJECT_NAME: str = "Financial Analysis Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Security - CRITICAL: Must be set via environment variable or .env file
    SECRET_KEY: str = ""

    @model_validator(mode="after")
    def validate_secret_key(self):
        if not self.SECRET_KEY or self.SECRET_KEY == "change-me-to-a-random-string":
            raise ValueError(
                "SECRET_KEY must be set in environment or .env file. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return self
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: Optional[str] = None
    TEST_DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS - Secure defaults
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # External APIs - Use environment variables
    ALPHA_VANTAGE_API_KEY: Optional[str] = os.getenv("ALPHA_VANTAGE_API_KEY")
    FINANCIAL_MODELING_PREP_API_KEY: Optional[str] = os.getenv("FINANCIAL_MODELING_PREP_API_KEY")

    # Market Data Streaming
    POLYGON_API_KEY: Optional[str] = os.getenv("POLYGON_API_KEY")
    POLYGON_WEBSOCKET_URL: str = "wss://socket.polygon.io/stocks"
    IEX_API_KEY: Optional[str] = os.getenv("IEX_API_KEY")
    IEX_WEBSOCKET_URL: str = "wss://cloud.iexapis.com/v1/stocks"

    # Sentiment / News
    NEWSAPI_KEY: Optional[str] = os.getenv("NEWSAPI_KEY")
    FINNHUB_API_KEY: Optional[str] = os.getenv("FINNHUB_API_KEY")

    # Stripe Billing
    STRIPE_API_KEY: Optional[str] = os.getenv("STRIPE_API_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET")

    # Email (for future use)
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[EmailStr] = None
    SMTP_PASSWORD: Optional[str] = None

    # Security settings
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 30

    # Cache settings
    CACHE_EXPIRE_SECONDS: int = 3600

    # Task queue
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None

    # Database performance settings
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    DATABASE_STATEMENT_CACHE_SIZE: int = 100

    # Response compression
    COMPRESS_MIN_SIZE: int = 500
    COMPRESS_GZIP_LEVEL: int = 6

    # Performance monitoring
    PERFORMANCE_TARGET_MS: int = 50
    SLOW_QUERY_THRESHOLD_MS: int = 100

    # SSL/HTTPS Configuration (for production)
    SSL_CERT_FILE: Optional[str] = os.getenv("SSL_CERT_FILE")
    SSL_KEY_FILE: Optional[str] = os.getenv("SSL_KEY_FILE")
    FORCE_HTTPS: bool = os.getenv("FORCE_HTTPS", "false").lower() == "true"

    # ---------------------------------------------------------------------
    # Interactive Brokers (IBKR) integration
    # ---------------------------------------------------------------------
    # When enabled, the backend connects to a locally-running TWS or IB
    # Gateway via the ib-async library. Default 7497 = TWS Paper Trading.
    IBKR_ENABLED: bool = os.getenv("IBKR_ENABLED", "false").lower() == "true"
    IBKR_HOST: str = os.getenv("IBKR_HOST", "127.0.0.1")
    IBKR_PORT: int = int(os.getenv("IBKR_PORT", "7497"))
    IBKR_CLIENT_ID: int = int(os.getenv("IBKR_CLIENT_ID", "42"))
    IBKR_ACCOUNT_ID: Optional[str] = os.getenv("IBKR_ACCOUNT_ID") or None
    IBKR_READONLY: bool = os.getenv("IBKR_READONLY", "true").lower() == "true"
    IBKR_RECONNECT_DELAY_SECONDS: int = int(os.getenv("IBKR_RECONNECT_DELAY_SECONDS", "5"))
    IBKR_MAX_RECONNECT_ATTEMPTS: int = int(os.getenv("IBKR_MAX_RECONNECT_ATTEMPTS", "10"))
    # Safety brakes — per-user, rolling UTC day
    IBKR_ORDER_DAILY_LIMIT: int = int(os.getenv("IBKR_ORDER_DAILY_LIMIT", "50"))
    IBKR_ORDER_NOTIONAL_LIMIT_USD: float = float(
        os.getenv("IBKR_ORDER_NOTIONAL_LIMIT_USD", "100000")
    )


# Create global settings instance
settings = Settings()
