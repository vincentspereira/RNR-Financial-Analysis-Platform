"""
Database configuration and connection management for RNR Financial Analysis Platform
"""
import os
from typing import AsyncGenerator

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings
from app.core.logging import get_logger

# Get database logger
db_logger = get_logger("app.database")

# Database URL configuration
DATABASE_URL = settings.DATABASE_URL or "postgresql://dev:dev@localhost:5432/financial_analysis_dev"
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine for main database operations with optimized settings
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_timeout=30,
    # Prepared statement cache — avoids re-parsing queries
    connect_args={
        "statement_cache_size": settings.DATABASE_STATEMENT_CACHE_SIZE,
        "server_settings": {
            "application_name": "rnr_financial_analysis_platform",
            "jit": "off",
            "tcp_keepalives_idle": "60",
            "tcp_keepalives_interval": "10",
            "tcp_keepalives_count": "5",
        },
    },
)

# Create sync engine for migrations
sync_engine = create_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_timeout=30,
    connect_args={
        "application_name": "rnr_financial_analysis_platform_sync"
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create sync session factory for migrations
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

# Metadata for table creation with optimized naming convention
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

# Base class for all models
Base = declarative_base(metadata=metadata)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get async database session
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            db_logger.logger.debug("Database session created")
            yield session
        except Exception as e:
            db_logger.logger.error(f"Database session error: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()
            db_logger.logger.debug("Database session closed")


async def check_database_connection() -> bool:
    """
    Check database connection health
    
    Returns:
        bool: True if connection is healthy
    """
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        db_logger.logger.info("Database connection check: OK")
        return True
    except Exception as e:
        db_logger.logger.error(f"Database connection check failed: {str(e)}")
        return False


async def get_database_stats() -> dict:
    """
    Get database connection pool statistics
    
    Returns:
        dict: Database statistics
    """
    pool = async_engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid(),
    }


def get_sync_session():
    """
    Get sync database session for migrations and testing
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def init_db():
    """
    Initialize database tables
    """
    async with async_engine.begin() as conn:
        # Import all models to ensure they are registered
        from app.models import (  # noqa: F401
            audit,
            company,
            financial_data,
            portfolio,
            user,
        )
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    Close database connections
    """
    await async_engine.dispose()


# Alias for backward compatibility
def get_db():
    """
    Alias for get_async_session for backward compatibility
    """
    return get_async_session()
