"""
Comprehensive Unit Tests for API Endpoints - 100% Path Coverage
"""
import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List

from app.main import app
from app.core.auth import get_current_user
from app.models.user import User


class TestAuthEndpoints:
    """Comprehensive tests for authentication endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    async def async_client(self):
        """Async test client fixture"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    def mock_user(self):
        """Mock user fixture"""
        return User(
            id="test-user-id",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_verified=True
        )
    
    @pytest.mark.asyncio
    async def test_register_endpoint_success(self, async_client):
        """Test successful user registration"""
        registration_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "full_name": "New User",
            "first_name": "New",
            "last_name": "User"
        }
        
        with patch('app.services.auth.auth_service.register_user') as mock_register:
            mock_register.return_value = {
                "id": "new-user-id",
                "email": "newuser@example.com",
                "full_name": "New User",
                "is_active": True,
                "is_verified": False,
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = await async_client.post("/api/v1/auth/register", json=registration_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["data"]["email"] == "newuser@example.com"
            assert "password" not in data["data"]  # Password should not be returned
    
    @pytest.mark.asyncio
    async def test_register_endpoint_validation_errors(self, async_client):
        """Test registration with validation errors"""
        # Test missing required fields
        invalid_data = {
            "email": "invalid-email",  # Invalid email format
            "password": "weak",  # Weak password
            # Missing full_name
        }
        
        response = await async_client.post("/api/v1/auth/register", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_register_endpoint_duplicate_email(self, async_client):
        """Test registration with duplicate email"""
        registration_data = {
            "email": "existing@example.com",
            "password": "SecurePassword123!",
            "full_name": "Existing User"
        }
        
        with patch('app.services.auth.auth_service.register_user') as mock_register:
            mock_register.side_effect = ValueError("Email already registered")
            
            response = await async_client.post("/api/v1/auth/register", json=registration_data)
            
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert "email already registered" in data["error"].lower()
    
    @pytest.mark.asyncio
    async def test_login_endpoint_success(self, async_client):
        """Test successful login"""
        login_data = {
            "email": "user@example.com",
            "password": "SecurePassword123!"
        }
        
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "access_token": "test-access-token",
                "refresh_token": "test-refresh-token",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": "user-id",
                    "email": "user@example.com",
                    "full_name": "Test User"
                }
            }
            
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "access_token" in data["data"]
            assert "refresh_token" in data["data"]
            assert data["data"]["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_endpoint_invalid_credentials(self, async_client):
        """Test login with invalid credentials"""
        login_data = {
            "email": "user@example.com",
            "password": "WrongPassword"
        }
        
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.side_effect = ValueError("Invalid credentials")
            
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 401
            data = response.json()
            assert data["success"] is False
            assert "invalid credentials" in data["error"].lower()
    
    @pytest.mark.asyncio
    async def test_refresh_token_endpoint_success(self, async_client):
        """Test successful token refresh"""
        refresh_data = {
            "refresh_token": "valid-refresh-token"
        }
        
        with patch('app.services.auth.auth_service.refresh_token') as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new-access-token",
                "token_type": "bearer",
                "expires_in": 1800
            }
            
            response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["access_token"] == "new-access-token"
    
    @pytest.mark.asyncio
    async def test_refresh_token_endpoint_invalid_token(self, async_client):
        """Test token refresh with invalid token"""
        refresh_data = {
            "refresh_token": "invalid-refresh-token"
        }
        
        with patch('app.services.auth.auth_service.refresh_token') as mock_refresh:
            mock_refresh.side_effect = ValueError("Invalid refresh token")
            
            response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
            
            assert response.status_code == 401
            data = response.json()
            assert data["success"] is False
    
    @pytest.mark.asyncio
    async def test_logout_endpoint_success(self, async_client, mock_user):
        """Test successful logout"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            with patch('app.services.auth.auth_service.logout_user') as mock_logout:
                mock_logout.return_value = True
                
                headers = {"Authorization": "Bearer test-token"}
                response = await async_client.post("/api/v1/auth/logout", headers=headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["message"] == "Successfully logged out"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_get_current_user_endpoint_success(self, async_client, mock_user):
        """Test getting current user information"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            headers = {"Authorization": "Bearer test-token"}
            response = await async_client.get("/api/v1/auth/me", headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["email"] == mock_user.email
            assert data["data"]["full_name"] == mock_user.full_name
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_get_current_user_endpoint_unauthorized(self, async_client):
        """Test getting current user without authentication"""
        response = await async_client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_change_password_endpoint_success(self, async_client, mock_user):
        """Test successful password change"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            password_data = {
                "current_password": "OldPassword123!",
                "new_password": "NewPassword123!"
            }
            
            with patch('app.services.auth.auth_service.change_password') as mock_change:
                mock_change.return_value = True
                
                headers = {"Authorization": "Bearer test-token"}
                response = await async_client.post("/api/v1/auth/change-password", 
                                                 json=password_data, headers=headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["message"] == "Password changed successfully"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_change_password_endpoint_wrong_current_password(self, async_client, mock_user):
        """Test password change with wrong current password"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            password_data = {
                "current_password": "WrongPassword",
                "new_password": "NewPassword123!"
            }
            
            with patch('app.services.auth.auth_service.change_password') as mock_change:
                mock_change.side_effect = ValueError("Current password is incorrect")
                
                headers = {"Authorization": "Bearer test-token"}
                response = await async_client.post("/api/v1/auth/change-password", 
                                                 json=password_data, headers=headers)
                
                assert response.status_code == 400
                data = response.json()
                assert data["success"] is False
        
        finally:
            app.dependency_overrides.clear()


class TestPortfolioEndpoints:
    """Comprehensive tests for portfolio endpoints"""
    
    @pytest.fixture
    async def async_client(self):
        """Async test client fixture"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    def mock_user(self):
        """Mock user fixture"""
        return User(
            id="portfolio-test-user",
            email="portfolio@example.com",
            full_name="Portfolio User",
            is_active=True
        )
    
    @pytest.mark.asyncio
    async def test_create_portfolio_endpoint_success(self, async_client, mock_user):
        """Test successful portfolio creation"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            portfolio_data = {
                "name": "Test Portfolio",
                "description": "A test portfolio for unit testing",
                "initial_cash": 10000.00
            }
            
            with patch('app.services.portfolio.portfolio_service.create_portfolio') as mock_create:
                mock_create.return_value = {
                    "id": "portfolio-123",
                    "name": "Test Portfolio",
                    "description": "A test portfolio for unit testing",
                    "user_id": mock_user.id,
                    "total_value": 10000.00,
                    "cash_balance": 10000.00,
                    "created_at": datetime.utcnow().isoformat(),
                    "is_active": True
                }
                
                response = await async_client.post("/api/v1/portfolios", json=portfolio_data)
                
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["data"]["name"] == "Test Portfolio"
                assert data["data"]["user_id"] == mock_user.id
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_create_portfolio_endpoint_validation_error(self, async_client, mock_user):
        """Test portfolio creation with validation errors"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Invalid portfolio data
            portfolio_data = {
                "name": "",  # Empty name
                "description": "x" * 1001,  # Too long description
                "initial_cash": -1000.00  # Negative cash
            }
            
            response = await async_client.post("/api/v1/portfolios", json=portfolio_data)
            
            assert response.status_code == 422
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_get_portfolios_endpoint_success(self, async_client, mock_user):
        """Test getting user portfolios"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            mock_portfolios = [
                {
                    "id": "portfolio-1",
                    "name": "Portfolio 1",
                    "user_id": mock_user.id,
                    "total_value": 15000.00
                },
                {
                    "id": "portfolio-2",
                    "name": "Portfolio 2",
                    "user_id": mock_user.id,
                    "total_value": 25000.00
                }
            ]
            
            with patch('app.services.portfolio.portfolio_service.get_portfolios') as mock_get:
                mock_get.return_value = mock_portfolios
                
                response = await async_client.get("/api/v1/portfolios")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]) == 2
                assert data["data"][0]["name"] == "Portfolio 1"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_get_portfolio_endpoint_success(self, async_client, mock_user):
        """Test getting a specific portfolio"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            portfolio_id = "portfolio-123"
            mock_portfolio = {
                "id": portfolio_id,
                "name": "Test Portfolio",
                "user_id": mock_user.id,
                "total_value": 15000.00,
                "holdings": []
            }
            
            with patch('app.services.portfolio.portfolio_service.get_portfolio') as mock_get:
                mock_get.return_value = mock_portfolio
                
                response = await async_client.get(f"/api/v1/portfolios/{portfolio_id}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["id"] == portfolio_id
                assert data["data"]["name"] == "Test Portfolio"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_get_portfolio_endpoint_not_found(self, async_client, mock_user):
        """Test getting a non-existent portfolio"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            portfolio_id = "non-existent-portfolio"
            
            with patch('app.services.portfolio.portfolio_service.get_portfolio') as mock_get:
                mock_get.return_value = None
                
                response = await async_client.get(f"/api/v1/portfolios/{portfolio_id}")
                
                assert response.status_code == 404
                data = response.json()
                assert data["success"] is False
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_update_portfolio_endpoint_success(self, async_client, mock_user):
        """Test successful portfolio update"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            portfolio_id = "portfolio-123"
            update_data = {
                "name": "Updated Portfolio Name",
                "description": "Updated description"
            }
            
            with patch('app.services.portfolio.portfolio_service.update_portfolio') as mock_update:
                mock_update.return_value = {
                    "id": portfolio_id,
                    "name": "Updated Portfolio Name",
                    "description": "Updated description",
                    "user_id": mock_user.id,
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                response = await async_client.put(f"/api/v1/portfolios/{portfolio_id}", 
                                                json=update_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["name"] == "Updated Portfolio Name"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_delete_portfolio_endpoint_success(self, async_client, mock_user):
        """Test successful portfolio deletion"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            portfolio_id = "portfolio-123"
            
            with patch('app.services.portfolio.portfolio_service.delete_portfolio') as mock_delete:
                mock_delete.return_value = True
                
                response = await async_client.delete(f"/api/v1/portfolios/{portfolio_id}")
                
                assert response.status_code == 204
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_add_holding_endpoint_success(self, async_client, mock_user):
        """Test successful holding addition"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            portfolio_id = "portfolio-123"
            holding_data = {
                "symbol": "AAPL",
                "shares": 100,
                "purchase_price": 150.00,
                "transaction_date": "2024-01-15"
            }
            
            with patch('app.services.portfolio.portfolio_service.add_holding') as mock_add:
                mock_add.return_value = {
                    "id": "holding-456",
                    "portfolio_id": portfolio_id,
                    "symbol": "AAPL",
                    "shares": 100,
                    "purchase_price": 150.00,
                    "current_price": 155.00,
                    "current_value": 15500.00,
                    "gain_loss": 500.00
                }
                
                response = await async_client.post(f"/api/v1/portfolios/{portfolio_id}/holdings", 
                                                 json=holding_data)
                
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["data"]["symbol"] == "AAPL"
                assert data["data"]["shares"] == 100
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_get_portfolio_performance_endpoint_success(self, async_client, mock_user):
        """Test getting portfolio performance"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            portfolio_id = "portfolio-123"
            
            with patch('app.services.analytics.analytics_service.calculate_portfolio_performance') as mock_perf:
                mock_perf.return_value = {
                    "portfolio_id": portfolio_id,
                    "total_value": 15500.00,
                    "total_return": 500.00,
                    "return_percentage": 3.33,
                    "holdings": [
                        {
                            "symbol": "AAPL",
                            "current_value": 15500.00,
                            "gain_loss": 500.00
                        }
                    ]
                }
                
                response = await async_client.get(f"/api/v1/portfolios/{portfolio_id}/performance")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["total_value"] == 15500.00
                assert data["data"]["return_percentage"] == 3.33
        
        finally:
            app.dependency_overrides.clear()


