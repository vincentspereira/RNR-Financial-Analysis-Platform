"""
Test configuration and fixtures for Phase 2 backend tests
"""
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import Base, get_async_session


# Use SQLite for testing (no external DB dependency needed)
TEST_DB_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for test session"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session"""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with DB session override"""
    from app.main import app

    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis():
    """Create a mock Redis client for testing"""
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.ttl = AsyncMock(return_value=-1)
    redis_mock.pipeline = MagicMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()

    # Pipeline mock
    pipe_mock = MagicMock()
    pipe_mock.zremrangebyscore = MagicMock(return_value=pipe_mock)
    pipe_mock.zadd = MagicMock(return_value=pipe_mock)
    pipe_mock.zcard = MagicMock(return_value=pipe_mock)
    pipe_mock.expire = MagicMock(return_value=pipe_mock)
    pipe_mock.execute = AsyncMock(return_value=[0, 1, 1, True])
    redis_mock.pipeline.return_value = pipe_mock

    return redis_mock


@pytest.fixture
def sample_user_data():
    """Sample user registration data"""
    return {
        "email": f"test_{uuid4().hex[:8]}@test.com",
        "password": "TestPass123!@#",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio creation data"""
    return {
        "name": "Test Portfolio",
        "description": "A test portfolio",
        "cash_balance": "10000.00",
    }


@pytest.fixture
def sample_holding_data():
    """Sample holding data"""
    return {
        "symbol": "AAPL",
        "quantity": "10",
        "purchase_price": "150.00",
        "current_price": "175.00",
        "purchase_date": "2024-01-15",
    }
