"""
Portfolio and investment tracking models
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Portfolio(Base):
    """
    User portfolio for tracking investments
    """
    __tablename__ = "portfolios"

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign key to user
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, 
        index=True
    )
    
    # Portfolio information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Portfolio status and settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Portfolio metrics (calculated fields)
    total_value: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0, nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0, nullable=False)
    total_cost_basis: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0, nullable=False)
    
    # Performance metrics
    day_change: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    day_change_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    total_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    total_return_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    
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
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, name='{self.name}', user_id={self.user_id})>"

    @property
    def holdings_count(self) -> int:
        """Get number of holdings in portfolio"""
        return len(self.holdings) if self.holdings else 0

    @property
    def invested_value(self) -> Decimal:
        """Get total invested value (excluding cash)"""
        return self.total_value - self.cash_balance


class PortfolioHolding(Base):
    """
    Individual holdings within a portfolio
    """
    __tablename__ = "portfolio_holdings"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "company_id", name="uq_portfolio_holding"),
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    portfolio_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False, 
        index=True
    )
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("companies.id"),
        nullable=False, 
        index=True
    )
    
    # Position information
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    shares: Mapped[Decimal] = mapped_column(Numeric(15, 6), nullable=False)
    average_cost: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    
    # Position dates
    first_purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Current market data (cached for performance)
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    market_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    unrealized_gain_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    unrealized_gain_loss_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))
    
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
    portfolio = relationship("Portfolio", back_populates="holdings")
    company = relationship("Company", back_populates="portfolio_holdings")

    def __repr__(self) -> str:
        return (
            f"<PortfolioHolding(portfolio_id={self.portfolio_id}, "
            f"symbol='{self.symbol}', shares={self.shares})>"
        )

    @property
    def cost_basis(self) -> Decimal:
        """Calculate total cost basis"""
        return self.shares * self.average_cost

    @property
    def current_value(self) -> Optional[Decimal]:
        """Calculate current market value"""
        if self.current_price:
            return self.shares * self.current_price
        return None


class Transaction(Base):
    """
    Investment transactions (buy, sell, dividend, etc.)
    """
    __tablename__ = "transactions"

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    portfolio_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False, 
        index=True
    )
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("companies.id"),
        nullable=False, 
        index=True
    )
    
    # Transaction details
    transaction_type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        index=True
    )  # 'buy', 'sell', 'dividend', 'split', 'spin_off'
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    
    # Transaction amounts
    shares: Mapped[Decimal] = mapped_column(Numeric(15, 6), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    
    # Fees and taxes
    commission: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    taxes: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    
    # Transaction metadata
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    settlement_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # External reference
    external_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    broker: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="transactions")
    company = relationship("Company", back_populates="transactions")

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, type='{self.transaction_type}', "
            f"symbol='{self.symbol}', shares={self.shares}, price={self.price})>"
        )

    @property
    def net_amount(self) -> Decimal:
        """Calculate net transaction amount including fees"""
        if self.transaction_type == 'buy':
            return self.total_amount + self.commission + self.fees + self.taxes
        else:  # sell or dividend
            return self.total_amount - self.commission - self.fees - self.taxes


class Watchlist(Base):
    """
    User watchlists for tracking stocks of interest
    """
    __tablename__ = "watchlists"

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign key to user
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, 
        index=True
    )
    
    # Watchlist information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Watchlist settings
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
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
    user = relationship("User", back_populates="watchlists")
    items = relationship("WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Watchlist(id={self.id}, name='{self.name}', user_id={self.user_id})>"

    @property
    def items_count(self) -> int:
        """Get number of items in watchlist"""
        return len(self.items) if self.items else 0


class WatchlistItem(Base):
    """
    Individual items within a watchlist
    """
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("watchlist_id", "company_id", name="uq_watchlist_item"),
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    watchlist_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("watchlists.id", ondelete="CASCADE"),
        nullable=False, 
        index=True
    )
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("companies.id"),
        nullable=False, 
        index=True
    )
    
    # Item metadata
    notes: Mapped[Optional[str]] = mapped_column(Text)
    target_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    alert_price_above: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    alert_price_below: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    
    # Timestamps
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    
    # Relationships
    watchlist = relationship("Watchlist", back_populates="items")
    company = relationship("Company", back_populates="watchlist_items")

    def __repr__(self) -> str:
        return (
            f"<WatchlistItem(watchlist_id={self.watchlist_id}, "
            f"company_id={self.company_id})>"
        )