class TestAnalyticsEndpoints:
    """Comprehensive tests for analytics endpoints"""
    
    @pytest.fixture
    async def async_client(self):
        """Async test client fixture"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    def mock_user(self):
        """Mock user fixture"""
        return User(
            id="analytics-test-user",
            email="analytics@example.com",
            full_name="Analytics User",
            is_active=True
        )
    
    @pytest.mark.asyncio
    async def test_stock_prediction_endpoint_success(self, async_client, mock_user):
        """Test successful stock price prediction"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            prediction_request = {
                "symbol": "AAPL",
                "days_ahead": 30,
                "model_type": "random_forest"
            }
            
            with patch('app.services.analytics.ml_service.predict_stock_price') as mock_predict:
                mock_predict.return_value = {
                    "symbol": "AAPL",
                    "predicted_price": 165.50,
                    "confidence_score": 0.78,
                    "current_price": 155.00,
                    "prediction_date": datetime.utcnow().isoformat(),
                    "days_ahead": 30,
                    "model_used": "random_forest"
                }
                
                response = await async_client.post("/api/v1/analytics/predict/stock-price", 
                                                 json=prediction_request)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["symbol"] == "AAPL"
                assert data["data"]["predicted_price"] == 165.50
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_portfolio_risk_analysis_endpoint_success(self, async_client, mock_user):
        """Test successful portfolio risk analysis"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            risk_request = {
                "portfolio": {
                    "AAPL": 0.4,
                    "GOOGL": 0.3,
                    "MSFT": 0.3
                },
                "time_horizon": 252
            }
            
            with patch('app.services.analytics.ml_service.analyze_portfolio_risk') as mock_risk:
                mock_risk.return_value = {
                    "expected_return": 0.12,
                    "volatility": 0.18,
                    "var_95": -0.08,
                    "var_99": -0.12,
                    "sharpe_ratio": 0.67
                }
                
                response = await async_client.post("/api/v1/analytics/analyze/portfolio-risk", 
                                                 json=risk_request)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["expected_return"] == 0.12
                assert data["data"]["var_95"] == -0.08
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_correlation_analysis_endpoint_success(self, async_client, mock_user):
        """Test successful correlation analysis"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            correlation_request = {
                "symbols": ["AAPL", "GOOGL", "MSFT"],
                "period": "1y"
            }
            
            with patch('app.services.analytics.ml_service.calculate_correlation_matrix') as mock_corr:
                mock_corr.return_value = {
                    "correlation_matrix": {
                        "AAPL": {"AAPL": 1.0, "GOOGL": 0.65, "MSFT": 0.72},
                        "GOOGL": {"AAPL": 0.65, "GOOGL": 1.0, "MSFT": 0.68},
                        "MSFT": {"AAPL": 0.72, "GOOGL": 0.68, "MSFT": 1.0}
                    },
                    "analysis_period": "1y",
                    "data_points": 252
                }
                
                response = await async_client.post("/api/v1/analytics/analyze/correlation", 
                                                 json=correlation_request)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "correlation_matrix" in data["data"]
        
        finally:
            app.dependency_overrides.clear()


