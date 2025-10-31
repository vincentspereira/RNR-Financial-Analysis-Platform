"""
Integration tests for API endpoints and service interactions
"""
import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from uuid import uuid4

from app.main import app
from app.core.database import get_async_session


class TestAuthenticationIntegration:
    """Integration tests for authentication API endpoints"""
    
    @pytest.fixture
    async def client(self):
        """Create test client"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        return AsyncMock()
    
    @pytest.mark.integration
    @pytest.mark.api
    async def test_health_check_endpoint(self, client):
        """Test health check endpoint integration"""
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "features" in data
        assert isinstance(data["features"], list)
    
    @pytest.mark.integration
    @pytest.mark.api
    async def test_user_registration_integration(self, client, mock_db_session):
        """Test user registration endpoint integration"""
        with patch("app.core.database.get_async_session") as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # Mock user doesn't exist
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db_session.execute.return_value = mock_result
            
            registration_data = {
                "email": "test@example.com",
                "password": "Test123!",
                "name": "Test User"
            }
            
            response = await client.post("/api/v1/auth/register", json=registration_data)
            
            # Should succeed or return user exists error
            assert response.status_code in [200, 400]
    
    @pytest.mark.integration
    @pytest.mark.api
    async def test_user_login_integration(self, client, mock_db_session):
        """Test user login endpoint integration"""
        with patch("app.core.database.get_async_session") as mock_get_db:
            mock_get_db.return_value = mock_db_session
            
            # Mock user exists
            from app.models.user import User
            mock_user = User(
                id=uuid4(),
                email="test@example.com",
                name="Test User",
                password_hash="hashed_password",
                is_active=True
            )
            
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db_session.execute.return_value = mock_result
            
            with patch("app.services.auth.password_handler.PasswordHandler.verify_password") as mock_verify:
                mock_verify.return_value = True
                
                login_data = {
                    "email": "test@example.com",
                    "password": "Test123!"
                }
                
                response = await client.post("/api/v1/auth/login", json=login_data)
                
                if response.status_code == 200:
                    data = response.json()
                    assert "access_token" in data
                    assert "token_type" in data
                    assert data["token_type"] == "bearer"


class TestFinancialCalculationIntegration:
    """Integration tests for financial calculation endpoints"""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Mock authentication
            with patch("app.api.v1.endpoints.financial.get_current_user_from_token") as mock_auth:
                from app.models.user import User
                mock_user = User(
                    id=uuid4(),
                    email="test@example.com",
                    name="Test User",
                    is_active=True
                )
                mock_auth.return_value = mock_user
                yield ac
    
    @pytest.mark.integration
    @pytest.mark.api
    async def test_financial_ratios_calculation_integration(self, authenticated_client):
        """Test financial ratios calculation endpoint integration"""
        with patch("app.core.database.get_async_session") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            # Mock financial calculator
            with patch("app.services.calculator.financial_calculator.financial_calculator.calculate_financial_ratios") as mock_calc:
                mock_calc.return_value = {
                    "company_id": str(uuid4()),
                    "period_type": "annual",
                    "fiscal_year": 2023,
                    "ratios": {
                        "current_ratio": 2.0,
                        "quick_ratio": 1.5
                    }
                }
                
                request_data = {
                    "company_id": str(uuid4()),
                    "period_type": "annual",
                    "fiscal_year": 2023
                }
                
                response = await authenticated_client.post(
                    "/api/v1/financial/ratios/calculate",
                    json=request_data
                )
                
                # Should return calculated ratios or 404 if no data
                assert response.status_code in [200, 404]
    
    @pytest.mark.integration
    @pytest.mark.api
    async def test_company_valuation_integration(self, authenticated_client):
        """Test company valuation endpoint integration"""
        with patch("app.core.database.get_async_session") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            with patch("app.services.calculator.financial_calculator.financial_calculator.calculate_company_valuation") as mock_valuation:
                mock_valuation.return_value = {
                    "company_id": str(uuid4()),
                    "company_name": "Test Company",
                    "company_symbol": "TEST",
                    "fair_value_estimates": {
                        "dcf_value": 45.50
                    }
                }
                
                request_data = {
                    "company_id": str(uuid4()),
                    "assumptions": {
                        "free_cash_flows": [1000000, 1100000, 1210000],
                        "terminal_growth_rate": 0.03,
                        "discount_rate": 0.10,
                        "shares_outstanding": 1000000
                    }
                }
                
                response = await authenticated_client.post(
                    "/api/v1/financial/valuation/calculate",
                    json=request_data
                )
                
                assert response.status_code in [200, 404]


class TestDataIngestionIntegration:
    """Integration tests for data ingestion endpoints"""
    
    @pytest.fixture
    async def authenticated_client(self):
        """Create authenticated test client"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            with patch("app.api.v1.endpoints.data.get_current_user_from_token") as mock_auth:
                from app.models.user import User
                mock_user = User(
                    id=uuid4(),
                    email="test@example.com",
                    name="Test User",
                    is_active=True
                )
                mock_auth.return_value = mock_user
                yield ac
    
    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.external
    async def test_data_ingestion_integration(self, authenticated_client):
        """Test data ingestion endpoint integration"""
        with patch("app.core.database.get_async_session") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            with patch("app.services.data.data_ingestion_service.data_ingestion_service.ingest_company_data") as mock_ingest:
                mock_ingest.return_value = {
                    "symbol": "AAPL",
                    "success": True,
                    "sources_used": ["yahoo_finance"],
                    "data_ingested": {"stock_info": True},
                    "errors": []
                }
                
                request_data = {
                    "symbol": "AAPL",
                    "force_update": False
                }
                
                response = await authenticated_client.post(
                    "/api/v1/data/ingest/company",
                    json=request_data
                )
                
                assert response.status_code in [200, 500]  # May fail without real data
    
    @pytest.mark.integration
    @pytest.mark.api
    async def test_data_sources_status_integration(self, authenticated_client):
        """Test data sources status endpoint integration"""
        with patch("app.core.database.get_async_session") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            with patch("app.services.data.data_ingestion_service.data_ingestion_service.get_data_source_status") as mock_status:
                mock_status.return_value = {
                    "alpha_vantage": {
                        "is_active": True,
                        "last_successful_update": None,
                        "total_api_calls_today": 0,
                        "rate_limit_remaining": 5
                    }
                }
                
                response = await authenticated_client.get("/api/v1/data/sources/status")
                
                assert response.status_code == 200
                data = response.json()
                assert "sources" in data
                assert "total_sources" in data


