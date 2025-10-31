"""
Company and financial data models
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Company(Base):
    """
    Company model for publicly traded companies
    """
    __tablename__ = "companies"

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Company identifiers
    symbol: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Exchange and classification
    exchange: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    
    # Company metrics
    market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    employees: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Company information
    description: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(String(255))
    headquarters: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Additional metadata
    cik: Mapped[Optional[str]] = mapped_column(String(20), index=True)  # SEC CIK number
    cusip: Mapped[Optional[str]] = mapped_column(String(9), index=True)  # CUSIP identifier
    isin: Mapped[Optional[str]] = mapped_column(String(12), index=True)  # ISIN identifier
    
    # Status flags
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_delisted: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # Relationships
    financial_statements = relationship("FinancialStatement", back_populates="company")
    financial_ratios = relationship("FinancialRatio", back_populates="company")
    market_data = relationship("MarketData", back_populates="company")
    portfolio_holdings = relationship("PortfolioHolding", back_populates="company")
    transactions = relationship("Transaction", back_populates="company")
    watchlist_items = relationship("WatchlistItem", back_populates="company")

    def __repr__(self) -> str:
        return f"<Company(symbol='{self.symbol}', name='{self.name}', exchange='{self.exchange}')>"


class FinancialStatement(Base):
    """
    Financial statement data (income statement, balance sheet, cash flow)
    """
    __tablename__ = "financial_statements"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "statement_type", "period_type", "fiscal_year", "fiscal_quarter",
            name="uq_financial_statement_period"
        ),
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign key to company
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("companies.id"),
        nullable=False, 
        index=True
    )
    
    # Statement metadata
    statement_type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        index=True
    )  # 'income', 'balance', 'cash_flow'
    period_type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        index=True
    )  # 'quarterly', 'annual'
    
    # Period information
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fiscal_quarter: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Financial data
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)  # Statement line items
    
    # Data quality and source
    data_source: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))  # 0.00 to 1.00
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # Relationships
    company = relationship("Company", back_populates="financial_statements")

    def __repr__(self) -> str:
        return (
            f"<FinancialStatement(company_id={self.company_id}, "
            f"type='{self.statement_type}', period='{self.period_type}', "
            f"year={self.fiscal_year}, quarter={self.fiscal_quarter})>"
        )


class FinancialRatio(Base):
    """
    Calculated financial ratios and metrics
    """
    __tablename__ = "financial_ratios"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "period_type", "fiscal_year", "fiscal_quarter",
            name="uq_financial_ratio_period"
        ),
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign key to company
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("companies.id"),
        nullable=False, 
        index=True
    )
    
    # Period information
    period_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fiscal_quarter: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Liquidity ratios
    current_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    quick_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    cash_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    operating_cash_flow_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    
    # Profitability ratios
    gross_profit_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    operating_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    net_profit_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    roa: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))  # Return on Assets
    roe: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))  # Return on Equity
    roic: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))  # Return on Invested Capital
    
    # Leverage ratios
    debt_to_equity: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    debt_to_assets: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    equity_multiplier: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    interest_coverage_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    
    # Efficiency ratios
    asset_turnover: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    inventory_turnover: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    receivables_turnover: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    days_sales_outstanding: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    
    # Valuation ratios
    pe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    pb_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    ps_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    ev_ebitda: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    peg_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    
    # Growth ratios
    revenue_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    earnings_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    eps_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    book_value_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    
    # Quality scores
    piotroski_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-9
    altman_z_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    beneish_m_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    # Relationships
    company = relationship("Company", back_populates="financial_ratios")

    def __repr__(self) -> str:
        return (
            f"<FinancialRatio(company_id={self.company_id}, "
            f"period='{self.period_type}', year={self.fiscal_year}, "
            f"quarter={self.fiscal_quarter})>"
        )


class MarketData(Base):
    """
    Daily market data (OHLCV) for companies
    """
    __tablename__ = "market_data"
    __table_args__ = (
        UniqueConstraint("company_id", "price_date", name="uq_market_data_date"),
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign key to company
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("companies.id"),
        nullable=False, 
        index=True
    )
    
    # Market data
    price_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    high_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    low_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    close_price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    adjusted_close: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    # Additional market metrics
    dividend_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    split_coefficient: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    
    # Data source and quality
    data_source: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    
    # Relationships
    company = relationship("Company", back_populates="market_data")

    def __repr__(self) -> str:
        return (
            f"<MarketData(company_id={self.company_id}, "
            f"date={self.price_date}, close={self.close_price})>"
        )