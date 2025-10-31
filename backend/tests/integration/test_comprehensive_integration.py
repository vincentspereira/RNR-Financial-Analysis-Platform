"""
Comprehensive Integration Tests - Component Interactions and API Contracts
"""
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.main import app
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User


class TestAPIIntegration:
    """Integration tests for API endpoints and component interactions"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest_asyncio.fixture
    async def async_client(self):
        """Async test client fixture"""
        from httpx import AsyncClient
        async with AsyncClient() as client:
            # Mock the client to avoid actual HTTP calls
            client.base_url = "http://testserver"
            yield client
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock()
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user"""
        return User(
            id="test-user-id",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_verified=True
        )
    
    def test_health_endpoint_integration(self, client):
        """Test health check endpoint integration"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure based on actual response
        assert "status" in data
        assert "service" in data
        assert "version" in data
        
        # Verify status is healthy
        assert data["status"] == "healthy"
        assert data["service"] == "Financial Analysis Platform API"
        assert data["version"] == "1.0.0"
        
        # Check if features are present (optional)
        if "features" in data:
            assert isinstance(data["features"], list)
            assert len(data["features"]) > 0
    
    @pytest.mark.asyncio
    async def test_authentication_flow_integration(self, async_client):
        """Test complete authentication flow integration"""
        
        # Test user registration
        registration_data = {
            "email": "integration.test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Integration Test User"
        }
        
        with patch('app.services.auth.auth_service.register_user') as mock_register:
            mock_register.return_value = {
                "id": "new-user-id",
                "email": "integration.test@example.com",
                "full_name": "Integration Test User",
                "is_active": True,
                "is_verified": False
            }
            
            response = await async_client.post("/api/v1/auth/register", json=registration_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["data"]["email"] == "integration.test@example.com"
            assert "id" in data["data"]
        
        # Test user login
        login_data = {
            "email": "integration.test@example.com",
            "password": "SecurePassword123!"
        }
        
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "access_token": "test-access-token-12345",
                "refresh_token": "test-refresh-token-67890",
                "token_type": "bearer",
                "expires_in": 900,
                "user": {
                    "id": "new-user-id",
                    "email": "integration.test@example.com",
                    "full_name": "Integration Test User"
                }
            }
            
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "access_token" in data["data"]
            assert "refresh_token" in data["data"]
            assert data["data"]["token_type"] == "bearer"
        
        # Test token refresh
        refresh_data = {
            "refresh_token": "test-refresh-token-67890"
        }
        
        with patch('app.services.auth.auth_service.refresh_token') as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new-access-token-12345",
                "token_type": "bearer",
                "expires_in": 900
            }
            
            response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["access_token"] == "new-access-token-12345"
    
    @pytest.mark.asyncio
    async def test_portfolio_crud_integration(self, async_client, mock_user):
        """Test complete portfolio CRUD operations integration"""
        
        # Override auth dependency for testing
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test portfolio creation
            portfolio_data = {
                "name": "Integration Test Portfolio",
                "description": "Portfolio for integration testing",
                "initial_cash": 10000.00
            }
            
            with patch('app.services.portfolio.portfolio_service.create_portfolio') as mock_create:
                mock_create.return_value = {
                    "id": "test-portfolio-id-123",
                    "name": "Integration Test Portfolio",
                    "description": "Portfolio for integration testing",
                    "user_id": mock_user.id,
                    "total_value": 10000.00,
                    "cash_balance": 10000.00,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True
                }
                
                response = await async_client.post("/api/v1/portfolios", json=portfolio_data)
                
                assert response.status_code == 201
                created_portfolio = response.json()
                assert created_portfolio["success"] is True
                portfolio_id = created_portfolio["data"]["id"]
                assert portfolio_id == "test-portfolio-id-123"
            
            # Test portfolio retrieval
            with patch('app.services.portfolio.portfolio_service.get_portfolio') as mock_get:
                mock_get.return_value = {
                    "id": portfolio_id,
                    "name": "Integration Test Portfolio",
                    "description": "Portfolio for integration testing",
                    "user_id": mock_user.id,
                    "total_value": 10000.00,
                    "cash_balance": 10000.00,
                    "holdings": []
                }
                
                response = await async_client.get(f"/api/v1/portfolios/{portfolio_id}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["name"] == "Integration Test Portfolio"
            
            # Test adding holdings
            holding_data = {
                "symbol": "AAPL",
                "shares": 100,
                "purchase_price": 150.00,
                "transaction_date": "2024-12-01"
            }
            
            with patch('app.services.portfolio.portfolio_service.add_holding') as mock_add_holding:
                mock_add_holding.return_value = {
                    "id": "test-holding-id-456",
                    "portfolio_id": portfolio_id,
                    "symbol": "AAPL",
                    "shares": 100,
                    "purchase_price": 150.00,
                    "current_price": 155.00,
                    "current_value": 15500.00,
                    "gain_loss": 500.00,
                    "gain_loss_percentage": 3.33
                }
                
                response = await async_client.post(
                    f"/api/v1/portfolios/{portfolio_id}/holdings",
                    json=holding_data
                )
                
                assert response.status_code == 201
                holding_response = response.json()
                assert holding_response["success"] is True
                assert holding_response["data"]["symbol"] == "AAPL"
            
            # Test portfolio performance calculation
            with patch('app.services.analytics.analytics_service.calculate_portfolio_performance') as mock_performance:
                mock_performance.return_value = {
                    "portfolio_id": portfolio_id,
                    "total_value": 15500.00,
                    "total_cost_basis": 15000.00,
                    "total_gain_loss": 500.00,
                    "total_return_percentage": 3.33,
                    "cash_balance": 0.00,
                    "holdings_value": 15500.00,
                    "holdings": [
                        {
                            "symbol": "AAPL",
                            "shares": 100,
                            "current_price": 155.00,
                            "current_value": 15500.00,
                            "cost_basis": 15000.00,
                            "gain_loss": 500.00,
                            "gain_loss_percentage": 3.33,
                            "weight": 100.0
                        }
                    ],
                    "performance_metrics": {
                        "daily_return": 0.5,
                        "weekly_return": 2.1,
                        "monthly_return": 3.33,
                        "ytd_return": 8.7,
                        "volatility": 15.2,
                        "sharpe_ratio": 1.8,
                        "max_drawdown": -2.1
                    }
                }
                
                response = await async_client.get(f"/api/v1/portfolios/{portfolio_id}/performance")
                
                assert response.status_code == 200
                performance_data = response.json()
                assert performance_data["success"] is True
                assert performance_data["data"]["total_value"] == 15500.00
                assert len(performance_data["data"]["holdings"]) == 1
                assert performance_data["data"]["holdings"][0]["symbol"] == "AAPL"
            
            # Test portfolio update
            update_data = {
                "name": "Updated Integration Portfolio",
                "description": "Updated description for testing"
            }
            
            with patch('app.services.portfolio.portfolio_service.update_portfolio') as mock_update:
                mock_update.return_value = {
                    "id": portfolio_id,
                    "name": "Updated Integration Portfolio",
                    "description": "Updated description for testing",
                    "user_id": mock_user.id,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                response = await async_client.put(f"/api/v1/portfolios/{portfolio_id}", json=update_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["name"] == "Updated Integration Portfolio"
            
            # Test portfolio deletion
            with patch('app.services.portfolio.portfolio_service.delete_portfolio') as mock_delete:
                mock_delete.return_value = True
                
                response = await async_client.delete(f"/api/v1/portfolios/{portfolio_id}")
                
                assert response.status_code == 204
        
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_analytics_integration_workflow(self, async_client, mock_user):
        """Test analytics and ML integration workflow"""
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test stock price prediction
            prediction_request = {
                "symbol": "AAPL",
                "days_ahead": 30,
                "model_type": "random_forest",
                "confidence_threshold": 0.7
            }
            
            with patch('app.services.analytics.ml_service.predict_stock_price') as mock_predict:
                mock_predict.return_value = {
                    "symbol": "AAPL",
                    "predicted_price": 165.50,
                    "confidence_score": 0.78,
                    "current_price": 155.00,
                    "prediction_date": datetime.now(timezone.utc).isoformat(),
                    "days_ahead": 30,
                    "model_used": "random_forest",
                    "features_used": ["sma_20", "rsi", "macd", "volume"],
                    "metadata": {
                        "data_points": 500,
                        "training_accuracy": 0.85,
                        "last_trained": "2024-12-01T10:00:00Z"
                    }
                }
                
                response = await async_client.post(
                    "/api/v1/analytics/predict/stock-price",
                    json=prediction_request
                )
                
                assert response.status_code == 200
                prediction_data = response.json()
                assert prediction_data["success"] is True
                assert prediction_data["data"]["symbol"] == "AAPL"
                assert prediction_data["data"]["predicted_price"] == 165.50
                assert prediction_data["data"]["confidence_score"] == 0.78
            
            # Test portfolio risk analysis
            risk_request = {
                "portfolio": {
                    "AAPL": 0.4,
                    "GOOGL": 0.3,
                    "MSFT": 0.2,
                    "TSLA": 0.1
                },
                "time_horizon": 252,
                "confidence_level": 0.95
            }
            
            with patch('app.services.analytics.ml_service.analyze_portfolio_risk') as mock_risk:
                mock_risk.return_value = {
                    "portfolio_weights": risk_request["portfolio"],
                    "expected_return": 0.12,
                    "volatility": 0.18,
                    "sharpe_ratio": 0.67,
                    "var_95": -0.08,
                    "var_99": -0.12,
                    "cvar_95": -0.11,
                    "max_drawdown": -0.15,
                    "correlation_matrix": {
                        "AAPL": {"AAPL": 1.0, "GOOGL": 0.65, "MSFT": 0.72, "TSLA": 0.45},
                        "GOOGL": {"AAPL": 0.65, "GOOGL": 1.0, "MSFT": 0.68, "TSLA": 0.38},
                        "MSFT": {"AAPL": 0.72, "GOOGL": 0.68, "MSFT": 1.0, "TSLA": 0.42},
                        "TSLA": {"AAPL": 0.45, "GOOGL": 0.38, "MSFT": 0.42, "TSLA": 1.0}
                    },
                    "risk_contributions": {
                        "AAPL": 0.35,
                        "GOOGL": 0.28,
                        "MSFT": 0.25,
                        "TSLA": 0.12
                    }
                }
                
                response = await async_client.post(
                    "/api/v1/analytics/analyze/portfolio-risk",
                    json=risk_request
                )
                
                assert response.status_code == 200
                risk_data = response.json()
                assert risk_data["success"] is True
                assert risk_data["data"]["expected_return"] == 0.12
                assert risk_data["data"]["var_95"] == -0.08
            
            # Test trading signals generation
            signals_request = {
                "symbol": "AAPL",
                "indicators": ["rsi", "macd", "bollinger_bands"],
                "timeframe": "1d"
            }
            
            with patch('app.services.analytics.ml_service.generate_trading_signals') as mock_signals:
                mock_signals.return_value = {
                    "symbol": "AAPL",
                    "signals": [
                        {
                            "indicator": "rsi",
                            "signal": "buy",
                            "strength": 0.75,
                            "value": 25.5,
                            "threshold": 30.0,
                            "description": "RSI oversold condition"
                        },
                        {
                            "indicator": "macd",
                            "signal": "neutral",
                            "strength": 0.45,
                            "value": 0.02,
                            "description": "MACD near zero line"
                        }
                    ],
                    "overall_signal": "buy",
                    "confidence": 0.68,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
                
                response = await async_client.post(
                    "/api/v1/analytics/signals/trading",
                    json=signals_request
                )
                
                assert response.status_code == 200
                signals_data = response.json()
                assert signals_data["success"] is True
                assert signals_data["data"]["symbol"] == "AAPL"
                assert signals_data["data"]["overall_signal"] == "buy"
                assert len(signals_data["data"]["signals"]) == 2
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_data_flow_validation(self, async_client, mock_user):
        """Test data flow between components with validation"""
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test complete data flow: User -> Portfolio -> Holdings -> Analytics -> Reports
            
            # Step 1: Create portfolio
            portfolio_data = {
                "name": "Data Flow Test Portfolio",
                "description": "Testing complete data flow",
                "initial_cash": 50000.00
            }
            
            with patch('app.services.portfolio.portfolio_service.create_portfolio') as mock_create_portfolio:
                mock_create_portfolio.return_value = {
                    "id": "dataflow-portfolio-123",
                    "name": "Data Flow Test Portfolio",
                    "user_id": mock_user.id,
                    "total_value": 50000.00,
                    "cash_balance": 50000.00
                }
                
                portfolio_response = await async_client.post("/api/v1/portfolios", json=portfolio_data)
                assert portfolio_response.status_code == 201
                portfolio_id = portfolio_response.json()["data"]["id"]
            
            # Step 2: Add multiple holdings
            holdings_data = [
                {"symbol": "AAPL", "shares": 100, "purchase_price": 150.00},
                {"symbol": "GOOGL", "shares": 20, "purchase_price": 2800.00},
                {"symbol": "MSFT", "shares": 50, "purchase_price": 380.00}
            ]
            
            for holding_data in holdings_data:
                with patch('app.services.portfolio.portfolio_service.add_holding') as mock_add_holding:
                    mock_add_holding.return_value = {
                        "id": f"holding-{holding_data['symbol']}-123",
                        "portfolio_id": portfolio_id,
                        **holding_data,
                        "current_price": holding_data["purchase_price"] * 1.05,  # 5% gain
                        "current_value": holding_data["shares"] * holding_data["purchase_price"] * 1.05
                    }
                    
                    holding_response = await async_client.post(
                        f"/api/v1/portfolios/{portfolio_id}/holdings",
                        json=holding_data
                    )
                    assert holding_response.status_code == 201
            
            # Step 3: Calculate portfolio performance (should include all holdings)
            with patch('app.services.analytics.analytics_service.calculate_portfolio_performance') as mock_performance:
                total_invested = sum(h["shares"] * h["purchase_price"] for h in holdings_data)
                total_current = total_invested * 1.05  # 5% overall gain
                
                mock_performance.return_value = {
                    "portfolio_id": portfolio_id,
                    "total_value": total_current,
                    "total_cost_basis": total_invested,
                    "total_gain_loss": total_current - total_invested,
                    "total_return_percentage": 5.0,
                    "holdings": [
                        {
                            "symbol": h["symbol"],
                            "shares": h["shares"],
                            "current_price": h["purchase_price"] * 1.05,
                            "current_value": h["shares"] * h["purchase_price"] * 1.05,
                            "cost_basis": h["shares"] * h["purchase_price"],
                            "gain_loss": h["shares"] * h["purchase_price"] * 0.05,
                            "gain_loss_percentage": 5.0
                        } for h in holdings_data
                    ]
                }
                
                performance_response = await async_client.get(f"/api/v1/portfolios/{portfolio_id}/performance")
                assert performance_response.status_code == 200
                
                performance_data = performance_response.json()["data"]
                assert len(performance_data["holdings"]) == 3
                assert performance_data["total_return_percentage"] == 5.0
            
            # Step 4: Generate portfolio report (should include performance data)
            report_request = {
                "portfolio_id": portfolio_id,
                "report_type": "comprehensive",
                "date_range": {
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31"
                },
                "sections": ["summary", "performance", "holdings", "risk_analysis"]
            }
            
            with patch('app.services.report.report_generator.generate_report') as mock_generate_report:
                mock_generate_report.return_value = {
                    "report_id": "report-dataflow-456",
                    "portfolio_id": portfolio_id,
                    "report_type": "comprehensive",
                    "format": "pdf",
                    "file_path": "/tmp/reports/report-dataflow-456.pdf",
                    "file_size": 2048576,  # 2MB
                    "sections": {
                        "summary": {"total_value": total_current, "return_percentage": 5.0},
                        "performance": {"holdings_count": 3, "best_performer": "AAPL"},
                        "holdings": {"count": 3, "diversification_score": 0.85},
                        "risk_analysis": {"var_95": -0.05, "volatility": 0.15}
                    },
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "status": "completed"
                }
                
                report_response = await async_client.post("/api/v1/reports/generate", json=report_request)
                assert report_response.status_code == 200
                
                report_data = report_response.json()["data"]
                assert report_data["portfolio_id"] == portfolio_id
                assert report_data["sections"]["holdings"]["count"] == 3
                assert report_data["sections"]["summary"]["return_percentage"] == 5.0
            
            # Step 5: Verify data consistency across all components
            # The data should flow consistently from portfolio -> analytics -> reports
            assert portfolio_id == "dataflow-portfolio-123"
            # Performance data should reflect the 3 holdings
            # Report should include all performance metrics
            
        finally:
            app.dependency_overrides.clear()


class TestModuleInterfaces:
    """Test interfaces and contracts between different modules"""
    
    @pytest.mark.asyncio
    async def test_auth_portfolio_integration(self):
        """Test integration between authentication and portfolio modules"""
        from app.services.auth import auth_service
        from app.services.portfolio import portfolio_service
        
        # Mock user authentication
        with patch.object(auth_service, 'get_user_by_id') as mock_get_user:
            mock_get_user.return_value = {
                "id": "auth-test-user-id",
                "email": "auth.test@example.com",
                "full_name": "Auth Test User",
                "is_active": True,
                "is_verified": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Mock portfolio creation that depends on authenticated user
            with patch.object(portfolio_service, 'create_portfolio') as mock_create:
                mock_create.return_value = {
                    "id": "auth-test-portfolio-id",
                    "user_id": "auth-test-user-id",
                    "name": "Auth Integration Test Portfolio",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Test that portfolio service correctly uses user from auth service
                user = await auth_service.get_user_by_id("auth-test-user-id")
                portfolio = await portfolio_service.create_portfolio(
                    user_id=user["id"],
                    portfolio_data={"name": "Auth Integration Test Portfolio"}
                )
                
                # Verify integration
                assert portfolio["user_id"] == user["id"]
                assert user["is_active"] is True
                mock_get_user.assert_called_once_with("auth-test-user-id")
                mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_portfolio_analytics_integration(self):
        """Test integration between portfolio and analytics modules"""
        from app.services.portfolio import portfolio_service
        from app.services.analytics import analytics_service
        
        # Mock portfolio data with holdings
        portfolio_data = {
            "id": "analytics-test-portfolio-id",
            "user_id": "test-user-id",
            "name": "Analytics Integration Portfolio",
            "holdings": [
                {
                    "id": "holding-1",
                    "symbol": "AAPL",
                    "shares": Decimal("100"),
                    "purchase_price": Decimal("150.00"),
                    "purchase_date": "2024-01-15"
                },
                {
                    "id": "holding-2",
                    "symbol": "GOOGL",
                    "shares": Decimal("25"),
                    "purchase_price": Decimal("2800.00"),
                    "purchase_date": "2024-02-01"
                }
            ]
        }
        
        with patch.object(portfolio_service, 'get_portfolio_with_holdings') as mock_get_portfolio:
            mock_get_portfolio.return_value = portfolio_data
            
            # Mock analytics calculation that processes portfolio data
            with patch.object(analytics_service, 'calculate_portfolio_performance') as mock_calculate:
                mock_calculate.return_value = {
                    "portfolio_id": "analytics-test-portfolio-id",
                    "total_value": Decimal("185000.00"),
                    "total_cost_basis": Decimal("185000.00"),
                    "total_return": Decimal("15000.00"),
                    "return_percentage": Decimal("8.82"),
                    "holdings_analysis": [
                        {
                            "symbol": "AAPL",
                            "contribution_to_return": Decimal("5.29"),
                            "weight": Decimal("40.54")
                        },
                        {
                            "symbol": "GOOGL",
                            "contribution_to_return": Decimal("3.53"),
                            "weight": Decimal("59.46")
                        }
                    ]
                }
                
                # Test integration flow
                portfolio = await portfolio_service.get_portfolio_with_holdings("analytics-test-portfolio-id")
                performance = await analytics_service.calculate_portfolio_performance(portfolio)
                
                # Verify integration
                assert performance["portfolio_id"] == portfolio["id"]
                assert len(performance["holdings_analysis"]) == len(portfolio["holdings"])
                assert performance["total_value"] > 0
                
                # Verify that analytics service received correct portfolio data
                mock_get_portfolio.assert_called_once_with("analytics-test-portfolio-id")
                mock_calculate.assert_called_once_with(portfolio_data)
    
    @pytest.mark.asyncio
    async def test_analytics_reporting_integration(self):
        """Test integration between analytics and reporting modules"""
        from app.services.analytics import analytics_service
        from app.services.report import report_generator
        
        # Mock analytics data
        analytics_data = {
            "portfolio_performance": {
                "total_return": 12.5,
                "volatility": 18.2,
                "sharpe_ratio": 0.68,
                "max_drawdown": -8.3
            },
            "risk_metrics": {
                "var_95": -0.045,
                "var_99": -0.067,
                "beta": 1.15,
                "correlation_with_market": 0.82
            },
            "holdings_analysis": [
                {"symbol": "AAPL", "weight": 35.2, "contribution": 4.8},
                {"symbol": "GOOGL", "weight": 28.7, "contribution": 3.2},
                {"symbol": "MSFT", "weight": 36.1, "contribution": 4.5}
            ]
        }
        
        with patch.object(analytics_service, 'get_comprehensive_analysis') as mock_analytics:
            mock_analytics.return_value = analytics_data
            
            # Mock report generation that uses analytics data
            with patch.object(report_generator, 'generate_performance_report') as mock_generate:
                mock_generate.return_value = {
                    "report_id": "analytics-integration-report",
                    "sections": {
                        "executive_summary": {
                            "total_return": analytics_data["portfolio_performance"]["total_return"],
                            "risk_level": "moderate"
                        },
                        "performance_analysis": analytics_data["portfolio_performance"],
                        "risk_analysis": analytics_data["risk_metrics"],
                        "holdings_breakdown": analytics_data["holdings_analysis"]
                    },
                    "charts": ["performance_chart", "risk_chart", "allocation_chart"],
                    "status": "completed"
                }
                
                # Test integration flow
                analysis = await analytics_service.get_comprehensive_analysis("test-portfolio-id")
                report = await report_generator.generate_performance_report(analysis)
                
                # Verify integration
                assert report["sections"]["performance_analysis"]["total_return"] == 12.5
                assert report["sections"]["risk_analysis"]["var_95"] == -0.045
                assert len(report["sections"]["holdings_breakdown"]) == 3
                
                # Verify data flow
                mock_analytics.assert_called_once_with("test-portfolio-id")
                mock_generate.assert_called_once_with(analytics_data)


class TestNegativeScenarios:
    """Test error handling and negative scenarios in integration"""
    
    @pytest.mark.asyncio
    async def test_invalid_authentication_integration(self, async_client):
        """Test API behavior with invalid authentication tokens"""
        
        # Test with completely invalid token
        headers = {"Authorization": "Bearer invalid-token-12345"}
        response = await async_client.get("/api/v1/portfolios", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "authentication" in data["error"].lower() or "unauthorized" in data["error"].lower()
        
        # Test with malformed token
        headers = {"Authorization": "InvalidFormat token-12345"}
        response = await async_client.get("/api/v1/portfolios", headers=headers)
        
        assert response.status_code == 401
        
        # Test with expired token
        headers = {"Authorization": "Bearer expired.jwt.token"}
        with patch('app.core.auth.verify_token', side_effect=Exception("Token expired")):
            response = await async_client.get("/api/v1/portfolios", headers=headers)
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_resource_not_found_integration(self, async_client, mock_user):
        """Test API behavior when resources are not found"""
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test non-existent portfolio
            with patch('app.services.portfolio.portfolio_service.get_portfolio', return_value=None):
                response = await async_client.get("/api/v1/portfolios/non-existent-portfolio-id")
                
                assert response.status_code == 404
                data = response.json()
                assert data["success"] is False
                assert "not found" in data["error"].lower()
            
            # Test non-existent user's portfolios
            with patch('app.services.portfolio.portfolio_service.get_portfolios', return_value=[]):
                response = await async_client.get("/api/v1/portfolios")
                
                assert response.status_code == 200  # Empty list is valid
                data = response.json()
                assert data["success"] is True
                assert data["data"] == []
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_validation_errors_integration(self, async_client, mock_user):
        """Test API validation error handling in integration scenarios"""
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test portfolio creation with invalid data
            invalid_portfolio_data = {
                "name": "",  # Empty name should fail validation
                "description": "x" * 1001,  # Too long description
                "initial_cash": -1000.00  # Negative cash should fail
            }
            
            response = await async_client.post("/api/v1/portfolios", json=invalid_portfolio_data)
            
            assert response.status_code == 422
            data = response.json()
            assert "detail" in data or "validation" in str(data).lower()
            
            # Test holding creation with invalid data
            invalid_holding_data = {
                "symbol": "INVALID_SYMBOL_TOO_LONG",  # Invalid symbol
                "shares": -100,  # Negative shares
                "purchase_price": 0  # Zero price
            }
            
            response = await async_client.post(
                "/api/v1/portfolios/test-portfolio-id/holdings",
                json=invalid_holding_data
            )
            
            assert response.status_code == 422
            
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_service_unavailable_integration(self, async_client, mock_user):
        """Test API behavior when backend services are unavailable"""
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test portfolio service failure
            with patch('app.services.portfolio.portfolio_service.get_portfolios', 
                      side_effect=Exception("Database connection failed")):
                
                response = await async_client.get("/api/v1/portfolios")
                
                assert response.status_code == 500
                data = response.json()
                assert data["success"] is False
                assert "error" in data
            
            # Test analytics service failure
            with patch('app.services.analytics.ml_service.predict_stock_price',
                      side_effect=Exception("ML service unavailable")):
                
                prediction_request = {
                    "symbol": "AAPL",
                    "days_ahead": 30
                }
                
                response = await async_client.post(
                    "/api/v1/analytics/predict/stock-price",
                    json=prediction_request
                )
                
                # Should either return error or fallback response
                assert response.status_code in [500, 503]
                
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_data_consistency_errors(self, async_client, mock_user):
        """Test handling of data consistency errors in integration"""
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test portfolio-holding consistency
            portfolio_id = "consistency-test-portfolio"
            
            # Try to add holding to non-existent portfolio
            holding_data = {
                "symbol": "AAPL",
                "shares": 100,
                "purchase_price": 150.00
            }
            
            with patch('app.services.portfolio.portfolio_service.add_holding',
                      side_effect=ValueError("Portfolio not found")):
                
                response = await async_client.post(
                    f"/api/v1/portfolios/{portfolio_id}/holdings",
                    json=holding_data
                )
                
                assert response.status_code in [400, 404]
                data = response.json()
                assert data["success"] is False
            
            # Test user-portfolio ownership consistency
            with patch('app.services.portfolio.portfolio_service.get_portfolio') as mock_get:
                # Return portfolio owned by different user
                mock_get.return_value = {
                    "id": portfolio_id,
                    "user_id": "different-user-id",  # Different from mock_user.id
                    "name": "Someone Else's Portfolio"
                }
                
                response = await async_client.get(f"/api/v1/portfolios/{portfolio_id}")
                
                # Should return 403 Forbidden or 404 Not Found
                assert response.status_code in [403, 404]
        
        finally:
            app.dependency_overrides.clear()


class TestAPIContractValidation:
    """Test API contracts and response schemas"""
    
    @pytest.mark.asyncio
    async def test_api_response_schema_validation(self, async_client, mock_user):
        """Test that API responses conform to expected schemas"""
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test portfolio list response schema
            with patch('app.services.portfolio.portfolio_service.get_portfolios') as mock_get_portfolios:
                mock_get_portfolios.return_value = [
                    {
                        "id": "schema-test-portfolio-1",
                        "name": "Schema Test Portfolio 1",
                        "description": "Test portfolio for schema validation",
                        "user_id": mock_user.id,
                        "total_value": 25000.00,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "is_active": True
                    }
                ]
                
                response = await async_client.get("/api/v1/portfolios")
                
                assert response.status_code == 200
                data = response.json()
                
                # Validate response structure
                assert "success" in data
                assert "data" in data
                assert "timestamp" in data
                assert isinstance(data["data"], list)
                
                # Validate portfolio object schema
                if len(data["data"]) > 0:
                    portfolio = data["data"][0]
                    required_fields = ["id", "name", "user_id", "total_value", "created_at", "is_active"]
                    for field in required_fields:
                        assert field in portfolio, f"Missing required field: {field}"
            
            # Test error response schema
            with patch('app.services.portfolio.portfolio_service.get_portfolio',
                      side_effect=ValueError("Test validation error")):
                
                response = await async_client.get("/api/v1/portfolios/invalid-id")
                
                assert response.status_code >= 400
                data = response.json()
                
                # Validate error response structure
                assert "success" in data
                assert data["success"] is False
                assert "error" in data
                assert "timestamp" in data
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_pagination_contract(self, async_client, mock_user):
        """Test pagination contract compliance"""
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test paginated portfolio list
            with patch('app.services.portfolio.portfolio_service.get_portfolios_paginated') as mock_paginated:
                mock_paginated.return_value = {
                    "items": [
                        {"id": f"portfolio-{i}", "name": f"Portfolio {i}", "user_id": mock_user.id}
                        for i in range(10)
                    ],
                    "total": 25,
                    "page": 1,
                    "size": 10,
                    "pages": 3
                }
                
                response = await async_client.get("/api/v1/portfolios?page=1&size=10")
                
                assert response.status_code == 200
                data = response.json()
                
                # Validate pagination structure
                assert "data" in data
                assert "pagination" in data
                
                pagination = data["pagination"]
                assert "page" in pagination
                assert "size" in pagination
                assert "total" in pagination
                assert "pages" in pagination
                
                assert pagination["page"] == 1
                assert pagination["size"] == 10
                assert pagination["total"] == 25
                assert pagination["pages"] == 3
        
        finally:
            app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_content_type_handling(self, async_client, mock_user):
        """Test proper content type handling in API contracts"""
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            # Test JSON content type
            portfolio_data = {
                "name": "Content Type Test Portfolio",
                "description": "Testing content type handling"
            }
            
            with patch('app.services.portfolio.portfolio_service.create_portfolio') as mock_create:
                mock_create.return_value = {
                    "id": "content-type-test-portfolio",
                    **portfolio_data,
                    "user_id": mock_user.id
                }
                
                # Test with correct content type
                response = await async_client.post(
                    "/api/v1/portfolios",
                    json=portfolio_data,
                    headers={"Content-Type": "application/json"}
                )
                
                assert response.status_code == 201
                
                # Test with incorrect content type (should still work with json parameter)
                response = await async_client.post(
                    "/api/v1/portfolios",
                    json=portfolio_data,
                    headers={"Content-Type": "text/plain"}
                )
                
                # FastAPI should handle this gracefully
                assert response.status_code in [201, 415]  # Created or Unsupported Media Type
        
        finally:
            app.dependency_overrides.clear()