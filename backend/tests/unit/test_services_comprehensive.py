"""
Comprehensive Unit Tests for Service Modules - 100% Coverage Target
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
import json
import hashlib

# Service imports - using actual available modules
from app.services.auth.auth_service import AuthService
from app.services.auth.jwt_handler import JWTHandler
from app.services.auth.password_handler import PasswordHandler
from app.services.calculator.financial_calculator import FinancialCalculator
from app.services.calculator.ratio_calculator import RatioCalculator
from app.services.calculator.valuation_calculator import ValuationCalculator
from app.services.data.data_ingestion_service import DataIngestionService
from app.services.data.alpha_vantage_client import AlphaVantageClient
from app.services.data.yahoo_finance_client import YahooFinanceClient
from app.services.analytics.ml_service import FinancialMLService  # Use actual class name


class TestAuthService:
    """Comprehensive tests for AuthService"""
    
    @pytest.fixture
    def auth_service(self):
        """Create auth service instance"""
        return AuthService()
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_user_data(self):
        """Mock user data"""
        return {
            "id": "user-123",
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": "$2b$12$hashedpassword",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.now(datetime.UTC),
        "updated_at": datetime.now(datetime.UTC)
        }
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, mock_db, mock_user_data):
        """Test successful user registration"""
        registration_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "full_name": "New User",
            "first_name": "New",
            "last_name": "User"
        }
        
        with patch.object(auth_service, '_check_user_exists', return_value=False), \
             patch.object(auth_service, '_create_user_record', return_value=mock_user_data), \
             patch.object(auth_service, '_send_verification_email', return_value=True):
            
            result = await auth_service.register_user(registration_data, mock_db)
            
            assert result["email"] == mock_user_data["email"]
            assert result["full_name"] == mock_user_data["full_name"]
            assert "password" not in result
            assert "hashed_password" not in result
    
    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, auth_service, mock_db):
        """Test registration with duplicate email"""
        registration_data = {
            "email": "existing@example.com",
            "password": "SecurePassword123!",
            "full_name": "Existing User"
        }
        
        with patch.object(auth_service, '_check_user_exists', return_value=True):
            with pytest.raises(ValueError, match="Email already registered"):
                await auth_service.register_user(registration_data, mock_db)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, mock_db, mock_user_data):
        """Test successful user authentication"""
        credentials = {
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
        
        with patch.object(auth_service, '_get_user_by_email', return_value=mock_user_data), \
             patch.object(auth_service, '_verify_password', return_value=True), \
             patch.object(auth_service, '_generate_tokens') as mock_tokens:
            
            mock_tokens.return_value = {
                "access_token": "access-token-123",
                "refresh_token": "refresh-token-456",
                "token_type": "bearer",
                "expires_in": 1800
            }
            
            result = await auth_service.authenticate_user(credentials, mock_db)
            
            assert result["access_token"] == "access-token-123"
            assert result["refresh_token"] == "refresh-token-456"
            assert result["user"]["email"] == mock_user_data["email"]
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(self, auth_service, mock_db, mock_user_data):
        """Test authentication with invalid credentials"""
        credentials = {
            "email": "test@example.com",
            "password": "WrongPassword"
        }
        
        with patch.object(auth_service, '_get_user_by_email', return_value=mock_user_data), \
             patch.object(auth_service, '_verify_password', return_value=False):
            
            with pytest.raises(ValueError, match="Invalid credentials"):
                await auth_service.authenticate_user(credentials, mock_db)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_inactive_account(self, auth_service, mock_db, mock_user_data):
        """Test authentication with inactive account"""
        mock_user_data["is_active"] = False
        credentials = {
            "email": "test@example.com",
            "password": "SecurePassword123!"
        }
        
        with patch.object(auth_service, '_get_user_by_email', return_value=mock_user_data):
            with pytest.raises(ValueError, match="Account is disabled"):
                await auth_service.authenticate_user(credentials, mock_db)
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, auth_service, mock_db, mock_user_data):
        """Test successful token refresh"""
        refresh_token = "valid-refresh-token"
        
        with patch.object(auth_service, '_verify_refresh_token', return_value={"user_id": "user-123"}), \
             patch.object(auth_service, '_get_user_by_id', return_value=mock_user_data), \
             patch.object(auth_service, '_generate_access_token', return_value="new-access-token"):
            
            result = await auth_service.refresh_token(refresh_token, mock_db)
            
            assert result["access_token"] == "new-access-token"
            assert result["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, auth_service, mock_db):
        """Test token refresh with invalid token"""
        refresh_token = "invalid-refresh-token"
        
        with patch.object(auth_service, '_verify_refresh_token', return_value=None):
            with pytest.raises(ValueError, match="Invalid refresh token"):
                await auth_service.refresh_token(refresh_token, mock_db)
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, auth_service, mock_db, mock_user_data):
        """Test successful password change"""
        user_id = "user-123"
        current_password = "OldPassword123!"
        new_password = "NewPassword123!"
        
        with patch.object(auth_service, '_get_user_by_id', return_value=mock_user_data), \
             patch.object(auth_service, '_verify_password', return_value=True), \
             patch.object(auth_service, '_update_user_password', return_value=True):
            
            result = await auth_service.change_password(user_id, current_password, new_password, mock_db)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, auth_service, mock_db, mock_user_data):
        """Test password change with wrong current password"""
        user_id = "user-123"
        current_password = "WrongPassword"
        new_password = "NewPassword123!"
        
        with patch.object(auth_service, '_get_user_by_id', return_value=mock_user_data), \
             patch.object(auth_service, '_verify_password', return_value=False):
            
            with pytest.raises(ValueError, match="Current password is incorrect"):
                await auth_service.change_password(user_id, current_password, new_password, mock_db)
    
    @pytest.mark.asyncio
    async def test_verify_session_success(self, auth_service, mock_db, mock_user_data):
        """Test successful session verification"""
        access_token = "valid-access-token"
        
        with patch.object(auth_service, '_verify_access_token', return_value={"user_id": "user-123"}), \
             patch.object(auth_service, '_get_user_by_id', return_value=mock_user_data):
            
            result = await auth_service.verify_session(access_token, mock_db)
            
            assert result["email"] == mock_user_data["email"]
            assert result["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_verify_session_invalid_token(self, auth_service, mock_db):
        """Test session verification with invalid token"""
        access_token = "invalid-access-token"
        
        with patch.object(auth_service, '_verify_access_token', return_value=None):
            result = await auth_service.verify_session(access_token, mock_db)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_logout_user_success(self, auth_service, mock_db):
        """Test successful user logout"""
        user_id = "user-123"
        access_token = "access-token-to-invalidate"
        
        with patch.object(auth_service, '_invalidate_token', return_value=True):
            result = await auth_service.logout_user(user_id, access_token, mock_db)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, auth_service, mock_db, mock_user_data):
        """Test getting user by ID"""
        user_id = "user-123"
        
        with patch.object(auth_service, '_get_user_by_id', return_value=mock_user_data):
            result = await auth_service.get_user_by_id(user_id, mock_db)
            
            assert result["id"] == user_id
            assert result["email"] == mock_user_data["email"]
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, auth_service, mock_db):
        """Test getting non-existent user by ID"""
        user_id = "non-existent-user"
        
        with patch.object(auth_service, '_get_user_by_id', return_value=None):
            result = await auth_service.get_user_by_id(user_id, mock_db)
            
            assert result is None


class TestJWTHandler:
    """Comprehensive tests for JWTHandler"""
    
    @pytest.fixture
    def jwt_handler(self):
        """Create JWT handler instance"""
        return JWTHandler()
    
    def test_create_access_token(self, jwt_handler):
        """Test access token creation"""
        user_id = "user-123"
        
        token = jwt_handler.create_access_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts
    
    def test_create_access_token_with_custom_expiry(self, jwt_handler):
        """Test access token creation with custom expiry"""
        user_id = "user-123"
        expires_delta = timedelta(hours=2)
        
        token = jwt_handler.create_access_token(user_id, expires_delta)
        
        assert token is not None
        
        # Verify token contains correct expiry
        payload = jwt_handler.verify_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
    
    def test_create_refresh_token(self, jwt_handler):
        """Test refresh token creation"""
        user_id = "user-123"
        
        token = jwt_handler.create_refresh_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split('.')) == 3
    
    def test_verify_token_valid(self, jwt_handler):
        """Test verification of valid token"""
        user_id = "user-123"
        token = jwt_handler.create_access_token(user_id)
        
        payload = jwt_handler.verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_verify_token_invalid(self, jwt_handler):
        """Test verification of invalid token"""
        invalid_token = "invalid.jwt.token"
        
        payload = jwt_handler.verify_token(invalid_token)
        
        assert payload is None
    
    def test_verify_token_expired(self, jwt_handler):
        """Test verification of expired token"""
        user_id = "user-123"
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = jwt_handler.create_access_token(user_id, expires_delta)
        
        payload = jwt_handler.verify_token(token)
        
        assert payload is None
    
    def test_verify_token_wrong_type(self, jwt_handler):
        """Test verification of token with wrong type"""
        user_id = "user-123"
        access_token = jwt_handler.create_access_token(user_id)
        
        # Try to verify access token as refresh token
        payload = jwt_handler.verify_token(access_token, "refresh")
        
        assert payload is None
    
    def test_decode_token_without_verification(self, jwt_handler):
        """Test decoding token without verification"""
        user_id = "user-123"
        token = jwt_handler.create_access_token(user_id)
        
        payload = jwt_handler.decode_token_without_verification(token)
        
        assert payload is not None
        assert payload["sub"] == user_id
    
    def test_get_token_expiry(self, jwt_handler):
        """Test getting token expiry time"""
        user_id = "user-123"
        token = jwt_handler.create_access_token(user_id)
        
        expiry = jwt_handler.get_token_expiry(token)
        
        assert expiry is not None
        assert isinstance(expiry, datetime)
        assert expiry > datetime.now(datetime.UTC)
    
    def test_is_token_expired(self, jwt_handler):
        """Test checking if token is expired"""
        user_id = "user-123"
        
        # Create valid token
        valid_token = jwt_handler.create_access_token(user_id)
        assert jwt_handler.is_token_expired(valid_token) is False
        
        # Create expired token
        expired_token = jwt_handler.create_access_token(user_id, timedelta(seconds=-1))
        assert jwt_handler.is_token_expired(expired_token) is True


class TestPasswordHandler:
    """Comprehensive tests for PasswordHandler"""
    
    @pytest.fixture
    def password_handler(self):
        """Create password handler instance"""
        return PasswordHandler()
    
    def test_hash_password(self, password_handler):
        """Test password hashing"""
        password = "SecurePassword123!"
        
        hashed = password_handler.hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")
        assert len(hashed) >= 50
    
    def test_verify_password_correct(self, password_handler):
        """Test password verification with correct password"""
        password = "SecurePassword123!"
        hashed = password_handler.hash_password(password)
        
        result = password_handler.verify_password(password, hashed)
        
        assert result is True
    
    def test_verify_password_incorrect(self, password_handler):
        """Test password verification with incorrect password"""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword123!"
        hashed = password_handler.hash_password(password)
        
        result = password_handler.verify_password(wrong_password, hashed)
        
        assert result is False
    
    def test_generate_random_password(self, password_handler):
        """Test random password generation"""
        password = password_handler.generate_random_password()
        
        assert password is not None
        assert len(password) >= 12
        assert isinstance(password, str)
        
        # Generate multiple passwords to ensure uniqueness
        passwords = [password_handler.generate_random_password() for _ in range(10)]
        assert len(set(passwords)) == 10
    
    def test_validate_password_strength_strong(self, password_handler):
        """Test password strength validation with strong password"""
        strong_passwords = [
            "SecurePassword123!",
            "MyStr0ng@Password",
            "C0mplex#Pass2024"
        ]
        
        for password in strong_passwords:
            result = password_handler.validate_password_strength(password)
            assert result["is_valid"] is True
            assert result["score"] >= 80
    
    def test_validate_password_strength_weak(self, password_handler):
        """Test password strength validation with weak password"""
        weak_passwords = [
            "password",  # Common word
            "123456",    # Too simple
            "Password",  # Missing numbers and symbols
            "pass123"    # Too short
        ]
        
        for password in weak_passwords:
            result = password_handler.validate_password_strength(password)
            assert result["is_valid"] is False
            assert result["score"] < 60
    
    def test_check_password_history(self, password_handler):
        """Test password history checking"""
        user_id = "user-123"
        new_password = "NewPassword123!"
        password_history = [
            password_handler.hash_password("OldPassword1!"),
            password_handler.hash_password("OldPassword2!"),
            password_handler.hash_password("OldPassword3!")
        ]
        
        # New password should not be in history
        result = password_handler.check_password_history(user_id, new_password, password_history)
        assert result is True
        
        # Password that's in history should be rejected
        old_password = "OldPassword1!"
        result = password_handler.check_password_history(user_id, old_password, password_history)
        assert result is False


class TestFinancialCalculator:
    """Comprehensive tests for FinancialCalculator"""
    
    @pytest.fixture
    def calculator(self):
        """Create financial calculator instance"""
        return FinancialCalculator()
    
    def test_calculate_portfolio_value(self, calculator):
        """Test portfolio value calculation"""
        holdings = [
            {"symbol": "AAPL", "shares": 100, "current_price": 155.00},
            {"symbol": "GOOGL", "shares": 25, "current_price": 2800.00},
            {"symbol": "MSFT", "shares": 50, "current_price": 380.00}
        ]
        
        total_value = calculator.calculate_portfolio_value(holdings)
        
        expected_value = (100 * 155.00) + (25 * 2800.00) + (50 * 380.00)
        assert total_value == expected_value
        assert total_value == 104500.00
    
    def test_calculate_portfolio_return(self, calculator):
        """Test portfolio return calculation"""
        current_value = Decimal("110000.00")
        cost_basis = Decimal("100000.00")
        
        return_amount, return_percentage = calculator.calculate_portfolio_return(current_value, cost_basis)
        
        assert return_amount == Decimal("10000.00")
        assert return_percentage == Decimal("10.00")
    
    def test_calculate_portfolio_return_loss(self, calculator):
        """Test portfolio return calculation with loss"""
        current_value = Decimal("90000.00")
        cost_basis = Decimal("100000.00")
        
        return_amount, return_percentage = calculator.calculate_portfolio_return(current_value, cost_basis)
        
        assert return_amount == Decimal("-10000.00")
        assert return_percentage == Decimal("-10.00")
    
    def test_calculate_compound_interest(self, calculator):
        """Test compound interest calculation"""
        principal = Decimal("10000.00")
        annual_rate = Decimal("0.08")  # 8%
        years = 5
        compounds_per_year = 12  # Monthly compounding
        
        future_value = calculator.calculate_compound_interest(
            principal, annual_rate, years, compounds_per_year
        )
        
        # Expected: 10000 * (1 + 0.08/12)^(12*5)
        expected = principal * ((1 + annual_rate / compounds_per_year) ** (compounds_per_year * years))
        assert abs(future_value - expected) < Decimal("0.01")
    
    def test_calculate_present_value(self, calculator):
        """Test present value calculation"""
        future_value = Decimal("15000.00")
        discount_rate = Decimal("0.08")
        years = 5
        
        present_value = calculator.calculate_present_value(future_value, discount_rate, years)
        
        # Expected: 15000 / (1 + 0.08)^5
        expected = future_value / ((1 + discount_rate) ** years)
        assert abs(present_value - expected) < Decimal("0.01")
    
    def test_calculate_annualized_return(self, calculator):
        """Test annualized return calculation"""
        beginning_value = Decimal("100000.00")
        ending_value = Decimal("121000.00")
        years = Decimal("2")
        
        annualized_return = calculator.calculate_annualized_return(
            beginning_value, ending_value, years
        )
        
        # Expected: (121000/100000)^(1/2) - 1 = 0.10 (10%)
        expected = ((ending_value / beginning_value) ** (1 / years)) - 1
        assert abs(annualized_return - expected) < Decimal("0.0001")
    
    def test_calculate_volatility(self, calculator):
        """Test volatility calculation"""
        returns = [
            Decimal("0.05"), Decimal("-0.02"), Decimal("0.03"),
            Decimal("0.01"), Decimal("-0.01"), Decimal("0.04"),
            Decimal("0.02"), Decimal("-0.03"), Decimal("0.06")
        ]
        
        volatility = calculator.calculate_volatility(returns)
        
        assert volatility > 0
        assert isinstance(volatility, Decimal)
    
    def test_calculate_sharpe_ratio(self, calculator):
        """Test Sharpe ratio calculation"""
        portfolio_return = Decimal("0.12")  # 12%
        risk_free_rate = Decimal("0.03")    # 3%
        volatility = Decimal("0.15")        # 15%
        
        sharpe_ratio = calculator.calculate_sharpe_ratio(
            portfolio_return, risk_free_rate, volatility
        )
        
        expected = (portfolio_return - risk_free_rate) / volatility
        assert sharpe_ratio == expected
        assert sharpe_ratio == Decimal("0.60")
    
    def test_calculate_beta(self, calculator):
        """Test beta calculation"""
        stock_returns = [0.05, -0.02, 0.03, 0.01, -0.01]
        market_returns = [0.04, -0.01, 0.02, 0.01, 0.00]
        
        beta = calculator.calculate_beta(stock_returns, market_returns)
        
        assert isinstance(beta, Decimal)
        assert beta > 0  # Assuming positive correlation
    
    def test_calculate_dividend_yield(self, calculator):
        """Test dividend yield calculation"""
        annual_dividends = Decimal("4.00")
        stock_price = Decimal("100.00")
        
        dividend_yield = calculator.calculate_dividend_yield(annual_dividends, stock_price)
        
        expected = (annual_dividends / stock_price) * 100
        assert dividend_yield == expected
        assert dividend_yield == Decimal("4.00")


class TestRatioCalculator:
    """Comprehensive tests for RatioCalculator"""
    
    @pytest.fixture
    def ratio_calculator(self):
        """Create ratio calculator instance"""
        return RatioCalculator()
    
    @pytest.fixture
    def sample_financial_data(self):
        """Sample financial data for testing"""
        return {
            "revenue": Decimal("1000000"),
            "net_income": Decimal("100000"),
            "total_assets": Decimal("500000"),
            "total_liabilities": Decimal("200000"),
            "shareholders_equity": Decimal("300000"),
            "current_assets": Decimal("150000"),
            "current_liabilities": Decimal("75000"),
            "inventory": Decimal("50000"),
            "accounts_receivable": Decimal("30000"),
            "cost_of_goods_sold": Decimal("600000"),
            "interest_expense": Decimal("10000"),
            "tax_expense": Decimal("20000"),
            "shares_outstanding": Decimal("10000"),
            "market_price_per_share": Decimal("50.00")
        }
    
    def test_calculate_current_ratio(self, ratio_calculator, sample_financial_data):
        """Test current ratio calculation"""
        current_ratio = ratio_calculator.calculate_current_ratio(
            sample_financial_data["current_assets"],
            sample_financial_data["current_liabilities"]
        )
        
        expected = sample_financial_data["current_assets"] / sample_financial_data["current_liabilities"]
        assert current_ratio == expected
        assert current_ratio == Decimal("2.00")
    
    def test_calculate_quick_ratio(self, ratio_calculator, sample_financial_data):
        """Test quick ratio calculation"""
        quick_assets = (sample_financial_data["current_assets"] - 
                       sample_financial_data["inventory"])
        
        quick_ratio = ratio_calculator.calculate_quick_ratio(
            quick_assets,
            sample_financial_data["current_liabilities"]
        )
        
        expected = quick_assets / sample_financial_data["current_liabilities"]
        assert quick_ratio == expected
        assert quick_ratio == Decimal("1.33")
    
    def test_calculate_debt_to_equity_ratio(self, ratio_calculator, sample_financial_data):
        """Test debt-to-equity ratio calculation"""
        debt_to_equity = ratio_calculator.calculate_debt_to_equity_ratio(
            sample_financial_data["total_liabilities"],
            sample_financial_data["shareholders_equity"]
        )
        
        expected = sample_financial_data["total_liabilities"] / sample_financial_data["shareholders_equity"]
        assert debt_to_equity == expected
        assert abs(debt_to_equity - Decimal("0.67")) < Decimal("0.01")
    
    def test_calculate_return_on_assets(self, ratio_calculator, sample_financial_data):
        """Test return on assets calculation"""
        roa = ratio_calculator.calculate_return_on_assets(
            sample_financial_data["net_income"],
            sample_financial_data["total_assets"]
        )
        
        expected = (sample_financial_data["net_income"] / sample_financial_data["total_assets"]) * 100
        assert roa == expected
        assert roa == Decimal("20.00")
    
    def test_calculate_return_on_equity(self, ratio_calculator, sample_financial_data):
        """Test return on equity calculation"""
        roe = ratio_calculator.calculate_return_on_equity(
            sample_financial_data["net_income"],
            sample_financial_data["shareholders_equity"]
        )
        
        expected = (sample_financial_data["net_income"] / sample_financial_data["shareholders_equity"]) * 100
        assert roe == expected
        assert abs(roe - Decimal("33.33")) < Decimal("0.01")
    
    def test_calculate_profit_margin(self, ratio_calculator, sample_financial_data):
        """Test profit margin calculation"""
        profit_margin = ratio_calculator.calculate_profit_margin(
            sample_financial_data["net_income"],
            sample_financial_data["revenue"]
        )
        
        expected = (sample_financial_data["net_income"] / sample_financial_data["revenue"]) * 100
        assert profit_margin == expected
        assert profit_margin == Decimal("10.00")
    
    def test_calculate_asset_turnover(self, ratio_calculator, sample_financial_data):
        """Test asset turnover calculation"""
        asset_turnover = ratio_calculator.calculate_asset_turnover(
            sample_financial_data["revenue"],
            sample_financial_data["total_assets"]
        )
        
        expected = sample_financial_data["revenue"] / sample_financial_data["total_assets"]
        assert asset_turnover == expected
        assert asset_turnover == Decimal("2.00")
    
    def test_calculate_inventory_turnover(self, ratio_calculator, sample_financial_data):
        """Test inventory turnover calculation"""
        inventory_turnover = ratio_calculator.calculate_inventory_turnover(
            sample_financial_data["cost_of_goods_sold"],
            sample_financial_data["inventory"]
        )
        
        expected = sample_financial_data["cost_of_goods_sold"] / sample_financial_data["inventory"]
        assert inventory_turnover == expected
        assert inventory_turnover == Decimal("12.00")
    
    def test_calculate_receivables_turnover(self, ratio_calculator, sample_financial_data):
        """Test receivables turnover calculation"""
        receivables_turnover = ratio_calculator.calculate_receivables_turnover(
            sample_financial_data["revenue"],
            sample_financial_data["accounts_receivable"]
        )
        
        expected = sample_financial_data["revenue"] / sample_financial_data["accounts_receivable"]
        assert receivables_turnover == expected
        assert abs(receivables_turnover - Decimal("33.33")) < Decimal("0.01")
    
    def test_calculate_earnings_per_share(self, ratio_calculator, sample_financial_data):
        """Test earnings per share calculation"""
        eps = ratio_calculator.calculate_earnings_per_share(
            sample_financial_data["net_income"],
            sample_financial_data["shares_outstanding"]
        )
        
        expected = sample_financial_data["net_income"] / sample_financial_data["shares_outstanding"]
        assert eps == expected
        assert eps == Decimal("10.00")
    
    def test_calculate_price_to_earnings_ratio(self, ratio_calculator, sample_financial_data):
        """Test price-to-earnings ratio calculation"""
        eps = sample_financial_data["net_income"] / sample_financial_data["shares_outstanding"]
        
        pe_ratio = ratio_calculator.calculate_price_to_earnings_ratio(
            sample_financial_data["market_price_per_share"],
            eps
        )
        
        expected = sample_financial_data["market_price_per_share"] / eps
        assert pe_ratio == expected
        assert pe_ratio == Decimal("5.00")


class TestValuationCalculator:
    """Comprehensive tests for ValuationCalculator"""
    
    @pytest.fixture
    def valuation_calculator(self):
        """Create valuation calculator instance"""
        return ValuationCalculator()
    
    def test_calculate_dcf_value(self, valuation_calculator):
        """Test discounted cash flow valuation"""
        cash_flows = [Decimal("10000"), Decimal("11000"), Decimal("12100"), Decimal("13310")]
        discount_rate = Decimal("0.10")
        terminal_growth_rate = Decimal("0.03")
        
        dcf_value = valuation_calculator.calculate_dcf_value(
            cash_flows, discount_rate, terminal_growth_rate
        )
        
        assert dcf_value > 0
        assert isinstance(dcf_value, Decimal)
    
    def test_calculate_terminal_value(self, valuation_calculator):
        """Test terminal value calculation"""
        final_cash_flow = Decimal("13310")
        growth_rate = Decimal("0.03")
        discount_rate = Decimal("0.10")
        
        terminal_value = valuation_calculator.calculate_terminal_value(
            final_cash_flow, growth_rate, discount_rate
        )
        
        expected = (final_cash_flow * (1 + growth_rate)) / (discount_rate - growth_rate)
        assert terminal_value == expected
    
    def test_calculate_book_value_per_share(self, valuation_calculator):
        """Test book value per share calculation"""
        shareholders_equity = Decimal("300000")
        shares_outstanding = Decimal("10000")
        
        book_value = valuation_calculator.calculate_book_value_per_share(
            shareholders_equity, shares_outstanding
        )
        
        expected = shareholders_equity / shares_outstanding
        assert book_value == expected
        assert book_value == Decimal("30.00")
    
    def test_calculate_price_to_book_ratio(self, valuation_calculator):
        """Test price-to-book ratio calculation"""
        market_price = Decimal("50.00")
        book_value_per_share = Decimal("30.00")
        
        pb_ratio = valuation_calculator.calculate_price_to_book_ratio(
            market_price, book_value_per_share
        )
        
        expected = market_price / book_value_per_share
        assert pb_ratio == expected
        assert abs(pb_ratio - Decimal("1.67")) < Decimal("0.01")
    
    def test_calculate_enterprise_value(self, valuation_calculator):
        """Test enterprise value calculation"""
        market_cap = Decimal("500000")
        total_debt = Decimal("100000")
        cash_and_equivalents = Decimal("50000")
        
        enterprise_value = valuation_calculator.calculate_enterprise_value(
            market_cap, total_debt, cash_and_equivalents
        )
        
        expected = market_cap + total_debt - cash_and_equivalents
        assert enterprise_value == expected
        assert enterprise_value == Decimal("550000")
    
    def test_calculate_ev_to_ebitda(self, valuation_calculator):
        """Test EV/EBITDA ratio calculation"""
        enterprise_value = Decimal("550000")
        ebitda = Decimal("150000")
        
        ev_ebitda = valuation_calculator.calculate_ev_to_ebitda(
            enterprise_value, ebitda
        )
        
        expected = enterprise_value / ebitda
        assert ev_ebitda == expected
        assert abs(ev_ebitda - Decimal("3.67")) < Decimal("0.01")


class TestDataIngestionService:
    """Comprehensive tests for DataIngestionService"""
    
    @pytest.fixture
    def data_service(self):
        """Create data ingestion service instance"""
        return DataIngestionService()
    
    @pytest.mark.asyncio
    async def test_get_stock_data_success(self, data_service):
        """Test successful stock data retrieval"""
        symbol = "AAPL"
        
        mock_data = {
            "symbol": "AAPL",
            "current_price": 155.00,
            "change": 2.50,
            "change_percent": 1.64,
            "volume": 50000000,
            "market_cap": 2500000000000
        }
        
        with patch.object(data_service, '_fetch_from_primary_source', return_value=mock_data):
            result = await data_service.get_stock_data(symbol)
            
            assert result["symbol"] == "AAPL"
            assert result["current_price"] == 155.00
    
    @pytest.mark.asyncio
    async def test_get_stock_data_with_fallback(self, data_service):
        """Test stock data retrieval with fallback to secondary source"""
        symbol = "AAPL"
        
        mock_data = {
            "symbol": "AAPL",
            "current_price": 155.00,
            "change": 2.50,
            "change_percent": 1.64
        }
        
        with patch.object(data_service, '_fetch_from_primary_source', side_effect=Exception("Primary failed")), \
             patch.object(data_service, '_fetch_from_secondary_source', return_value=mock_data):
            
            result = await data_service.get_stock_data(symbol)
            
            assert result["symbol"] == "AAPL"
            assert result["current_price"] == 155.00
    
    @pytest.mark.asyncio
    async def test_get_historical_data_success(self, data_service):
        """Test successful historical data retrieval"""
        symbol = "AAPL"
        period = "1mo"
        
        mock_data = {
            "symbol": "AAPL",
            "data": [
                {
                    "date": "2024-01-01",
                    "open": 150.00,
                    "high": 155.00,
                    "low": 149.00,
                    "close": 154.00,
                    "volume": 45000000
                }
            ],
            "period": "1mo"
        }
        
        with patch.object(data_service, '_fetch_historical_data', return_value=mock_data):
            result = await data_service.get_historical_data(symbol, period)
            
            assert result["symbol"] == "AAPL"
            assert len(result["data"]) == 1
            assert result["period"] == "1mo"
    
    @pytest.mark.asyncio
    async def test_search_stocks_success(self, data_service):
        """Test successful stock search"""
        query = "apple"
        
        mock_results = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "type": "Common Stock"
            }
        ]
        
        with patch.object(data_service, '_search_stocks', return_value=mock_results):
            result = await data_service.search_stocks(query)
            
            assert len(result) == 1
            assert result[0]["symbol"] == "AAPL"
            assert result[0]["name"] == "Apple Inc."
    
    @pytest.mark.asyncio
    async def test_get_market_data_success(self, data_service):
        """Test successful market data retrieval"""
        mock_data = {
            "indices": {
                "SPY": {"price": 450.00, "change": 5.50},
                "QQQ": {"price": 380.00, "change": 3.20}
            },
            "market_status": "open",
            "last_updated": datetime.now(datetime.UTC).isoformat()
        }
        
        with patch.object(data_service, '_fetch_market_data', return_value=mock_data):
            result = await data_service.get_market_data()
            
            assert "indices" in result
            assert result["market_status"] == "open"
            assert "SPY" in result["indices"]
    
    @pytest.mark.asyncio
    async def test_data_caching(self, data_service):
        """Test data caching functionality"""
        symbol = "AAPL"
        
        mock_data = {
            "symbol": "AAPL",
            "current_price": 155.00
        }
        
        with patch.object(data_service, '_fetch_from_primary_source', return_value=mock_data) as mock_fetch, \
             patch.object(data_service, 'cache') as mock_cache:
            
            mock_cache.get.return_value = None  # Cache miss
            mock_cache.set.return_value = True
            
            # First call should fetch from source
            result1 = await data_service.get_stock_data(symbol)
            assert mock_fetch.call_count == 1
            
            # Second call with cache hit
            mock_cache.get.return_value = mock_data
            result2 = await data_service.get_stock_data(symbol)
            assert mock_fetch.call_count == 1  # Should not fetch again
            
            assert result1 == result2


class TestAlphaVantageClient:
    """Comprehensive tests for AlphaVantageClient"""
    
    @pytest.fixture
    def alpha_vantage_client(self):
        """Create Alpha Vantage client instance"""
        return AlphaVantageClient(api_key="test_api_key")
    
    @pytest.mark.asyncio
    async def test_get_quote_success(self, alpha_vantage_client):
        """Test successful quote retrieval"""
        symbol = "AAPL"
        
        mock_response = {
            "Global Quote": {
                "01. symbol": "AAPL",
                "05. price": "155.00",
                "09. change": "2.50",
                "10. change percent": "1.64%"
            }
        }
        
        with patch.object(alpha_vantage_client, '_make_request', return_value=mock_response):
            result = await alpha_vantage_client.get_quote(symbol)
            
            assert result["symbol"] == "AAPL"
            assert result["price"] == 155.00
            assert result["change"] == 2.50
    
    @pytest.mark.asyncio
    async def test_get_intraday_data_success(self, alpha_vantage_client):
        """Test successful intraday data retrieval"""
        symbol = "AAPL"
        interval = "5min"
        
        mock_response = {
            "Time Series (5min)": {
                "2024-01-01 16:00:00": {
                    "1. open": "150.00",
                    "2. high": "155.00",
                    "3. low": "149.00",
                    "4. close": "154.00",
                    "5. volume": "45000000"
                }
            }
        }
        
        with patch.object(alpha_vantage_client, '_make_request', return_value=mock_response):
            result = await alpha_vantage_client.get_intraday_data(symbol, interval)
            
            assert symbol in result
            assert len(result[symbol]) > 0
    
    @pytest.mark.asyncio
    async def test_api_rate_limiting(self, alpha_vantage_client):
        """Test API rate limiting handling"""
        symbol = "AAPL"
        
        # Mock rate limit response
        with patch.object(alpha_vantage_client, '_make_request', 
                         side_effect=Exception("API call frequency exceeded")):
            
            with pytest.raises(Exception, match="API call frequency exceeded"):
                await alpha_vantage_client.get_quote(symbol)
    
    @pytest.mark.asyncio
    async def test_invalid_api_key(self, alpha_vantage_client):
        """Test handling of invalid API key"""
        symbol = "AAPL"
        
        mock_response = {
            "Error Message": "Invalid API call"
        }
        
        with patch.object(alpha_vantage_client, '_make_request', return_value=mock_response):
            with pytest.raises(ValueError, match="Invalid API call"):
                await alpha_vantage_client.get_quote(symbol)


class TestYahooFinanceClient:
    """Comprehensive tests for YahooFinanceClient"""
    
    @pytest.fixture
    def yahoo_client(self):
        """Create Yahoo Finance client instance"""
        return YahooFinanceClient()
    
    @pytest.mark.asyncio
    async def test_get_stock_info_success(self, yahoo_client):
        """Test successful stock info retrieval"""
        symbol = "AAPL"
        
        mock_data = {
            "symbol": "AAPL",
            "regularMarketPrice": 155.00,
            "regularMarketChange": 2.50,
            "regularMarketChangePercent": 0.0164,
            "regularMarketVolume": 50000000
        }
        
        with patch.object(yahoo_client, '_fetch_stock_data', return_value=mock_data):
            result = await yahoo_client.get_stock_info(symbol)
            
            assert result["symbol"] == "AAPL"
            assert result["price"] == 155.00
    
    @pytest.mark.asyncio
    async def test_get_historical_prices_success(self, yahoo_client):
        """Test successful historical prices retrieval"""
        symbol = "AAPL"
        period = "1mo"
        
        mock_data = [
            {
                "Date": "2024-01-01",
                "Open": 150.00,
                "High": 155.00,
                "Low": 149.00,
                "Close": 154.00,
                "Volume": 45000000
            }
        ]
        
        with patch.object(yahoo_client, '_fetch_historical_data', return_value=mock_data):
            result = await yahoo_client.get_historical_prices(symbol, period)
            
            assert len(result) == 1
            assert result[0]["Close"] == 154.00
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, yahoo_client):
        """Test connection error handling"""
        symbol = "AAPL"
        
        with patch.object(yahoo_client, '_fetch_stock_data', 
                         side_effect=Exception("Connection failed")):
            
            with pytest.raises(Exception, match="Connection failed"):
                await yahoo_client.get_stock_info(symbol)


class TestMLService:
    """Comprehensive tests for MLService"""
    
    @pytest.fixture
    def ml_service(self):
        """Create ML service instance"""
        return MLService()
    
    @pytest.mark.asyncio
    async def test_predict_stock_price_success(self, ml_service):
        """Test successful stock price prediction"""
        symbol = "AAPL"
        days_ahead = 30
        
        mock_prediction = {
            "symbol": "AAPL",
            "predicted_price": 165.50,
            "confidence_score": 0.78,
            "current_price": 155.00,
            "model_used": "random_forest"
        }
        
        with patch.object(ml_service, '_load_model', return_value=Mock()), \
             patch.object(ml_service, '_prepare_features', return_value=Mock()), \
             patch.object(ml_service, '_make_prediction', return_value=mock_prediction):
            
            result = await ml_service.predict_stock_price(symbol, days_ahead)
            
            assert result["symbol"] == "AAPL"
            assert result["predicted_price"] == 165.50
            assert result["confidence_score"] == 0.78
    
    @pytest.mark.asyncio
    async def test_analyze_portfolio_risk_success(self, ml_service):
        """Test successful portfolio risk analysis"""
        portfolio = {
            "AAPL": 0.4,
            "GOOGL": 0.3,
            "MSFT": 0.3
        }
        
        mock_analysis = {
            "expected_return": 0.12,
            "volatility": 0.18,
            "var_95": -0.08,
            "sharpe_ratio": 0.67
        }
        
        with patch.object(ml_service, '_calculate_portfolio_metrics', return_value=mock_analysis):
            result = await ml_service.analyze_portfolio_risk(portfolio)
            
            assert result["expected_return"] == 0.12
            assert result["volatility"] == 0.18
            assert result["var_95"] == -0.08
    
    @pytest.mark.asyncio
    async def test_generate_trading_signals_success(self, ml_service):
        """Test successful trading signals generation"""
        symbol = "AAPL"
        indicators = ["rsi", "macd"]
        
        mock_signals = {
            "symbol": "AAPL",
            "signals": [
                {
                    "indicator": "rsi",
                    "signal": "buy",
                    "strength": 0.75
                },
                {
                    "indicator": "macd",
                    "signal": "neutral",
                    "strength": 0.45
                }
            ],
            "overall_signal": "buy",
            "confidence": 0.68
        }
        
        with patch.object(ml_service, '_calculate_indicators', return_value=mock_signals):
            result = await ml_service.generate_trading_signals(symbol, indicators)
            
            assert result["symbol"] == "AAPL"
            assert result["overall_signal"] == "buy"
            assert len(result["signals"]) == 2
    
    @pytest.mark.asyncio
    async def test_model_not_available_fallback(self, ml_service):
        """Test fallback when ML models are not available"""
        symbol = "AAPL"
        days_ahead = 30
        
        with patch.object(ml_service, '_load_model', side_effect=Exception("Model not found")):
            result = await ml_service.predict_stock_price(symbol, days_ahead)
            
            # Should return mock prediction when model is not available
            assert result["symbol"] == symbol
            assert "predicted_price" in result
            assert result.get("model_used") == "mock"


# Edge Cases and Error Handling Tests
class TestServicesEdgeCases:
    """Test edge cases and error conditions for service modules"""
    
    @pytest.mark.asyncio
    async def test_auth_service_database_error(self):
        """Test auth service behavior during database errors"""
        auth_service = AuthService()
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database connection failed")
        
        registration_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User"
        }
        
        with pytest.raises(Exception):
            await auth_service.register_user(registration_data, mock_db)
    
    def test_financial_calculator_zero_division(self):
        """Test financial calculator with zero division scenarios"""
        calculator = FinancialCalculator()
        
        # Test division by zero in return calculation
        with pytest.raises(ZeroDivisionError):
            calculator.calculate_portfolio_return(Decimal("100"), Decimal("0"))
        
        # Test division by zero in Sharpe ratio
        with pytest.raises(ZeroDivisionError):
            calculator.calculate_sharpe_ratio(Decimal("0.1"), Decimal("0.03"), Decimal("0"))
    
    def test_ratio_calculator_negative_values(self):
        """Test ratio calculator with negative values"""
        calculator = RatioCalculator()
        
        # Test with negative equity (should handle gracefully or raise appropriate error)
        try:
            result = calculator.calculate_debt_to_equity_ratio(Decimal("100"), Decimal("-50"))
            # If it doesn't raise an error, result should be negative
            assert result < 0
        except ValueError:
            # This is also acceptable behavior
            pass
    
    @pytest.mark.asyncio
    async def test_data_service_network_timeout(self):
        """Test data service behavior during network timeouts"""
        data_service = DataIngestionService()
        
        with patch.object(data_service, '_fetch_from_primary_source', 
                         side_effect=asyncio.TimeoutError("Request timed out")), \
             patch.object(data_service, '_fetch_from_secondary_source', 
                         side_effect=asyncio.TimeoutError("Request timed out")):
            
            with pytest.raises(Exception):
                await data_service.get_stock_data("AAPL")
    
    def test_jwt_handler_malformed_token(self):
        """Test JWT handler with malformed tokens"""
        jwt_handler = JWTHandler()
        
        malformed_tokens = [
            "not.a.jwt",
            "too.few.parts",
            "too.many.parts.in.this.token",
            "",
            None
        ]
        
        for token in malformed_tokens:
            result = jwt_handler.verify_token(token)
            assert result is None
    
    def test_password_handler_edge_cases(self):
        """Test password handler with edge cases"""
        password_handler = PasswordHandler()
        
        # Test with empty password
        with pytest.raises((ValueError, TypeError)):
            password_handler.hash_password("")
        
        # Test with None password
        with pytest.raises((ValueError, TypeError)):
            password_handler.hash_password(None)
        
        # Test with very long password
        long_password = "A1!" + "a" * 1000
        hashed = password_handler.hash_password(long_password)
        assert hashed is not None
        assert password_handler.verify_password(long_password, hashed)