"""  
Pytest configuration and fixtures for the RNR Financial Analysis Platform
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_async_session
from app.models.user import User
from app.models.company import Company
from app.services.auth.jwt_handler import jwt_handler


# Configure pytest-asyncio
pytest_asyncio.asyncio_mode = "auto"

# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
TEST_SYNC_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Database fixtures
# Create test engines
test_async_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

test_sync_engine = create_engine(
    TEST_SYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# Create test session makers
TestAsyncSessionLocal = async_sessionmaker(
    test_async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest.fixture(scope="function")
async def async_engine():
    """Create async test database engine"""
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async test database session"""
    async_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
def override_get_async_session(async_session):
    """Override the get_async_session dependency"""
    async def _override_get_async_session():
        yield async_session
    
    return _override_get_async_session


@pytest.fixture(scope="function")
def test_client(override_get_async_session):
    """Create test client with database override"""
    app.dependency_overrides[get_async_session] = override_get_async_session
    
    with TestClient(app) as client:
        yield client
    
    # Clean up
    app.dependency_overrides.clear()


# User fixtures
@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User"
    }


@pytest.fixture
async def test_user(async_session, test_user_data) -> User:
    """Create a test user in the database"""
    from app.services.auth.password_handler import password_handler
    
    user = User(
        id=uuid4(),
        email=test_user_data["email"],
        password_hash=password_handler.hash_password(test_user_data["password"]),
        first_name=test_user_data["first_name"],
        last_name=test_user_data["last_name"],
        is_active=True,
        is_verified=True,
        is_superuser=False
    )
    
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    
    return user


@pytest.fixture
def test_user_token(test_user) -> str:
    """Create JWT token for test user"""
    return jwt_handler.create_access_token(test_user.id)


@pytest.fixture
def auth_headers(test_user_token) -> dict:
    """Create authorization headers for test requests"""
    return {"Authorization": f"Bearer {test_user_token}"}


# Company fixtures
@pytest.fixture
def test_company_data():
    """Test company data"""
    return {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap": 3000000000000,  # 3 trillion
        "employees": 164000,
        "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.",
        "website": "https://www.apple.com",
        "headquarters": "Cupertino, CA, USA"
    }


@pytest.fixture
async def test_company(async_session, test_company_data) -> Company:
    """Create a test company in the database"""
    company = Company(
        id=uuid4(),
        **test_company_data
    )
    
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)
    
    return company


# Mock fixtures
@pytest.fixture
def mock_alpha_vantage_client():
    """Mock Alpha Vantage client"""
    mock_client = AsyncMock()
    
    # Mock successful responses
    mock_client.get_company_overview.return_value = {
        "Symbol": "AAPL",
        "Name": "Apple Inc.",
        "Exchange": "NASDAQ",
        "Sector": "Technology",
        "Industry": "Consumer Electronics",
        "MarketCapitalization": "3000000000000"
    }
    
    mock_client.get_income_statement.return_value = [
        {
            "fiscalDateEnding": "2023-09-30",
            "reportedCurrency": "USD",
            "totalRevenue": "383285000000",
            "grossProfit": "169148000000",
            "netIncome": "96995000000"
        }
    ]
    
    mock_client.get_balance_sheet.return_value = [
        {
            "fiscalDateEnding": "2023-09-30",
            "reportedCurrency": "USD",
            "totalAssets": "352755000000",
            "totalLiabilities": "290437000000",
            "totalShareholderEquity": "62318000000"
        }
    ]
    
    mock_client.get_daily_prices.return_value = {
        "prices": [
            {
                "date": "2023-12-01",
                "open": 189.84,
                "high": 190.32,
                "low": 188.19,
                "close": 189.95,
                "volume": 46278900
            }
        ]
    }
    
    return mock_client


@pytest.fixture
def mock_yahoo_finance_client():
    """Mock Yahoo Finance client"""
    mock_client = AsyncMock()
    
    mock_client.get_stock_info.return_value = {
        "symbol": "AAPL",
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        "currentPrice": 189.95,
        "marketCap": 3000000000000,
        "volume": 46278900
    }
    
    return mock_client


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock_redis = MagicMock()
    
    # Mock Redis operations
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = False
    
    return mock_redis


# Performance testing fixtures
@pytest.fixture
def performance_threshold():
    """Performance thresholds for testing"""
    return {
        "api_response_time_ms": 500,
        "database_query_time_ms": 200,
        "calculation_time_ms": 100
    }


# Security testing fixtures
@pytest.fixture
def security_test_data():
    """Security test data"""
    return {
        "sql_injection_payloads": [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ],
        "xss_payloads": [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//"
        ],
        "invalid_tokens": [
            "invalid.jwt.token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
            "Bearer invalid_token"
        ]
    }


# Utility fixtures
@pytest.fixture
def sample_financial_data():
    """Sample financial data for testing calculations"""
    return {
        "total_revenue": 383285000000,
        "gross_profit": 169148000000,
        "operating_income": 114301000000,
        "net_income": 96995000000,
        "total_assets": 352755000000,
        "total_liabilities": 290437000000,
        "shareholders_equity": 62318000000,
        "current_assets": 143566000000,
        "current_liabilities": 145308000000,
        "cash_and_equivalents": 29965000000,
        "total_debt": 123930000000,
        "shares_outstanding": 15728700000,
        "stock_price": 189.95
    }


@pytest.fixture
def mock_external_apis(mock_alpha_vantage_client, mock_yahoo_finance_client):
    """Mock all external API clients"""
    return {
        "alpha_vantage": mock_alpha_vantage_client,
        "yahoo_finance": mock_yahoo_finance_client
    }


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test"""
    yield
    # Perform any necessary cleanup here
    pass


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "system: System/End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "uat: User Acceptance Tests")
    config.addinivalue_line("markers", "contract: Contract tests")
    config.addinivalue_line("markers", "chaos: Chaos engineering tests")
    config.addinivalue_line("markers", "compliance: Compliance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "fast: Fast running tests")
    config.addinivalue_line("markers", "smoke: Smoke tests")
    config.addinivalue_line("markers", "regression: Regression tests")
    config.addinivalue_line("markers", "critical: Critical path tests")
    config.addinivalue_line("markers", "monitoring: Monitoring module tests")
    config.addinivalue_line("markers", "autoscaling: Autoscaling module tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "database: Database tests")
    config.addinivalue_line("markers", "external: External service tests")
    config.addinivalue_line("markers", "benchmark: Benchmark tests")
    config.addinivalue_line("markers", "penetration: Penetration tests")
    config.addinivalue_line("markers", "encryption: Encryption tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location"""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
            item.add_marker(pytest.mark.fast)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "system" in str(item.fspath):
            item.add_marker(pytest.mark.system)
            item.add_marker(pytest.mark.slow)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        elif "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        
        # Add markers based on test name patterns
        if "test_auth" in item.name or "test_login" in item.name:
            item.add_marker(pytest.mark.security)
        elif "test_performance" in item.name or "test_benchmark" in item.name:
            item.add_marker(pytest.mark.performance)
        elif "test_database" in item.name or "test_db" in item.name:
            item.add_marker(pytest.mark.database)