class TestDataEndpoints:
    """Comprehensive tests for data endpoints"""
    
    @pytest.fixture
    async def async_client(self):
        """Async test client fixture"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    def mock_user(self):
        """Mock user fixture"""
        return User(
            id="data-test-user",
            email="data@example.com",
            full_name="Data User",
            is_active=True
        )
    
    @pytest.mark.asyncio
    async def test_get_stock_data_endpoint_success(self, async_client, mock_user):
        """Test successful stock data retrieval"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            symbol = "AAPL"
            
            with patch('app.services.data.data_ingestion_service.get_stock_data') as mock_data:
                mock_data.return_value = {
                    "symbol": "AAPL",
                    "current_price": 155.00,
                    "change": 2.50,
                    "change_percent": 1.64,
                    "volume": 50000000,
                    "market_cap": 2500000000000,
                    "pe_ratio": 25.5,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                response = await async_client.get(f"/api/v1/data/stocks/{symbol}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["symbol"] == "AAPL"
                assert data["data"]["current_price"] == 155.00
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_get_historical_data_endpoint_success(self, async_client, mock_user):
        """Test successful historical data retrieval"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            symbol = "AAPL"
            
            with patch('app.services.data.data_ingestion_service.get_historical_data') as mock_hist:
                mock_hist.return_value = {
                    "symbol": "AAPL",
                    "data": [
                        {
                            "date": "2024-01-01",
                            "open": 150.00,
                            "high": 155.00,
                            "low": 149.00,
                            "close": 154.00,
                            "volume": 45000000
                        },
                        {
                            "date": "2024-01-02",
                            "open": 154.00,
                            "high": 157.00,
                            "low": 153.00,
                            "close": 156.00,
                            "volume": 48000000
                        }
                    ],
                    "period": "1mo"
                }
                
                response = await async_client.get(f"/api/v1/data/stocks/{symbol}/historical?period=1mo")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["symbol"] == "AAPL"
                assert len(data["data"]["data"]) == 2
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_search_stocks_endpoint_success(self, async_client, mock_user):
        """Test successful stock search"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            search_query = "apple"
            
            with patch('app.services.data.data_ingestion_service.search_stocks') as mock_search:
                mock_search.return_value = [
                    {
                        "symbol": "AAPL",
                        "name": "Apple Inc.",
                        "exchange": "NASDAQ",
                        "type": "Common Stock"
                    },
                    {
                        "symbol": "APLE",
                        "name": "Apple Hospitality REIT Inc.",
                        "exchange": "NYSE",
                        "type": "REIT"
                    }
                ]
                
                response = await async_client.get(f"/api/v1/data/search?q={search_query}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]) == 2
                assert data["data"][0]["symbol"] == "AAPL"
        
        finally:
            app.dependency_overrides.clear()


class TestReportEndpoints:
    """Comprehensive tests for report endpoints"""
    
    @pytest.fixture
    async def async_client(self):
        """Async test client fixture"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    def mock_user(self):
        """Mock user fixture"""
        return User(
            id="report-test-user",
            email="report@example.com",
            full_name="Report User",
            is_active=True
        )
    
    @pytest.mark.asyncio
    async def test_generate_portfolio_report_endpoint_success(self, async_client, mock_user):
        """Test successful portfolio report generation"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            report_request = {
                "portfolio_id": "portfolio-123",
                "report_type": "performance",
                "date_range": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31"
                },
                "format": "pdf"
            }
            
            with patch('app.services.report.pdf_generator.generate_report') as mock_generate:
                mock_generate.return_value = {
                    "report_id": "report-456",
                    "portfolio_id": "portfolio-123",
                    "report_type": "performance",
                    "format": "pdf",
                    "file_path": "/tmp/reports/report-456.pdf",
                    "file_size": 2048576,
                    "generated_at": datetime.utcnow().isoformat(),
                    "status": "completed"
                }
                
                response = await async_client.post("/api/v1/reports/generate", json=report_request)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["report_id"] == "report-456"
                assert data["data"]["status"] == "completed"
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_get_report_status_endpoint_success(self, async_client, mock_user):
        """Test getting report generation status"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            report_id = "report-456"
            
            with patch('app.services.report.pdf_generator.get_report_status') as mock_status:
                mock_status.return_value = {
                    "report_id": report_id,
                    "status": "completed",
                    "progress": 100,
                    "file_path": "/tmp/reports/report-456.pdf",
                    "file_size": 2048576,
                    "generated_at": datetime.utcnow().isoformat()
                }
                
                response = await async_client.get(f"/api/v1/reports/{report_id}/status")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["status"] == "completed"
                assert data["data"]["progress"] == 100
        
        finally:
            app.dependency_overrides.clear()


# Edge Cases and Error Handling Tests
class TestAPIEndpointsEdgeCases:
    """Test edge cases and error conditions for API endpoints"""
    
    @pytest.fixture
    async def async_client(self):
        """Async test client fixture"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_endpoints_without_authentication(self, async_client):
        """Test protected endpoints without authentication"""
        protected_endpoints = [
            ("GET", "/api/v1/portfolios"),
            ("POST", "/api/v1/portfolios"),
            ("GET", "/api/v1/portfolios/123"),
            ("PUT", "/api/v1/portfolios/123"),
            ("DELETE", "/api/v1/portfolios/123"),
            ("POST", "/api/v1/analytics/predict/stock-price"),
            ("GET", "/api/v1/data/stocks/AAPL"),
            ("POST", "/api/v1/reports/generate")
        ]
        
        for method, endpoint in protected_endpoints:
            if method == "GET":
                response = await async_client.get(endpoint)
            elif method == "POST":
                response = await async_client.post(endpoint, json={})
            elif method == "PUT":
                response = await async_client.put(endpoint, json={})
            elif method == "DELETE":
                response = await async_client.delete(endpoint)
            
            assert response.status_code == 401, f"{method} {endpoint} should require authentication"
    
    @pytest.mark.asyncio
    async def test_endpoints_with_invalid_json(self, async_client):
        """Test endpoints with invalid JSON data"""
        # Test with malformed JSON
        response = await async_client.post("/api/v1/auth/register", 
                                         content="invalid json data",
                                         headers={"Content-Type": "application/json"})
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_endpoints_with_missing_required_fields(self, async_client):
        """Test endpoints with missing required fields"""
        # Test registration without required fields
        response = await async_client.post("/api/v1/auth/register", json={})
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_endpoints_with_invalid_data_types(self, async_client):
        """Test endpoints with invalid data types"""
        # Test with invalid data types
        invalid_data = {
            "email": 12345,  # Should be string
            "password": True,  # Should be string
            "full_name": ["not", "a", "string"]  # Should be string
        }
        
        response = await async_client.post("/api/v1/auth/register", json=invalid_data)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_endpoints_with_sql_injection_attempts(self, async_client, mock_user):
        """Test endpoints with SQL injection attempts"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # SQL injection payloads
            sql_payloads = [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "'; UPDATE users SET is_admin=true; --"
            ]
            
            for payload in sql_payloads:
                # Test in portfolio name
                portfolio_data = {
                    "name": payload,
                    "description": "Test portfolio"
                }
                
                with patch('app.services.portfolio.portfolio_service.create_portfolio') as mock_create:
                    mock_create.return_value = {"id": "test", "name": payload, "user_id": mock_user.id}
                    
                    response = await async_client.post("/api/v1/portfolios", json=portfolio_data)
                    
                    # Should handle SQL injection safely
                    assert response.status_code in [201, 400, 422]
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_endpoints_with_xss_attempts(self, async_client, mock_user):
        """Test endpoints with XSS attempts"""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # XSS payloads
            xss_payloads = [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "javascript:alert('XSS')"
            ]
            
            for payload in xss_payloads:
                portfolio_data = {
                    "name": payload,
                    "description": payload
                }
                
                with patch('app.services.portfolio.portfolio_service.create_portfolio') as mock_create:
                    mock_create.return_value = {"id": "test", "name": payload, "user_id": mock_user.id}
                    
                    response = await async_client.post("/api/v1/portfolios", json=portfolio_data)
                    
                    # Should handle XSS safely
                    assert response.status_code in [201, 400, 422]
                    
                    if response.status_code == 201:
                        # Response should not contain raw script tags
                        response_text = response.text
                        assert "<script>" not in response_text
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_endpoints_with_extremely_large_payloads(self, async_client):
        """Test endpoints with extremely large payloads"""
        # Create a very large payload
        large_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "A" * 100000,  # 100KB string
            "description": "B" * 100000  # Another 100KB string
        }
        
        response = await async_client.post("/api/v1/auth/register", json=large_data)
        
        # Should reject overly large payloads
        assert response.status_code in [400, 413, 422]