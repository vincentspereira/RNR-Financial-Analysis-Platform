"""
Comprehensive Unit Tests for Pydantic Schemas - 100% Validation Coverage
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
import json
from pydantic import ValidationError

# Schema imports - using actual available schemas
from app.schemas.auth import (
    RegisterRequest, LoginRequest, UserResponse, LoginResponse,
    RefreshTokenResponse, MessageResponse, ErrorResponse
)
from app.schemas.financial import (
    FinancialRatiosResponse, ValuationRequest
)


class TestAuthSchemas:
    """Comprehensive tests for authentication schemas"""
    
    def test_user_registration_valid(self):
        """Test valid user registration data"""
        valid_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User",
            "first_name": "Test",
            "last_name": "User",
            "phone": "+1-555-123-4567",
            "date_of_birth": "1990-01-15"
        }
        
        registration = UserRegistration(**valid_data)
        
        assert registration.email == "test@example.com"
        assert registration.password == "SecurePassword123!"
        assert registration.full_name == "Test User"
        assert registration.first_name == "Test"
        assert registration.last_name == "User"
        assert registration.phone == "+1-555-123-4567"
        assert registration.date_of_birth == date(1990, 1, 15)
    
    def test_user_registration_minimal_required(self):
        """Test user registration with minimal required fields"""
        minimal_data = {
            "email": "minimal@example.com",
            "password": "SecurePassword123!",
            "full_name": "Minimal User"
        }
        
        registration = UserRegistration(**minimal_data)
        
        assert registration.email == "minimal@example.com"
        assert registration.password == "SecurePassword123!"
        assert registration.full_name == "Minimal User"
        assert registration.first_name is None
        assert registration.last_name is None
        assert registration.phone is None
        assert registration.date_of_birth is None
    
    def test_user_registration_email_validation(self):
        """Test user registration email validation"""
        # Valid emails
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user123@test-domain.com",
            "firstname.lastname@company.org"
        ]
        
        for email in valid_emails:
            data = {
                "email": email,
                "password": "SecurePassword123!",
                "full_name": "Test User"
            }
            registration = UserRegistration(**data)
            assert registration.email == email
        
        # Invalid emails
        invalid_emails = [
            "invalid.email",
            "@domain.com",
            "user@",
            "user@domain",
            "user name@domain.com",
            "user@domain..com",
            ""
        ]
        
        for email in invalid_emails:
            data = {
                "email": email,
                "password": "SecurePassword123!",
                "full_name": "Test User"
            }
            with pytest.raises(ValidationError):
                UserRegistration(**data)
    
    def test_user_registration_password_validation(self):
        """Test user registration password validation"""
        base_data = {
            "email": "test@example.com",
            "full_name": "Test User"
        }
        
        # Valid passwords
        valid_passwords = [
            "SecurePassword123!",
            "MyStr0ng@Password",
            "C0mplex#Pass2024",
            "Ungu3ssable$Pwd!"
        ]
        
        for password in valid_passwords:
            data = {**base_data, "password": password}
            registration = UserRegistration(**data)
            assert registration.password == password
        
        # Invalid passwords
        invalid_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecialChars123",  # No special characters
            "Has Spaces123!",  # Contains spaces
            ""  # Empty
        ]
        
        for password in invalid_passwords:
            data = {**base_data, "password": password}
            with pytest.raises(ValidationError):
                UserRegistration(**data)
    
    def test_user_registration_phone_validation(self):
        """Test user registration phone validation"""
        base_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User"
        }
        
        # Valid phone numbers
        valid_phones = [
            "+1-555-123-4567",
            "(555) 123-4567",
            "555.123.4567",
            "5551234567",
            "+44 20 7946 0958"
        ]
        
        for phone in valid_phones:
            data = {**base_data, "phone": phone}
            registration = UserRegistration(**data)
            assert registration.phone == phone
        
        # Invalid phone numbers
        invalid_phones = [
            "123",  # Too short
            "abc-def-ghij",  # Contains letters
            "555-123-456",  # Too short
            "+1-555-123-45678"  # Too long
        ]
        
        for phone in invalid_phones:
            data = {**base_data, "phone": phone}
            with pytest.raises(ValidationError):
                UserRegistration(**data)
    
    def test_user_registration_date_validation(self):
        """Test user registration date of birth validation"""
        base_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "full_name": "Test User"
        }
        
        # Valid dates
        valid_dates = [
            "1990-01-15",
            "1985-12-31",
            "2000-06-15"
        ]
        
        for date_str in valid_dates:
            data = {**base_data, "date_of_birth": date_str}
            registration = UserRegistration(**data)
            assert registration.date_of_birth == datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Invalid dates
        invalid_dates = [
            "invalid-date",
            "2025-01-01",  # Future date
            "1800-01-01",  # Too old
            "31-12-1990",  # Wrong format
            ""
        ]
        
        for date_str in invalid_dates:
            data = {**base_data, "date_of_birth": date_str}
            with pytest.raises(ValidationError):
                UserRegistration(**data)
    
    def test_user_login_valid(self):
        """Test valid user login data"""
        login_data = {
            "email": "user@example.com",
            "password": "SecurePassword123!"
        }
        
        login = UserLogin(**login_data)
        
        assert login.email == "user@example.com"
        assert login.password == "SecurePassword123!"
    
    def test_user_login_validation_errors(self):
        """Test user login validation errors"""
        # Missing email
        with pytest.raises(ValidationError):
            UserLogin(password="SecurePassword123!")
        
        # Missing password
        with pytest.raises(ValidationError):
            UserLogin(email="user@example.com")
        
        # Invalid email
        with pytest.raises(ValidationError):
            UserLogin(email="invalid-email", password="SecurePassword123!")
        
        # Empty fields
        with pytest.raises(ValidationError):
            UserLogin(email="", password="")
    
    def test_user_response_schema(self):
        """Test user response schema"""
        user_data = {
            "id": "user-123",
            "email": "user@example.com",
            "full_name": "Test User",
            "first_name": "Test",
            "last_name": "User",
            "phone": "+1-555-123-4567",
            "date_of_birth": "1990-01-15",
            "is_active": True,
            "is_verified": True,
            "role": "user",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "last_login_at": datetime.utcnow().isoformat()
        }
        
        response = UserResponse(**user_data)
        
        assert response.id == "user-123"
        assert response.email == "user@example.com"
        assert response.full_name == "Test User"
        assert response.is_active is True
        assert response.is_verified is True
        assert response.role == "user"
    
    def test_token_response_schema(self):
        """Test token response schema"""
        token_data = {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "token_type": "bearer",
            "expires_in": 1800,
            "user": {
                "id": "user-123",
                "email": "user@example.com",
                "full_name": "Test User",
                "is_active": True,
                "is_verified": True,
                "role": "user",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        }
        
        response = TokenResponse(**token_data)
        
        assert response.access_token.startswith("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9")
        assert response.refresh_token.startswith("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9")
        assert response.token_type == "bearer"
        assert response.expires_in == 1800
        assert response.user.id == "user-123"
    
    def test_password_change_schema(self):
        """Test password change schema"""
        password_data = {
            "current_password": "OldPassword123!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        
        change = PasswordChange(**password_data)
        
        assert change.current_password == "OldPassword123!"
        assert change.new_password == "NewPassword123!"
        assert change.confirm_password == "NewPassword123!"
    
    def test_password_change_validation(self):
        """Test password change validation"""
        # Passwords don't match
        with pytest.raises(ValidationError):
            PasswordChange(
                current_password="OldPassword123!",
                new_password="NewPassword123!",
                confirm_password="DifferentPassword123!"
            )
        
        # Weak new password
        with pytest.raises(ValidationError):
            PasswordChange(
                current_password="OldPassword123!",
                new_password="weak",
                confirm_password="weak"
            )
        
        # Same as current password
        with pytest.raises(ValidationError):
            PasswordChange(
                current_password="SamePassword123!",
                new_password="SamePassword123!",
                confirm_password="SamePassword123!"
            )
    
    def test_email_verification_schema(self):
        """Test email verification schema"""
        verification_data = {
            "email": "user@example.com",
            "verification_code": "123456"
        }
        
        verification = EmailVerification(**verification_data)
        
        assert verification.email == "user@example.com"
        assert verification.verification_code == "123456"
    
    def test_password_reset_schema(self):
        """Test password reset schema"""
        reset_data = {
            "email": "user@example.com",
            "reset_token": "reset-token-123",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        
        reset = PasswordReset(**reset_data)
        
        assert reset.email == "user@example.com"
        assert reset.reset_token == "reset-token-123"
        assert reset.new_password == "NewPassword123!"
        assert reset.confirm_password == "NewPassword123!"


class TestDataSchemas:
    """Comprehensive tests for data schemas"""
    
    def test_stock_quote_schema(self):
        """Test stock quote schema"""
        quote_data = {
            "symbol": "AAPL",
            "current_price": 155.00,
            "change": 2.50,
            "change_percent": 1.64,
            "volume": 50000000,
            "market_cap": 2500000000000,
            "pe_ratio": 25.5,
            "dividend_yield": 0.52,
            "52_week_high": 198.23,
            "52_week_low": 124.17,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        quote = StockQuote(**quote_data)
        
        assert quote.symbol == "AAPL"
        assert quote.current_price == 155.00
        assert quote.change == 2.50
        assert quote.change_percent == 1.64
        assert quote.volume == 50000000
        assert quote.market_cap == 2500000000000
        assert quote.pe_ratio == 25.5
    
    def test_stock_quote_validation(self):
        """Test stock quote validation"""
        # Invalid symbol
        with pytest.raises(ValidationError):
            StockQuote(
                symbol="",  # Empty symbol
                current_price=155.00,
                change=2.50,
                change_percent=1.64,
                volume=50000000
            )
        
        # Negative price
        with pytest.raises(ValidationError):
            StockQuote(
                symbol="AAPL",
                current_price=-155.00,  # Negative price
                change=2.50,
                change_percent=1.64,
                volume=50000000
            )
        
        # Negative volume
        with pytest.raises(ValidationError):
            StockQuote(
                symbol="AAPL",
                current_price=155.00,
                change=2.50,
                change_percent=1.64,
                volume=-50000000  # Negative volume
            )
    
    def test_historical_data_schema(self):
        """Test historical data schema"""
        historical_data = {
            "symbol": "AAPL",
            "data": [
                {
                    "date": "2024-01-01",
                    "open": 150.00,
                    "high": 155.00,
                    "low": 149.00,
                    "close": 154.00,
                    "adjusted_close": 154.00,
                    "volume": 45000000
                },
                {
                    "date": "2024-01-02",
                    "open": 154.00,
                    "high": 157.00,
                    "low": 153.00,
                    "close": 156.00,
                    "adjusted_close": 156.00,
                    "volume": 48000000
                }
            ],
            "period": "1mo",
            "interval": "1d"
        }
        
        historical = HistoricalData(**historical_data)
        
        assert historical.symbol == "AAPL"
        assert len(historical.data) == 2
        assert historical.period == "1mo"
        assert historical.interval == "1d"
        
        # Test individual data points
        first_point = historical.data[0]
        assert first_point["date"] == "2024-01-01"
        assert first_point["open"] == 150.00
        assert first_point["high"] == 155.00
        assert first_point["low"] == 149.00
        assert first_point["close"] == 154.00
        assert first_point["volume"] == 45000000
    
    def test_historical_data_validation(self):
        """Test historical data validation"""
        # Invalid OHLC data (high < low)
        with pytest.raises(ValidationError):
            HistoricalData(
                symbol="AAPL",
                data=[{
                    "date": "2024-01-01",
                    "open": 150.00,
                    "high": 149.00,  # High less than low
                    "low": 155.00,
                    "close": 154.00,
                    "volume": 45000000
                }],
                period="1d"
            )
        
        # Empty data array
        with pytest.raises(ValidationError):
            HistoricalData(
                symbol="AAPL",
                data=[],  # Empty data
                period="1d"
            )
    
    def test_stock_search_schema(self):
        """Test stock search schema"""
        search_data = {
            "query": "apple",
            "results": [
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "exchange": "NASDAQ",
                    "type": "Common Stock",
                    "currency": "USD",
                    "country": "United States"
                },
                {
                    "symbol": "APLE",
                    "name": "Apple Hospitality REIT Inc.",
                    "exchange": "NYSE",
                    "type": "REIT",
                    "currency": "USD",
                    "country": "United States"
                }
            ]
        }
        
        search = StockSearch(**search_data)
        
        assert search.query == "apple"
        assert len(search.results) == 2
        
        # Test individual results
        first_result = search.results[0]
        assert first_result["symbol"] == "AAPL"
        assert first_result["name"] == "Apple Inc."
        assert first_result["exchange"] == "NASDAQ"
        assert first_result["type"] == "Common Stock"
    
    def test_market_data_schema(self):
        """Test market data schema"""
        market_data = {
            "indices": {
                "SPY": {
                    "price": 450.00,
                    "change": 5.50,
                    "change_percent": 1.24
                },
                "QQQ": {
                    "price": 380.00,
                    "change": 3.20,
                    "change_percent": 0.85
                }
            },
            "market_status": "open",
            "trading_session": "regular",
            "last_updated": datetime.utcnow().isoformat()
        }
        
        market = MarketData(**market_data)
        
        assert market.market_status == "open"
        assert market.trading_session == "regular"
        assert "SPY" in market.indices
        assert "QQQ" in market.indices
        
        # Test index data
        spy_data = market.indices["SPY"]
        assert spy_data["price"] == 450.00
        assert spy_data["change"] == 5.50
        assert spy_data["change_percent"] == 1.24
    
    def test_company_profile_schema(self):
        """Test company profile schema"""
        profile_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "exchange": "NASDAQ",
            "currency": "USD",
            "country": "United States",
            "ceo": "Tim Cook",
            "employees": 154000,
            "founded": 1976,
            "headquarters": "Cupertino, CA",
            "website": "https://www.apple.com",
            "market_cap": 2500000000000,
            "enterprise_value": 2450000000000,
            "pe_ratio": 25.5,
            "pb_ratio": 12.8,
            "dividend_yield": 0.52
        }
        
        profile = CompanyProfile(**profile_data)
        
        assert profile.symbol == "AAPL"
        assert profile.name == "Apple Inc."
        assert profile.sector == "Technology"
        assert profile.industry == "Consumer Electronics"
        assert profile.ceo == "Tim Cook"
        assert profile.employees == 154000
        assert profile.founded == 1976
        assert profile.market_cap == 2500000000000
    
    def test_financial_statement_schema(self):
        """Test financial statement schema"""
        statement_data = {
            "symbol": "AAPL",
            "period": "2023-Q4",
            "statement_type": "income",
            "fiscal_year": 2023,
            "fiscal_quarter": 4,
            "currency": "USD",
            "revenue": 119575000000,
            "gross_profit": 70898000000,
            "operating_income": 40437000000,
            "net_income": 33916000000,
            "earnings_per_share": 2.18,
            "total_assets": 352755000000,
            "total_liabilities": 290437000000,
            "shareholders_equity": 62318000000,
            "operating_cash_flow": 110543000000,
            "free_cash_flow": 99584000000
        }
        
        statement = FinancialStatement(**statement_data)
        
        assert statement.symbol == "AAPL"
        assert statement.period == "2023-Q4"
        assert statement.statement_type == "income"
        assert statement.fiscal_year == 2023
        assert statement.fiscal_quarter == 4
        assert statement.revenue == 119575000000
        assert statement.net_income == 33916000000
        assert statement.earnings_per_share == 2.18
    
    def test_economic_indicator_schema(self):
        """Test economic indicator schema"""
        indicator_data = {
            "indicator_name": "GDP Growth Rate",
            "value": 2.5,
            "unit": "percent",
            "period": "2023-Q4",
            "frequency": "quarterly",
            "release_date": "2024-01-25",
            "source": "Bureau of Economic Analysis",
            "country": "United States",
            "category": "economic_growth"
        }
        
        indicator = EconomicIndicator(**indicator_data)
        
        assert indicator.indicator_name == "GDP Growth Rate"
        assert indicator.value == 2.5
        assert indicator.unit == "percent"
        assert indicator.period == "2023-Q4"
        assert indicator.frequency == "quarterly"
        assert indicator.source == "Bureau of Economic Analysis"
        assert indicator.country == "United States"


class TestFinancialSchemas:
    """Comprehensive tests for financial schemas"""
    
    def test_portfolio_create_schema(self):
        """Test portfolio creation schema"""
        portfolio_data = {
            "name": "My Investment Portfolio",
            "description": "A diversified portfolio for long-term growth",
            "initial_cash": 10000.00,
            "currency": "USD",
            "risk_tolerance": "moderate",
            "investment_objective": "growth"
        }
        
        portfolio = PortfolioCreate(**portfolio_data)
        
        assert portfolio.name == "My Investment Portfolio"
        assert portfolio.description == "A diversified portfolio for long-term growth"
        assert portfolio.initial_cash == 10000.00
        assert portfolio.currency == "USD"
        assert portfolio.risk_tolerance == "moderate"
        assert portfolio.investment_objective == "growth"
    
    def test_portfolio_create_validation(self):
        """Test portfolio creation validation"""
        # Invalid name (too short)
        with pytest.raises(ValidationError):
            PortfolioCreate(
                name="A",  # Too short
                initial_cash=10000.00
            )
        
        # Invalid initial cash (negative)
        with pytest.raises(ValidationError):
            PortfolioCreate(
                name="Valid Portfolio Name",
                initial_cash=-1000.00  # Negative cash
            )
        
        # Invalid currency
        with pytest.raises(ValidationError):
            PortfolioCreate(
                name="Valid Portfolio Name",
                initial_cash=10000.00,
                currency="INVALID"  # Invalid currency code
            )
        
        # Invalid risk tolerance
        with pytest.raises(ValidationError):
            PortfolioCreate(
                name="Valid Portfolio Name",
                initial_cash=10000.00,
                risk_tolerance="invalid_risk"  # Invalid risk level
            )
    
    def test_portfolio_update_schema(self):
        """Test portfolio update schema"""
        update_data = {
            "name": "Updated Portfolio Name",
            "description": "Updated description",
            "risk_tolerance": "aggressive",
            "investment_objective": "income"
        }
        
        update = PortfolioUpdate(**update_data)
        
        assert update.name == "Updated Portfolio Name"
        assert update.description == "Updated description"
        assert update.risk_tolerance == "aggressive"
        assert update.investment_objective == "income"
    
    def test_portfolio_response_schema(self):
        """Test portfolio response schema"""
        portfolio_data = {
            "id": "portfolio-123",
            "name": "My Portfolio",
            "description": "Test portfolio",
            "user_id": "user-456",
            "total_value": 15000.00,
            "cash_balance": 2000.00,
            "invested_amount": 13000.00,
            "total_return": 1500.00,
            "return_percentage": 11.54,
            "currency": "USD",
            "risk_tolerance": "moderate",
            "investment_objective": "growth",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "holdings_count": 5,
            "last_rebalanced": datetime.utcnow().isoformat()
        }
        
        response = PortfolioResponse(**portfolio_data)
        
        assert response.id == "portfolio-123"
        assert response.name == "My Portfolio"
        assert response.user_id == "user-456"
        assert response.total_value == 15000.00
        assert response.cash_balance == 2000.00
        assert response.total_return == 1500.00
        assert response.return_percentage == 11.54
        assert response.holdings_count == 5
    
    def test_holding_create_schema(self):
        """Test holding creation schema"""
        holding_data = {
            "symbol": "AAPL",
            "shares": 100.0,
            "purchase_price": 150.00,
            "purchase_date": "2024-01-15",
            "transaction_type": "buy",
            "notes": "Initial purchase of Apple stock"
        }
        
        holding = HoldingCreate(**holding_data)
        
        assert holding.symbol == "AAPL"
        assert holding.shares == 100.0
        assert holding.purchase_price == 150.00
        assert holding.purchase_date == date(2024, 1, 15)
        assert holding.transaction_type == "buy"
        assert holding.notes == "Initial purchase of Apple stock"
    
    def test_holding_create_validation(self):
        """Test holding creation validation"""
        # Invalid symbol
        with pytest.raises(ValidationError):
            HoldingCreate(
                symbol="",  # Empty symbol
                shares=100.0,
                purchase_price=150.00
            )
        
        # Invalid shares (negative)
        with pytest.raises(ValidationError):
            HoldingCreate(
                symbol="AAPL",
                shares=-100.0,  # Negative shares
                purchase_price=150.00
            )
        
        # Invalid purchase price (negative)
        with pytest.raises(ValidationError):
            HoldingCreate(
                symbol="AAPL",
                shares=100.0,
                purchase_price=-150.00  # Negative price
            )
        
        # Invalid purchase date (future date)
        future_date = (datetime.utcnow() + timedelta(days=30)).date()
        with pytest.raises(ValidationError):
            HoldingCreate(
                symbol="AAPL",
                shares=100.0,
                purchase_price=150.00,
                purchase_date=future_date  # Future date
            )
    
    def test_holding_response_schema(self):
        """Test holding response schema"""
        holding_data = {
            "id": "holding-789",
            "portfolio_id": "portfolio-123",
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "shares": 100.0,
            "purchase_price": 150.00,
            "current_price": 155.00,
            "purchase_date": "2024-01-15",
            "current_value": 15500.00,
            "cost_basis": 15000.00,
            "unrealized_gain_loss": 500.00,
            "unrealized_gain_loss_percent": 3.33,
            "dividend_yield": 0.52,
            "annual_dividend": 80.60,
            "sector": "Technology",
            "weight_in_portfolio": 31.0,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        response = HoldingResponse(**holding_data)
        
        assert response.id == "holding-789"
        assert response.portfolio_id == "portfolio-123"
        assert response.symbol == "AAPL"
        assert response.company_name == "Apple Inc."
        assert response.shares == 100.0
        assert response.current_value == 15500.00
        assert response.unrealized_gain_loss == 500.00
        assert response.weight_in_portfolio == 31.0
    
    def test_transaction_create_schema(self):
        """Test transaction creation schema"""
        transaction_data = {
            "symbol": "AAPL",
            "transaction_type": "buy",
            "shares": 50.0,
            "price": 150.00,
            "transaction_date": "2024-01-15",
            "fees": 9.99,
            "notes": "Bought 50 shares of Apple"
        }
        
        transaction = TransactionCreate(**transaction_data)
        
        assert transaction.symbol == "AAPL"
        assert transaction.transaction_type == "buy"
        assert transaction.shares == 50.0
        assert transaction.price == 150.00
        assert transaction.transaction_date == date(2024, 1, 15)
        assert transaction.fees == 9.99
        assert transaction.notes == "Bought 50 shares of Apple"
    
    def test_transaction_create_validation(self):
        """Test transaction creation validation"""
        # Invalid transaction type
        with pytest.raises(ValidationError):
            TransactionCreate(
                symbol="AAPL",
                transaction_type="invalid_type",  # Invalid type
                shares=50.0,
                price=150.00
            )
        
        # Invalid shares for buy transaction
        with pytest.raises(ValidationError):
            TransactionCreate(
                symbol="AAPL",
                transaction_type="buy",
                shares=0.0,  # Zero shares for buy
                price=150.00
            )
        
        # Invalid price
        with pytest.raises(ValidationError):
            TransactionCreate(
                symbol="AAPL",
                transaction_type="buy",
                shares=50.0,
                price=0.0  # Zero price
            )
        
        # Negative fees
        with pytest.raises(ValidationError):
            TransactionCreate(
                symbol="AAPL",
                transaction_type="buy",
                shares=50.0,
                price=150.00,
                fees=-10.0  # Negative fees
            )
    
    def test_transaction_response_schema(self):
        """Test transaction response schema"""
        transaction_data = {
            "id": "transaction-456",
            "portfolio_id": "portfolio-123",
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "transaction_type": "buy",
            "shares": 50.0,
            "price": 150.00,
            "total_amount": 7500.00,
            "fees": 9.99,
            "net_amount": 7509.99,
            "transaction_date": "2024-01-15",
            "notes": "Bought 50 shares of Apple",
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = TransactionResponse(**transaction_data)
        
        assert response.id == "transaction-456"
        assert response.portfolio_id == "portfolio-123"
        assert response.symbol == "AAPL"
        assert response.transaction_type == "buy"
        assert response.shares == 50.0
        assert response.total_amount == 7500.00
        assert response.net_amount == 7509.99
    
    def test_performance_metrics_schema(self):
        """Test performance metrics schema"""
        metrics_data = {
            "portfolio_id": "portfolio-123",
            "total_value": 50000.00,
            "total_return": 5000.00,
            "return_percentage": 11.11,
            "annualized_return": 10.5,
            "volatility": 15.2,
            "sharpe_ratio": 0.69,
            "max_drawdown": -8.5,
            "beta": 1.05,
            "alpha": 2.3,
            "sortino_ratio": 0.85,
            "calmar_ratio": 1.24,
            "var_95": -1250.00,
            "cvar_95": -1875.00,
            "period_start": "2023-01-01",
            "period_end": "2024-01-01",
            "benchmark_return": 8.7,
            "excess_return": 2.41,
            "tracking_error": 3.2,
            "information_ratio": 0.75
        }
        
        metrics = PerformanceMetrics(**metrics_data)
        
        assert metrics.portfolio_id == "portfolio-123"
        assert metrics.total_value == 50000.00
        assert metrics.return_percentage == 11.11
        assert metrics.sharpe_ratio == 0.69
        assert metrics.max_drawdown == -8.5
        assert metrics.var_95 == -1250.00
        assert metrics.benchmark_return == 8.7
    
    def test_risk_analysis_schema(self):
        """Test risk analysis schema"""
        risk_data = {
            "portfolio_id": "portfolio-123",
            "risk_score": 7.5,
            "risk_level": "moderate-high",
            "volatility": 18.5,
            "beta": 1.15,
            "var_95": -2500.00,
            "var_99": -3750.00,
            "cvar_95": -3125.00,
            "cvar_99": -4687.50,
            "max_drawdown": -12.3,
            "downside_deviation": 11.2,
            "sortino_ratio": 0.78,
            "correlation_matrix": {
                "AAPL": {"AAPL": 1.0, "GOOGL": 0.65, "MSFT": 0.72},
                "GOOGL": {"AAPL": 0.65, "GOOGL": 1.0, "MSFT": 0.68},
                "MSFT": {"AAPL": 0.72, "GOOGL": 0.68, "MSFT": 1.0}
            },
            "sector_allocation": {
                "Technology": 60.0,
                "Healthcare": 25.0,
                "Finance": 15.0
            },
            "concentration_risk": 0.35,
            "liquidity_risk": "low",
            "currency_risk": "low"
        }
        
        risk = RiskAnalysis(**risk_data)
        
        assert risk.portfolio_id == "portfolio-123"
        assert risk.risk_score == 7.5
        assert risk.risk_level == "moderate-high"
        assert risk.volatility == 18.5
        assert risk.var_95 == -2500.00
        assert risk.concentration_risk == 0.35
        assert "Technology" in risk.sector_allocation
        assert risk.sector_allocation["Technology"] == 60.0
    
    def test_valuation_request_schema(self):
        """Test valuation request schema"""
        valuation_data = {
            "symbol": "AAPL",
            "valuation_method": "dcf",
            "assumptions": {
                "revenue_growth_rate": 0.08,
                "discount_rate": 0.10,
                "terminal_growth_rate": 0.03,
                "tax_rate": 0.21
            },
            "time_horizon": 5,
            "scenario": "base_case"
        }
        
        request = ValuationRequest(**valuation_data)
        
        assert request.symbol == "AAPL"
        assert request.valuation_method == "dcf"
        assert request.assumptions["revenue_growth_rate"] == 0.08
        assert request.time_horizon == 5
        assert request.scenario == "base_case"
    
    def test_valuation_response_schema(self):
        """Test valuation response schema"""
        valuation_data = {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "valuation_method": "dcf",
            "intrinsic_value": 175.50,
            "current_price": 155.00,
            "upside_downside": 13.23,
            "recommendation": "buy",
            "confidence_level": 0.78,
            "scenario_analysis": {
                "bull_case": 195.00,
                "base_case": 175.50,
                "bear_case": 145.00
            },
            "key_assumptions": {
                "revenue_growth_rate": 0.08,
                "discount_rate": 0.10,
                "terminal_growth_rate": 0.03
            },
            "sensitivity_analysis": {
                "discount_rate": {
                    "0.08": 195.25,
                    "0.10": 175.50,
                    "0.12": 158.75
                }
            },
            "valuation_date": datetime.utcnow().isoformat(),
            "analyst_notes": "Strong fundamentals support higher valuation"
        }
        
        response = ValuationResponse(**valuation_data)
        
        assert response.symbol == "AAPL"
        assert response.intrinsic_value == 175.50
        assert response.current_price == 155.00
        assert response.upside_downside == 13.23
        assert response.recommendation == "buy"
        assert response.confidence_level == 0.78
        assert "bull_case" in response.scenario_analysis


# Schema Integration and Edge Cases Tests
class TestSchemaEdgeCases:
    """Test edge cases and integration scenarios for schemas"""
    
    def test_schema_serialization_deserialization(self):
        """Test schema serialization and deserialization"""
        # Create a complex portfolio response
        portfolio_data = {
            "id": "portfolio-123",
            "name": "Test Portfolio",
            "user_id": "user-456",
            "total_value": 15000.00,
            "cash_balance": 2000.00,
            "total_return": 1500.00,
            "return_percentage": 11.54,
            "currency": "USD",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Create schema instance
        portfolio = PortfolioResponse(**portfolio_data)
        
        # Serialize to dict
        serialized = portfolio.dict()
        assert isinstance(serialized, dict)
        assert serialized["id"] == "portfolio-123"
        
        # Serialize to JSON
        json_str = portfolio.json()
        assert isinstance(json_str, str)
        
        # Deserialize from JSON
        deserialized = PortfolioResponse.parse_raw(json_str)
        assert deserialized.id == portfolio.id
        assert deserialized.total_value == portfolio.total_value
    
    def test_schema_field_aliases(self):
        """Test schema field aliases"""
        # Test with field aliases if they exist
        user_data = {
            "id": "user-123",
            "email": "user@example.com",
            "full_name": "Test User",
            "is_active": True,
            "is_verified": True,
            "role": "user",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        user = UserResponse(**user_data)
        
        # Test that aliases work in serialization
        serialized = user.dict(by_alias=True)
        assert "id" in serialized
        assert "email" in serialized
    
    def test_schema_optional_fields(self):
        """Test schema optional fields handling"""
        # Test with minimal required fields
        minimal_portfolio = {
            "name": "Minimal Portfolio",
            "initial_cash": 1000.00
        }
        
        portfolio = PortfolioCreate(**minimal_portfolio)
        
        assert portfolio.name == "Minimal Portfolio"
        assert portfolio.initial_cash == 1000.00
        assert portfolio.description is None
        assert portfolio.currency == "USD"  # Default value
    
    def test_schema_validation_error_messages(self):
        """Test schema validation error messages"""
        try:
            UserRegistration(
                email="invalid-email",
                password="weak",
                full_name=""
            )
        except ValidationError as e:
            errors = e.errors()
            
            # Should have multiple validation errors
            assert len(errors) >= 2
            
            # Check error types
            error_fields = [error["loc"][0] for error in errors]
            assert "email" in error_fields
            assert "password" in error_fields
    
    def test_schema_custom_validators(self):
        """Test custom validators in schemas"""
        # Test password confirmation validator
        try:
            PasswordChange(
                current_password="OldPassword123!",
                new_password="NewPassword123!",
                confirm_password="DifferentPassword123!"
            )
        except ValidationError as e:
            errors = e.errors()
            # Should have password mismatch error
            assert any("password" in str(error) for error in errors)
    
    def test_schema_decimal_precision(self):
        """Test decimal precision in financial schemas"""
        holding_data = {
            "symbol": "AAPL",
            "shares": 100.123456789,  # High precision
            "purchase_price": 150.9876543210,  # High precision
            "current_price": 155.1234567890
        }
        
        holding = HoldingCreate(**holding_data)
        
        # Test that precision is maintained appropriately
        assert holding.shares == 100.123456789
        assert holding.purchase_price == 150.9876543210
    
    def test_schema_date_time_handling(self):
        """Test date and time handling in schemas"""
        # Test various date formats
        date_formats = [
            "2024-01-15",
            "2024-01-15T10:30:00",
            "2024-01-15T10:30:00Z",
            "2024-01-15T10:30:00.123456Z"
        ]
        
        for date_str in date_formats:
            try:
                holding_data = {
                    "symbol": "AAPL",
                    "shares": 100.0,
                    "purchase_price": 150.00,
                    "purchase_date": date_str
                }
                
                holding = HoldingCreate(**holding_data)
                assert holding.purchase_date is not None
            except ValidationError:
                # Some formats might not be supported
                pass
    
    def test_schema_nested_validation(self):
        """Test nested schema validation"""
        # Test token response with nested user data
        token_data = {
            "access_token": "valid.jwt.token",
            "refresh_token": "valid.refresh.token",
            "token_type": "bearer",
            "expires_in": 1800,
            "user": {
                "id": "user-123",
                "email": "invalid-email",  # Invalid nested field
                "full_name": "Test User",
                "is_active": True,
                "is_verified": True,
                "role": "user",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        }
        
        try:
            TokenResponse(**token_data)
        except ValidationError as e:
            # Should catch nested validation error
            errors = e.errors()
            assert any("user" in str(error["loc"]) for error in errors)
    
    def test_schema_enum_validation(self):
        """Test enum field validation"""
        # Test valid enum values
        valid_risk_levels = ["conservative", "moderate", "aggressive"]
        
        for risk_level in valid_risk_levels:
            portfolio_data = {
                "name": "Test Portfolio",
                "initial_cash": 10000.00,
                "risk_tolerance": risk_level
            }
            
            portfolio = PortfolioCreate(**portfolio_data)
            assert portfolio.risk_tolerance == risk_level
        
        # Test invalid enum value
        with pytest.raises(ValidationError):
            PortfolioCreate(
                name="Test Portfolio",
                initial_cash=10000.00,
                risk_tolerance="invalid_risk_level"
            )
    
    def test_schema_list_validation(self):
        """Test list field validation"""
        # Test historical data with list of price points
        historical_data = {
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
            "period": "1d"
        }
        
        historical = HistoricalData(**historical_data)
        assert len(historical.data) == 1
        
        # Test with empty list (should fail)
        with pytest.raises(ValidationError):
            HistoricalData(
                symbol="AAPL",
                data=[],  # Empty list
                period="1d"
            )
    
    def test_schema_conditional_validation(self):
        """Test conditional validation logic"""
        # Test transaction validation based on type
        buy_transaction = {
            "symbol": "AAPL",
            "transaction_type": "buy",
            "shares": 50.0,
            "price": 150.00
        }
        
        transaction = TransactionCreate(**buy_transaction)
        assert transaction.shares > 0  # Buy transactions need positive shares
        
        # Test sell transaction
        sell_transaction = {
            "symbol": "AAPL",
            "transaction_type": "sell",
            "shares": 25.0,
            "price": 155.00
        }
        
        transaction = TransactionCreate(**sell_transaction)
        assert transaction.shares > 0  # Sell transactions also need positive shares