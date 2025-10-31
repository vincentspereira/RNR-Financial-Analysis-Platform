"""
Configuration settings for the Financial Analysis Platform
"""
import os
import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, field_validator, ConfigDict
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
    DEBUG: bool = True

    # Security - CRITICAL: Use environment variables for production
    SECRET_KEY: str = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
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

    # SSL/HTTPS Configuration (for production)
    SSL_CERT_FILE: Optional[str] = os.getenv("SSL_CERT_FILE")
    SSL_KEY_FILE: Optional[str] = os.getenv("SSL_KEY_FILE")
    FORCE_HTTPS: bool = os.getenv("FORCE_HTTPS", "false").lower() == "true"


# Create global settings instance
settings = Settings()
