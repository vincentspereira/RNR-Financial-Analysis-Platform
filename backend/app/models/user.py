"""
User models for authentication and user management
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text, func, ForeignKey
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """User model for authentication and identity."""
    __tablename__ = "users"

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Authentication fields
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile information
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Denormalized subscription tier — synced from UserSubscription by billing service
    subscription_tier: Mapped[str] = mapped_column(String(50), default="basic", nullable=False)

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
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', name='{self.first_name} {self.last_name}')>"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @full_name.setter
    def full_name(self, value: str) -> None:
        if value:
            parts = value.strip().split(' ', 1)
            self.first_name = parts[0]
            self.last_name = parts[1] if len(parts) > 1 else ""

    @property
    def is_premium(self) -> bool:
        return self.subscription_tier in ["premium", "professional", "enterprise"]

    def sync_subscription_tier(self, tier: str) -> None:
        """Update the denormalized subscription tier from the billing service."""
        self.subscription_tier = tier


class UserProfile(Base):
    """Typed user preferences — replaces the opaque JSONB blob on User."""
    __tablename__ = "user_profiles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Display preferences
    theme: Mapped[str] = mapped_column(String(20), default="dark", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    date_format: Mapped[str] = mapped_column(String(20), default="YYYY-MM-DD", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    # Notification preferences
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    price_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    report_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Dashboard preferences
    default_portfolio_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    default_watchlist_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    landing_page: Mapped[str] = mapped_column(String(50), default="dashboard", nullable=False)

    # Catch-all for future preferences without schema migration
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile(user_id={self.user_id}, theme='{self.theme}')>"

    def to_legacy_preferences(self) -> dict:
        """Export as the old-style dict for backward-compatible serialization."""
        return {
            "theme": self.theme,
            "currency": self.currency,
            "date_format": self.date_format,
            "timezone": self.timezone,
            "email_notifications": self.email_notifications,
            "push_notifications": self.push_notifications,
            "price_alerts": self.price_alerts,
            "report_notifications": self.report_notifications,
            "landing_page": self.landing_page,
            **self.extra,
        }

    @classmethod
    def from_legacy_preferences(cls, user_id: UUID, data: dict) -> "UserProfile":
        """Create from old-style preferences dict."""
        known_keys = {
            "theme", "currency", "date_format", "timezone",
            "email_notifications", "push_notifications",
            "price_alerts", "report_notifications",
            "landing_page",
        }
        extra = {k: v for k, v in data.items() if k not in known_keys}
        return cls(
            user_id=user_id,
            theme=data.get("theme", "dark"),
            currency=data.get("currency", "USD"),
            date_format=data.get("date_format", "YYYY-MM-DD"),
            timezone=data.get("timezone", "UTC"),
            email_notifications=data.get("email_notifications", True),
            push_notifications=data.get("push_notifications", True),
            price_alerts=data.get("price_alerts", True),
            report_notifications=data.get("report_notifications", True),
            landing_page=data.get("landing_page", "dashboard"),
            extra=extra,
        )


class UserSession(Base):
    """User session model for JWT token management and security."""
    __tablename__ = "user_sessions"

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign key to user
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Session information
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    # Session metadata
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refresh_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Security information
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(255))

    # Session status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    @property
    def is_refresh_expired(self) -> bool:
        if not self.refresh_expires_at:
            return True
        return datetime.utcnow() > self.refresh_expires_at

    def revoke(self) -> None:
        self.is_active = False
        self.revoked_at = datetime.utcnow()

    def update_last_used(self) -> None:
        self.last_used_at = datetime.utcnow()
