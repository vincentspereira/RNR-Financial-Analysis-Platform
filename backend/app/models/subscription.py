"""
Subscription and billing models for the RNR Financial Analysis Platform.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SubscriptionPlan(Base):
    """Available subscription plans."""
    __tablename__ = "subscription_plans"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    price_monthly: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_annually: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    features: Mapped[dict] = mapped_column(JSONB, default=list)
    limits: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    subscriptions = relationship("UserSubscription", back_populates="plan")

    def __repr__(self) -> str:
        return f"<SubscriptionPlan(name='{self.name}', price={self.price_monthly})>"


class UserSubscription(Base):
    """User's current subscription."""
    __tablename__ = "user_subscriptions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False, index=True
    )
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trial_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<UserSubscription(user_id={self.user_id}, status='{self.status}')>"


class UsageRecord(Base):
    """Usage tracking for metering."""
    __tablename__ = "usage_records"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("user_subscriptions.id", ondelete="SET NULL"), index=True
    )
    usage_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)

    def __repr__(self) -> str:
        return f"<UsageRecord(user_id={self.user_id}, type='{self.usage_type}')>"
