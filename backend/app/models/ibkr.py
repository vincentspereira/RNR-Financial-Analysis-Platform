"""
SQLAlchemy model for IBKR orders placed through this platform.

Every order submitted via /api/v1/ibkr/orders is persisted here for audit,
post-mortem analysis, and recovery after a backend restart. Status is kept in
sync with IBKR via OrderManager._sync_one().
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IBKROrder(Base):
    """
    Order submitted to Interactive Brokers via the platform.

    Status lifecycle:
      pending_submit -> submitted -> (partially_filled) -> filled
                                  -> pending_cancel -> cancelled
                                  -> rejected
    """

    __tablename__ = "ibkr_orders"
    __table_args__ = (
        Index("ix_ibkr_orders_user_status", "user_id", "status"),
        Index("ix_ibkr_orders_user_submitted_at", "user_id", "submitted_at"),
        Index("ix_ibkr_orders_ib_order_id", "ib_order_id"),
        Index("ix_ibkr_orders_client_order_id", "client_order_id"),
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Ownership
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Idempotency / external linkage
    client_order_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    ib_order_id: Mapped[Optional[int]] = mapped_column()
    ib_perm_id: Mapped[Optional[int]] = mapped_column()
    account_id: Mapped[Optional[str]] = mapped_column(String(32))

    # Contract
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    sec_type: Mapped[str] = mapped_column(String(8), nullable=False, default="STK")
    exchange: Mapped[str] = mapped_column(String(16), nullable=False, default="SMART")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")

    # Order parameters
    action: Mapped[str] = mapped_column(String(8), nullable=False)  # BUY / SELL
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    limit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 6))
    stop_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 6))
    time_in_force: Mapped[str] = mapped_column(String(8), nullable=False, default="DAY")

    # Status
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending_submit")
    filled_quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), nullable=False, default=Decimal(0)
    )
    avg_fill_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 6))
    notional_usd_at_submit: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    last_error: Mapped[Optional[str]] = mapped_column(Text)

    # Timestamps
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<IBKROrder id={self.id} user={self.user_id} "
            f"{self.action} {self.quantity} {self.symbol} "
            f"{self.order_type} status={self.status}>"
        )