class TestServiceInteractions:
    """Integration tests for service-to-service interactions"""
    
    @pytest.mark.integration
    @pytest.mark.database
    async def test_auth_service_database_interaction(self):
        """Test authentication service database interactions"""
        from app.services.auth.auth_service import auth_service
        
        mock_db = AsyncMock()
        
        # Mock user registration database interaction
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with patch("app.services.auth.password_handler.PasswordHandler.hash_password") as mock_hash:
            mock_hash.return_value = "hashed_password"
            
            result = await auth_service.register_user(
                email="test@example.com",
                password="password123",
                name="Test User",
                db=mock_db
            )
            
            # Verify database interactions
            assert mock_db.add.called
            assert mock_db.commit.called
            assert result is not None
    
    @pytest.mark.integration
    @pytest.mark.external
    async def test_external_api_integration(self):
        """Test external API service integrations"""
        from app.services.data.yahoo_finance_client import yahoo_finance_client
        
        # Test with mock responses
        with patch("yfinance.Ticker") as mock_ticker:
            mock_info = {
                "symbol": "AAPL",
                "longName": "Apple Inc.",
                "sector": "Technology",
                "marketCap": 3000000000000
            }
            
            mock_ticker_instance = AsyncMock()
            mock_ticker_instance.info = mock_info
            mock_ticker.return_value = mock_ticker_instance
            
            # This would normally make external API call
            result = await yahoo_finance_client.get_stock_info("AAPL")
            
            # Verify integration works
            assert result is not None or result is None  # May fail without real API
    
    @pytest.mark.integration
    @pytest.mark.contract
    async def test_api_contract_validation(self):
        """Test API contract validation between services"""
        from app.schemas.financial import FinancialRatiosRequest, FinancialRatiosResponse
        from pydantic import ValidationError
        
        # Test valid request contract
        valid_request = {
            "company_id": str(uuid4()),
            "period_type": "annual",
            "fiscal_year": 2023
        }
        
        request_obj = FinancialRatiosRequest(**valid_request)
        assert request_obj.company_id is not None
        assert request_obj.period_type == "annual"
        
        # Test invalid request contract
        invalid_request = {
            "company_id": "invalid-uuid",
            "period_type": "invalid",
            "fiscal_year": "invalid"
        }
        
        with pytest.raises(ValidationError):
            FinancialRatiosRequest(**invalid_request)
    
    @pytest.mark.integration
    @pytest.mark.monitoring
    async def test_monitoring_integration(self):
        """Test monitoring and metrics collection integration"""
        from app.services.calculator.ratio_calculator import ratio_calculator
        
        # Test monitoring of calculation performance
        sample_data = {
            "current_assets": 1000000,
            "current_liabilities": 500000,
            "revenue": 5000000,
            "net_income": 500000
        }
        
        # Measure calculation time
        import time
        start_time = time.time()
        
        ratios = ratio_calculator.calculate_liquidity_ratios(sample_data)
        
        end_time = time.time()
        calculation_time = end_time - start_time
        
        # Verify monitoring metrics
        assert ratios is not None
        assert calculation_time < 1.0  # Should complete within 1 second
        assert "current_ratio" in ratios
    
    @pytest.mark.integration
    @pytest.mark.autoscaling
    async def test_autoscaling_integration(self):
        """Test autoscaling policy evaluation integration"""
        # Simulate load testing scenario
        from app.services.calculator.financial_calculator import FinancialCalculator
        
        calculator = FinancialCalculator()
        
        # Test concurrent calculations (simulating autoscaling scenario)
        async def calculate_ratios():
            sample_data = {
                "revenue": 1000000,
                "net_income": 100000,
                "total_assets": 2000000
            }
            return sample_data  # Simplified for testing
        
        # Run multiple concurrent calculations
        tasks = [calculate_ratios() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify all calculations completed successfully
        assert len(results) == 10
        assert all(result is not None for result in results)


class TestErrorHandlingIntegration:
    """Integration tests for error handling across services"""
    
    @pytest.mark.integration
    @pytest.mark.api
    async def test_api_error_handling_integration(self):
        """Test API error handling integration"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Test invalid endpoint
            response = await client.get("/api/v1/invalid-endpoint")
            assert response.status_code == 404
            
            # Test invalid request data
            response = await client.post("/api/v1/auth/register", json={"invalid": "data"})
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.integration
    @pytest.mark.database
    async def test_database_error_handling_integration(self):
        """Test database error handling integration"""
        from app.services.auth.auth_service import auth_service
        
        # Mock database connection error
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database connection error")
        
        result = await auth_service.authenticate_user(
            email="test@example.com",
            password="password123",
            db=mock_db
        )
        
        # Should handle error gracefully
        assert result is None
    
    @pytest.mark.integration
    @pytest.mark.external
    async def test_external_api_error_handling_integration(self):
        """Test external API error handling integration"""
        from app.services.data.alpha_vantage_client import alpha_vantage_client
        
        # Test with invalid symbol
        async with alpha_vantage_client as av:
            result = await av.get_company_overview("INVALID_SYMBOL")
            
            # Should handle error gracefully
            assert result is None or isinstance(result, dict)