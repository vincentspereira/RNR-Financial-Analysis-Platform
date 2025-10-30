"""
Configuration settings for the Financial Analysis Platform
"""
import os
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Basic settings
    PROJECT_NAME: str = "Financial Analysis Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: Optional[str] = None
    TEST_DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # External APIs
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    FINANCIAL_MODELING_PREP_API_KEY: Optional[str] = None

    # Email (for future use)
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[EmailStr] = None
    SMTP_PASSWORD: Optional[str] = None

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Cache settings
    CACHE_EXPIRE_SECONDS: int = 3600

    # Task queue
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()