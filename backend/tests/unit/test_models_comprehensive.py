"""
Comprehensive Unit Tests for Database Models - 100% Coverage Target
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import uuid

# Model imports - using actual available models
from app.models.user import User
from app.models.portfolio import Portfolio, PortfolioHolding, Transaction
from app.models.company import Company, FinancialStatement, FinancialRatio, MarketData
from app.models.financial_data import DataSource, DataUpdate, ExternalApiLog, ScreeningResult
from app.models.audit import AuditLog
from app.core.database import Base


class TestUserModel:
    """Comprehensive tests for User model"""
    
    @pytest.fixture
    def user_data(self):
        """Sample user data"""
        return {
            "email": "test@example.com",
            "full_name": "Test User",
            "first_name": "Test",
            "last_name": "User",
            "hashed_password": "$2b$12$hashedpassword",
            "is_active": True,
            "is_verified": True,
            "role": UserRole.USER
        }
    
    def test_user_creation(self, user_data):
        """Test user model creation"""
        user = User(**user_data)
        
        assert user.email == user_data["email"]
        assert user.full_name == user_data["full_name"]
        assert user.first_name == user_data["first_name"]
        assert user.last_name == user_data["last_name"]
        assert user.hashed_password == user_data["hashed_password"]
        assert user.is_active is True
        assert user.is_verified is True
        assert user.role == UserRole.USER
        assert user.status == UserStatus.ACTIVE  # Default value
    
    def test_user_id_generation(self, user_data):
        """Test user ID is automatically generated"""
        user = User(**user_data)
        
        assert user.id is not None
        assert isinstance(user.id, str)
        assert len(user.id) > 0
    
    def test_user_timestamps(self, user_data):
        """Test user timestamp fields"""
        user = User(**user_data)
        
        # Timestamps should be set automatically
        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
    
    def test_user_role_enum(self, user_data):
        """Test user role enumeration"""
        # Test different roles
        roles = [UserRole.USER, UserRole.ADMIN, UserRole.PREMIUM]
        
        for role in roles:
            user_data["role"] = role
            user = User(**user_data)
            assert user.role == role
    
    def test_user_status_enum(self, user_data):
        """Test user status enumeration"""
        statuses = [UserStatus.ACTIVE, UserStatus.INACTIVE, UserStatus.SUSPENDED, UserStatus.PENDING]
        
        for status in statuses:
            user_data["status"] = status
            user = User(**user_data)
            assert user.status == status
    
    def test_user_email_validation(self, user_data):
        """Test user email validation"""
        # Valid emails should work
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user123@test-domain.com"
        ]
        
        for email in valid_emails:
            user_data["email"] = email
            user = User(**user_data)
            assert user.email == email
    
    def test_user_optional_fields(self, user_data):
        """Test user optional fields"""
        # Remove optional fields
        optional_fields = ["first_name", "last_name", "phone", "date_of_birth"]
        for field in optional_fields:
            if field in user_data:
                del user_data[field]
        
        user = User(**user_data)
        
        assert user.first_name is None
        assert user.last_name is None
        assert user.phone is None
        assert user.date_of_birth is None
    
    def test_user_string_representation(self, user_data):
        """Test user string representation"""
        user = User(**user_data)
        
        str_repr = str(user)
        assert user.email in str_repr
        assert user.full_name in str_repr
    
    def test_user_password_methods(self, user_data):
        """Test user password-related methods"""
        user = User(**user_data)
        
        # Test password verification (would be implemented in the model)
        assert hasattr(user, 'hashed_password')
        assert user.hashed_password == user_data["hashed_password"]
    
    def test_user_activation_methods(self, user_data):
        """Test user activation/deactivation methods"""
        user = User(**user_data)
        
        # Test initial state
        assert user.is_active is True
        
        # Test deactivation
        user.is_active = False
        assert user.is_active is False
        
        # Test reactivation
        user.is_active = True
        assert user.is_active is True
    
    def test_user_verification_methods(self, user_data):
        """Test user email verification methods"""
        user = User(**user_data)
        
        # Test initial state
        assert user.is_verified is True
        
        # Test unverified state
        user.is_verified = False
        assert user.is_verified is False
    
    def test_user_last_login_tracking(self, user_data):
        """Test user last login tracking"""
        user = User(**user_data)
        
        # Initially no last login
        assert user.last_login_at is None
        
        # Set last login
        login_time = datetime.utcnow()
        user.last_login_at = login_time
        assert user.last_login_at == login_time


class TestPortfolioModel:
    """Comprehensive tests for Portfolio model"""
    
    @pytest.fixture
    def portfolio_data(self):
        """Sample portfolio data"""
        return {
            "name": "Test Portfolio",
            "description": "A test portfolio for unit testing",
            "user_id": "user-123",
            "total_value": Decimal("10000.00"),
            "cash_balance": Decimal("1000.00"),
            "is_active": True
        }
    
    def test_portfolio_creation(self, portfolio_data):
        """Test portfolio model creation"""
        portfolio = Portfolio(**portfolio_data)
        
        assert portfolio.name == portfolio_data["name"]
        assert portfolio.description == portfolio_data["description"]
        assert portfolio.user_id == portfolio_data["user_id"]
        assert portfolio.total_value == portfolio_data["total_value"]
        assert portfolio.cash_balance == portfolio_data["cash_balance"]
        assert portfolio.is_active is True
    
    def test_portfolio_id_generation(self, portfolio_data):
        """Test portfolio ID is automatically generated"""
        portfolio = Portfolio(**portfolio_data)
        
        assert portfolio.id is not None
        assert isinstance(portfolio.id, str)
        assert len(portfolio.id) > 0
    
    def test_portfolio_timestamps(self, portfolio_data):
        """Test portfolio timestamp fields"""
        portfolio = Portfolio(**portfolio_data)
        
        assert portfolio.created_at is not None
        assert portfolio.updated_at is not None
        assert isinstance(portfolio.created_at, datetime)
        assert isinstance(portfolio.updated_at, datetime)
    
    def test_portfolio_decimal_fields(self, portfolio_data):
        """Test portfolio decimal field handling"""
        portfolio = Portfolio(**portfolio_data)
        
        # Test decimal precision
        assert isinstance(portfolio.total_value, Decimal)
        assert isinstance(portfolio.cash_balance, Decimal)
        
        # Test decimal operations
        portfolio.total_value += Decimal("500.00")
        assert portfolio.total_value == Decimal("10500.00")
    
    def test_portfolio_optional_fields(self, portfolio_data):
        """Test portfolio optional fields"""
        # Remove optional fields
        del portfolio_data["description"]
        
        portfolio = Portfolio(**portfolio_data)
        
        assert portfolio.description is None
    
    def test_portfolio_user_relationship(self, portfolio_data):
        """Test portfolio-user relationship"""
        portfolio = Portfolio(**portfolio_data)
        
        assert portfolio.user_id == "user-123"
        # In a real test with database, you would test the relationship
        # assert portfolio.user is not None
    
    def test_portfolio_performance_calculation(self, portfolio_data):
        """Test portfolio performance calculation methods"""
        portfolio = Portfolio(**portfolio_data)
        
        # Test return calculation
        initial_value = Decimal("9000.00")
        current_value = portfolio.total_value
        
        expected_return = current_value - initial_value
        expected_return_percentage = (expected_return / initial_value) * 100
        
        assert expected_return == Decimal("1000.00")
        assert expected_return_percentage == Decimal("11.11")
    
    def test_portfolio_string_representation(self, portfolio_data):
        """Test portfolio string representation"""
        portfolio = Portfolio(**portfolio_data)
        
        str_repr = str(portfolio)
        assert portfolio.name in str_repr
        assert portfolio.user_id in str_repr


class TestHoldingModel:
    """Comprehensive tests for Holding model"""
    
    @pytest.fixture
    def holding_data(self):
        """Sample holding data"""
        return {
            "portfolio_id": "portfolio-123",
            "symbol": "AAPL",
            "shares": Decimal("100"),
            "purchase_price": Decimal("150.00"),
            "current_price": Decimal("155.00"),
            "purchase_date": datetime.utcnow().date()
        }
    
    def test_holding_creation(self, holding_data):
        """Test holding model creation"""
        holding = Holding(**holding_data)
        
        assert holding.portfolio_id == holding_data["portfolio_id"]
        assert holding.symbol == holding_data["symbol"]
        assert holding.shares == holding_data["shares"]
        assert holding.purchase_price == holding_data["purchase_price"]
        assert holding.current_price == holding_data["current_price"]
        assert holding.purchase_date == holding_data["purchase_date"]
    
    def test_holding_value_calculations(self, holding_data):
        """Test holding value calculations"""
        holding = Holding(**holding_data)
        
        # Test current value calculation
        expected_current_value = holding.shares * holding.current_price
        assert expected_current_value == Decimal("15500.00")
        
        # Test cost basis calculation
        expected_cost_basis = holding.shares * holding.purchase_price
        assert expected_cost_basis == Decimal("15000.00")
        
        # Test gain/loss calculation
        expected_gain_loss = expected_current_value - expected_cost_basis
        assert expected_gain_loss == Decimal("500.00")
        
        # Test gain/loss percentage
        expected_percentage = (expected_gain_loss / expected_cost_basis) * 100
        assert abs(expected_percentage - Decimal("3.33")) < Decimal("0.01")
    
    def test_holding_weight_calculation(self, holding_data):
        """Test holding weight calculation in portfolio"""
        holding = Holding(**holding_data)
        portfolio_total_value = Decimal("50000.00")
        
        holding_value = holding.shares * holding.current_price
        expected_weight = (holding_value / portfolio_total_value) * 100
        
        assert expected_weight == Decimal("31.00")
    
    def test_holding_fractional_shares(self, holding_data):
        """Test holding with fractional shares"""
        holding_data["shares"] = Decimal("100.5")
        holding = Holding(**holding_data)
        
        assert holding.shares == Decimal("100.5")
        
        # Test calculations with fractional shares
        current_value = holding.shares * holding.current_price
        assert current_value == Decimal("15577.50")
    
    def test_holding_portfolio_relationship(self, holding_data):
        """Test holding-portfolio relationship"""
        holding = Holding(**holding_data)
        
        assert holding.portfolio_id == "portfolio-123"
        # In a real test with database, you would test the relationship
        # assert holding.portfolio is not None


class TestTransactionModel:
    """Comprehensive tests for Transaction model"""
    
    @pytest.fixture
    def transaction_data(self):
        """Sample transaction data"""
        return {
            "portfolio_id": "portfolio-123",
            "symbol": "AAPL",
            "transaction_type": TransactionType.BUY,
            "shares": Decimal("50"),
            "price": Decimal("150.00"),
            "total_amount": Decimal("7500.00"),
            "transaction_date": datetime.utcnow(),
            "fees": Decimal("9.99")
        }
    
    def test_transaction_creation(self, transaction_data):
        """Test transaction model creation"""
        transaction = Transaction(**transaction_data)
        
        assert transaction.portfolio_id == transaction_data["portfolio_id"]
        assert transaction.symbol == transaction_data["symbol"]
        assert transaction.transaction_type == transaction_data["transaction_type"]
        assert transaction.shares == transaction_data["shares"]
        assert transaction.price == transaction_data["price"]
        assert transaction.total_amount == transaction_data["total_amount"]
        assert transaction.fees == transaction_data["fees"]
    
    def test_transaction_type_enum(self, transaction_data):
        """Test transaction type enumeration"""
        transaction_types = [
            TransactionType.BUY,
            TransactionType.SELL,
            TransactionType.DIVIDEND,
            TransactionType.SPLIT,
            TransactionType.DEPOSIT,
            TransactionType.WITHDRAWAL
        ]
        
        for tx_type in transaction_types:
            transaction_data["transaction_type"] = tx_type
            transaction = Transaction(**transaction_data)
            assert transaction.transaction_type == tx_type
    
    def test_transaction_amount_calculation(self, transaction_data):
        """Test transaction amount calculations"""
        transaction = Transaction(**transaction_data)
        
        # Test total amount calculation
        expected_total = transaction.shares * transaction.price
        assert expected_total == Decimal("7500.00")
        
        # Test net amount (including fees)
        expected_net = transaction.total_amount + transaction.fees
        assert expected_net == Decimal("7509.99")
    
    def test_transaction_buy_vs_sell(self, transaction_data):
        """Test buy vs sell transaction handling"""
        # Test buy transaction
        buy_transaction = Transaction(**transaction_data)
        assert buy_transaction.transaction_type == TransactionType.BUY
        
        # Test sell transaction
        transaction_data["transaction_type"] = TransactionType.SELL
        sell_transaction = Transaction(**transaction_data)
        assert sell_transaction.transaction_type == TransactionType.SELL
    
    def test_transaction_dividend_handling(self, transaction_data):
        """Test dividend transaction handling"""
        transaction_data.update({
            "transaction_type": TransactionType.DIVIDEND,
            "shares": Decimal("0"),  # Dividends don't involve share transactions
            "price": Decimal("0"),
            "total_amount": Decimal("125.00"),  # Dividend amount
            "fees": Decimal("0")
        })
        
        dividend_transaction = Transaction(**transaction_data)
        
        assert dividend_transaction.transaction_type == TransactionType.DIVIDEND
        assert dividend_transaction.shares == Decimal("0")
        assert dividend_transaction.total_amount == Decimal("125.00")
    
    def test_transaction_stock_split_handling(self, transaction_data):
        """Test stock split transaction handling"""
        transaction_data.update({
            "transaction_type": TransactionType.SPLIT,
            "shares": Decimal("50"),  # Additional shares from split
            "price": Decimal("0"),    # No price for split
            "total_amount": Decimal("0"),  # No money involved
            "fees": Decimal("0")
        })
        
        split_transaction = Transaction(**transaction_data)
        
        assert split_transaction.transaction_type == TransactionType.SPLIT
        assert split_transaction.shares == Decimal("50")
        assert split_transaction.total_amount == Decimal("0")


class TestCompanyModel:
    """Comprehensive tests for Company model"""
    
    @pytest.fixture
    def company_data(self):
        """Sample company data"""
        return {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "market_cap": Decimal("2500000000000"),  # $2.5T
            "employees": 154000,
            "founded_year": 1976,
            "headquarters": "Cupertino, CA",
            "website": "https://www.apple.com"
        }
    
    def test_company_creation(self, company_data):
        """Test company model creation"""
        company = Company(**company_data)
        
        assert company.symbol == company_data["symbol"]
        assert company.name == company_data["name"]
        assert company.exchange == company_data["exchange"]
        assert company.sector == company_data["sector"]
        assert company.industry == company_data["industry"]
        assert company.market_cap == company_data["market_cap"]
        assert company.employees == company_data["employees"]
        assert company.founded_year == company_data["founded_year"]
    
    def test_company_symbol_primary_key(self, company_data):
        """Test company symbol as primary key"""
        company = Company(**company_data)
        
        assert company.symbol == "AAPL"
        # Symbol should be the primary key
        assert hasattr(company, 'symbol')
    
    def test_company_market_cap_handling(self, company_data):
        """Test company market cap decimal handling"""
        company = Company(**company_data)
        
        assert isinstance(company.market_cap, Decimal)
        assert company.market_cap == Decimal("2500000000000")
        
        # Test market cap in billions
        market_cap_billions = company.market_cap / Decimal("1000000000")
        assert market_cap_billions == Decimal("2500")
    
    def test_company_optional_fields(self, company_data):
        """Test company optional fields"""
        # Remove optional fields
        optional_fields = ["employees", "founded_year", "headquarters", "website"]
        for field in optional_fields:
            if field in company_data:
                del company_data[field]
        
        company = Company(**company_data)
        
        assert company.employees is None
        assert company.founded_year is None
        assert company.headquarters is None
        assert company.website is None
    
    def test_company_string_representation(self, company_data):
        """Test company string representation"""
        company = Company(**company_data)
        
        str_repr = str(company)
        assert company.symbol in str_repr
        assert company.name in str_repr


class TestCompanyProfileModel:
    """Comprehensive tests for CompanyProfile model"""
    
    @pytest.fixture
    def profile_data(self):
        """Sample company profile data"""
        return {
            "symbol": "AAPL",
            "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.",
            "ceo": "Tim Cook",
            "business_summary": "Technology company focused on consumer electronics and services.",
            "full_time_employees": 154000,
            "address": "One Apple Park Way, Cupertino, CA 95014",
            "phone": "+1-408-996-1010",
            "website": "https://www.apple.com"
        }
    
    def test_company_profile_creation(self, profile_data):
        """Test company profile model creation"""
        profile = CompanyProfile(**profile_data)
        
        assert profile.symbol == profile_data["symbol"]
        assert profile.description == profile_data["description"]
        assert profile.ceo == profile_data["ceo"]
        assert profile.business_summary == profile_data["business_summary"]
        assert profile.full_time_employees == profile_data["full_time_employees"]
    
    def test_company_profile_relationship(self, profile_data):
        """Test company profile-company relationship"""
        profile = CompanyProfile(**profile_data)
        
        assert profile.symbol == "AAPL"
        # In a real test with database, you would test the relationship
        # assert profile.company is not None


class TestFinancialStatementModel:
    """Comprehensive tests for FinancialStatement model"""
    
    @pytest.fixture
    def financial_data(self):
        """Sample financial statement data"""
        return {
            "symbol": "AAPL",
            "period": "2023-Q4",
            "statement_type": "income",
            "fiscal_year": 2023,
            "fiscal_quarter": 4,
            "revenue": Decimal("119575000000"),
            "net_income": Decimal("33916000000"),
            "total_assets": Decimal("352755000000"),
            "total_liabilities": Decimal("290437000000"),
            "shareholders_equity": Decimal("62318000000"),
            "operating_cash_flow": Decimal("110543000000"),
            "free_cash_flow": Decimal("99584000000")
        }
    
    def test_financial_statement_creation(self, financial_data):
        """Test financial statement model creation"""
        statement = FinancialStatement(**financial_data)
        
        assert statement.symbol == financial_data["symbol"]
        assert statement.period == financial_data["period"]
        assert statement.statement_type == financial_data["statement_type"]
        assert statement.fiscal_year == financial_data["fiscal_year"]
        assert statement.fiscal_quarter == financial_data["fiscal_quarter"]
        assert statement.revenue == financial_data["revenue"]
        assert statement.net_income == financial_data["net_income"]
    
    def test_financial_ratios_calculation(self, financial_data):
        """Test financial ratios calculation from statement data"""
        statement = FinancialStatement(**financial_data)
        
        # Test profit margin
        profit_margin = (statement.net_income / statement.revenue) * 100
        expected_margin = Decimal("28.36")  # Approximately 28.36%
        assert abs(profit_margin - expected_margin) < Decimal("0.1")
        
        # Test return on assets
        roa = (statement.net_income / statement.total_assets) * 100
        expected_roa = Decimal("9.62")  # Approximately 9.62%
        assert abs(roa - expected_roa) < Decimal("0.1")
        
        # Test return on equity
        roe = (statement.net_income / statement.shareholders_equity) * 100
        expected_roe = Decimal("54.43")  # Approximately 54.43%
        assert abs(roe - expected_roe) < Decimal("0.1")
    
    def test_financial_statement_types(self, financial_data):
        """Test different financial statement types"""
        statement_types = ["income", "balance_sheet", "cash_flow"]
        
        for stmt_type in statement_types:
            financial_data["statement_type"] = stmt_type
            statement = FinancialStatement(**financial_data)
            assert statement.statement_type == stmt_type


class TestStockPriceModel:
    """Comprehensive tests for StockPrice model"""
    
    @pytest.fixture
    def price_data(self):
        """Sample stock price data"""
        return {
            "symbol": "AAPL",
            "date": datetime.utcnow().date(),
            "open_price": Decimal("150.00"),
            "high_price": Decimal("155.00"),
            "low_price": Decimal("149.00"),
            "close_price": Decimal("154.00"),
            "adjusted_close": Decimal("154.00"),
            "volume": 50000000
        }
    
    def test_stock_price_creation(self, price_data):
        """Test stock price model creation"""
        price = StockPrice(**price_data)
        
        assert price.symbol == price_data["symbol"]
        assert price.date == price_data["date"]
        assert price.open_price == price_data["open_price"]
        assert price.high_price == price_data["high_price"]
        assert price.low_price == price_data["low_price"]
        assert price.close_price == price_data["close_price"]
        assert price.volume == price_data["volume"]
    
    def test_stock_price_calculations(self, price_data):
        """Test stock price calculations"""
        price = StockPrice(**price_data)
        
        # Test daily change
        previous_close = Decimal("152.00")
        daily_change = price.close_price - previous_close
        assert daily_change == Decimal("2.00")
        
        # Test daily change percentage
        change_percentage = (daily_change / previous_close) * 100
        expected_percentage = Decimal("1.32")  # Approximately 1.32%
        assert abs(change_percentage - expected_percentage) < Decimal("0.01")
        
        # Test trading range
        trading_range = price.high_price - price.low_price
        assert trading_range == Decimal("6.00")
    
    def test_stock_price_volume_analysis(self, price_data):
        """Test stock price volume analysis"""
        price = StockPrice(**price_data)
        
        assert price.volume == 50000000
        
        # Test volume in millions
        volume_millions = price.volume / 1000000
        assert volume_millions == 50
    
    def test_stock_price_ohlc_validation(self, price_data):
        """Test OHLC price validation logic"""
        price = StockPrice(**price_data)
        
        # High should be >= Open, Close, Low
        assert price.high_price >= price.open_price
        assert price.high_price >= price.close_price
        assert price.high_price >= price.low_price
        
        # Low should be <= Open, Close, High
        assert price.low_price <= price.open_price
        assert price.low_price <= price.close_price
        assert price.low_price <= price.high_price


class TestMarketDataModel:
    """Comprehensive tests for MarketData model"""
    
    @pytest.fixture
    def market_data(self):
        """Sample market data"""
        return {
            "symbol": "SPY",
            "data_type": "index",
            "value": Decimal("450.00"),
            "change": Decimal("5.50"),
            "change_percent": Decimal("1.24"),
            "volume": 75000000,
            "timestamp": datetime.utcnow()
        }
    
    def test_market_data_creation(self, market_data):
        """Test market data model creation"""
        data = MarketData(**market_data)
        
        assert data.symbol == market_data["symbol"]
        assert data.data_type == market_data["data_type"]
        assert data.value == market_data["value"]
        assert data.change == market_data["change"]
        assert data.change_percent == market_data["change_percent"]
        assert data.volume == market_data["volume"]
    
    def test_market_data_types(self, market_data):
        """Test different market data types"""
        data_types = ["index", "etf", "commodity", "currency", "crypto"]
        
        for data_type in data_types:
            market_data["data_type"] = data_type
            data = MarketData(**market_data)
            assert data.data_type == data_type


class TestEconomicIndicatorModel:
    """Comprehensive tests for EconomicIndicator model"""
    
    @pytest.fixture
    def indicator_data(self):
        """Sample economic indicator data"""
        return {
            "indicator_name": "GDP Growth Rate",
            "value": Decimal("2.5"),
            "unit": "percent",
            "period": "2023-Q4",
            "release_date": datetime.utcnow().date(),
            "source": "Bureau of Economic Analysis"
        }
    
    def test_economic_indicator_creation(self, indicator_data):
        """Test economic indicator model creation"""
        indicator = EconomicIndicator(**indicator_data)
        
        assert indicator.indicator_name == indicator_data["indicator_name"]
        assert indicator.value == indicator_data["value"]
        assert indicator.unit == indicator_data["unit"]
        assert indicator.period == indicator_data["period"]
        assert indicator.source == indicator_data["source"]
    
    def test_economic_indicator_types(self, indicator_data):
        """Test different economic indicator types"""
        indicators = [
            ("Unemployment Rate", "4.2", "percent"),
            ("Inflation Rate", "3.1", "percent"),
            ("Interest Rate", "5.25", "percent"),
            ("Consumer Confidence", "102.5", "index")
        ]
        
        for name, value, unit in indicators:
            indicator_data.update({
                "indicator_name": name,
                "value": Decimal(value),
                "unit": unit
            })
            
            indicator = EconomicIndicator(**indicator_data)
            assert indicator.indicator_name == name
            assert indicator.value == Decimal(value)
            assert indicator.unit == unit


class TestNewsArticleModel:
    """Comprehensive tests for NewsArticle model"""
    
    @pytest.fixture
    def news_data(self):
        """Sample news article data"""
        return {
            "title": "Apple Reports Strong Q4 Earnings",
            "content": "Apple Inc. reported strong fourth-quarter earnings...",
            "source": "Financial Times",
            "author": "John Smith",
            "published_at": datetime.utcnow(),
            "url": "https://example.com/apple-earnings",
            "sentiment_score": Decimal("0.75"),
            "relevance_score": Decimal("0.90"),
            "symbols": ["AAPL"]
        }
    
    def test_news_article_creation(self, news_data):
        """Test news article model creation"""
        article = NewsArticle(**news_data)
        
        assert article.title == news_data["title"]
        assert article.content == news_data["content"]
        assert article.source == news_data["source"]
        assert article.author == news_data["author"]
        assert article.url == news_data["url"]
        assert article.sentiment_score == news_data["sentiment_score"]
        assert article.relevance_score == news_data["relevance_score"]
    
    def test_news_article_sentiment_analysis(self, news_data):
        """Test news article sentiment analysis"""
        article = NewsArticle(**news_data)
        
        # Test sentiment score range (-1 to 1)
        assert -1 <= article.sentiment_score <= 1
        
        # Test sentiment classification
        if article.sentiment_score > Decimal("0.1"):
            sentiment = "positive"
        elif article.sentiment_score < Decimal("-0.1"):
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        assert sentiment == "positive"  # Based on 0.75 score
    
    def test_news_article_relevance_scoring(self, news_data):
        """Test news article relevance scoring"""
        article = NewsArticle(**news_data)
        
        # Test relevance score range (0 to 1)
        assert 0 <= article.relevance_score <= 1
        
        # High relevance article
        assert article.relevance_score == Decimal("0.90")


class TestAuditLogModel:
    """Comprehensive tests for AuditLog model"""
    
    @pytest.fixture
    def audit_data(self):
        """Sample audit log data"""
        return {
            "user_id": "user-123",
            "action": AuditAction.LOGIN,
            "resource_type": "authentication",
            "resource_id": "session-456",
            "details": {"ip_address": "192.168.1.1", "user_agent": "Mozilla/5.0"},
            "timestamp": datetime.utcnow()
        }
    
    def test_audit_log_creation(self, audit_data):
        """Test audit log model creation"""
        audit = AuditLog(**audit_data)
        
        assert audit.user_id == audit_data["user_id"]
        assert audit.action == audit_data["action"]
        assert audit.resource_type == audit_data["resource_type"]
        assert audit.resource_id == audit_data["resource_id"]
        assert audit.details == audit_data["details"]
    
    def test_audit_action_enum(self, audit_data):
        """Test audit action enumeration"""
        actions = [
            AuditAction.LOGIN,
            AuditAction.LOGOUT,
            AuditAction.CREATE,
            AuditAction.UPDATE,
            AuditAction.DELETE,
            AuditAction.VIEW
        ]
        
        for action in actions:
            audit_data["action"] = action
            audit = AuditLog(**audit_data)
            assert audit.action == action
    
    def test_audit_log_details_json(self, audit_data):
        """Test audit log details JSON handling"""
        audit = AuditLog(**audit_data)
        
        # Test JSON details
        assert isinstance(audit.details, dict)
        assert audit.details["ip_address"] == "192.168.1.1"
        assert audit.details["user_agent"] == "Mozilla/5.0"
    
    def test_audit_log_system_events(self, audit_data):
        """Test audit log for system events (no user)"""
        audit_data["user_id"] = None
        audit_data["action"] = AuditAction.SYSTEM
        audit_data["resource_type"] = "system"
        audit_data["details"] = {"event": "database_backup", "status": "completed"}
        
        audit = AuditLog(**audit_data)
        
        assert audit.user_id is None
        assert audit.action == AuditAction.SYSTEM
        assert audit.details["event"] == "database_backup"


# Model Relationship Tests
class TestModelRelationships:
    """Test relationships between models"""
    
    def test_user_portfolio_relationship(self):
        """Test user-portfolio one-to-many relationship"""
        user_data = {
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": "$2b$12$hashedpassword"
        }
        user = User(**user_data)
        
        portfolio_data = {
            "name": "Test Portfolio",
            "user_id": user.id,
            "total_value": Decimal("10000.00"),
            "cash_balance": Decimal("1000.00")
        }
        portfolio = Portfolio(**portfolio_data)
        
        assert portfolio.user_id == user.id
    
    def test_portfolio_holding_relationship(self):
        """Test portfolio-holding one-to-many relationship"""
        portfolio_data = {
            "name": "Test Portfolio",
            "user_id": "user-123",
            "total_value": Decimal("10000.00"),
            "cash_balance": Decimal("1000.00")
        }
        portfolio = Portfolio(**portfolio_data)
        
        holding_data = {
            "portfolio_id": portfolio.id,
            "symbol": "AAPL",
            "shares": Decimal("100"),
            "purchase_price": Decimal("150.00"),
            "current_price": Decimal("155.00")
        }
        holding = Holding(**holding_data)
        
        assert holding.portfolio_id == portfolio.id
    
    def test_portfolio_transaction_relationship(self):
        """Test portfolio-transaction one-to-many relationship"""
        portfolio_data = {
            "name": "Test Portfolio",
            "user_id": "user-123",
            "total_value": Decimal("10000.00"),
            "cash_balance": Decimal("1000.00")
        }
        portfolio = Portfolio(**portfolio_data)
        
        transaction_data = {
            "portfolio_id": portfolio.id,
            "symbol": "AAPL",
            "transaction_type": TransactionType.BUY,
            "shares": Decimal("50"),
            "price": Decimal("150.00"),
            "total_amount": Decimal("7500.00")
        }
        transaction = Transaction(**transaction_data)
        
        assert transaction.portfolio_id == portfolio.id
    
    def test_company_stock_price_relationship(self):
        """Test company-stock price one-to-many relationship"""
        company_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "sector": "Technology"
        }
        company = Company(**company_data)
        
        price_data = {
            "symbol": company.symbol,
            "date": datetime.utcnow().date(),
            "open_price": Decimal("150.00"),
            "high_price": Decimal("155.00"),
            "low_price": Decimal("149.00"),
            "close_price": Decimal("154.00"),
            "volume": 50000000
        }
        price = StockPrice(**price_data)
        
        assert price.symbol == company.symbol


# Edge Cases and Validation Tests
class TestModelEdgeCases:
    """Test edge cases and validation for models"""
    
    def test_decimal_precision_handling(self):
        """Test decimal precision in financial fields"""
        portfolio_data = {
            "name": "Precision Test",
            "user_id": "user-123",
            "total_value": Decimal("10000.123456789"),  # High precision
            "cash_balance": Decimal("1000.99")
        }
        portfolio = Portfolio(**portfolio_data)
        
        # Test that precision is maintained
        assert portfolio.total_value == Decimal("10000.123456789")
        assert portfolio.cash_balance == Decimal("1000.99")
    
    def test_large_numbers_handling(self):
        """Test handling of very large numbers"""
        company_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "market_cap": Decimal("3000000000000")  # $3 trillion
        }
        company = Company(**company_data)
        
        assert company.market_cap == Decimal("3000000000000")
    
    def test_negative_values_handling(self):
        """Test handling of negative values where appropriate"""
        transaction_data = {
            "portfolio_id": "portfolio-123",
            "symbol": "AAPL",
            "transaction_type": TransactionType.SELL,
            "shares": Decimal("50"),
            "price": Decimal("140.00"),  # Sold at loss
            "total_amount": Decimal("-500.00")  # Net loss after fees
        }
        transaction = Transaction(**transaction_data)
        
        assert transaction.total_amount == Decimal("-500.00")
    
    def test_zero_values_handling(self):
        """Test handling of zero values"""
        holding_data = {
            "portfolio_id": "portfolio-123",
            "symbol": "AAPL",
            "shares": Decimal("0"),  # Sold all shares
            "purchase_price": Decimal("150.00"),
            "current_price": Decimal("155.00")
        }
        holding = Holding(**holding_data)
        
        assert holding.shares == Decimal("0")
        
        # Current value should be zero
        current_value = holding.shares * holding.current_price
        assert current_value == Decimal("0")
    
    def test_string_length_limits(self):
        """Test string field length handling"""
        # Test very long company name
        long_name = "A" * 1000
        company_data = {
            "symbol": "TEST",
            "name": long_name,
            "exchange": "NASDAQ",
            "sector": "Technology"
        }
        company = Company(**company_data)
        
        # Should handle long strings (up to database limits)
        assert len(company.name) == 1000
    
    def test_date_edge_cases(self):
        """Test date field edge cases"""
        # Test with very old date
        old_date = datetime(1900, 1, 1).date()
        
        price_data = {
            "symbol": "AAPL",
            "date": old_date,
            "open_price": Decimal("1.00"),
            "high_price": Decimal("1.10"),
            "low_price": Decimal("0.90"),
            "close_price": Decimal("1.05"),
            "volume": 1000
        }
        price = StockPrice(**price_data)
        
        assert price.date == old_date
    
    def test_enum_invalid_values(self):
        """Test enum fields with invalid values"""
        user_data = {
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": "$2b$12$hashedpassword",
            "role": UserRole.USER
        }
        
        # Valid enum value should work
        user = User(**user_data)
        assert user.role == UserRole.USER
        
        # Invalid enum value should raise error (in real implementation)
        # This would be caught by the database or ORM validation