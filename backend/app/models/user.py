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
    """
    User model for authentication and profile management
    """
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
    
    # Subscription and preferences
    subscription_tier: Mapped[str] = mapped_column(String(50), default="basic", nullable=False)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
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

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', name='{self.first_name} {self.last_name}')>"

    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @full_name.setter
    def full_name(self, value: str) -> None:
        """Set user's full name by splitting into first and last name"""
        if value:
            parts = value.strip().split(' ', 1)
            self.first_name = parts[0]
            self.last_name = parts[1] if len(parts) > 1 else ""

    @property
    def is_premium(self) -> bool:
        """Check if user has premium subscription"""
        return self.subscription_tier in ["premium", "professional", "enterprise"]


class UserSession(Base):
    """
    User session model for JWT token management and security
    """
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
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at

    @property
    def is_refresh_expired(self) -> bool:
        """Check if refresh token is expired"""
        if not self.refresh_expires_at:
            return True
        return datetime.utcnow() > self.refresh_expires_at

    def revoke(self) -> None:
        """Revoke the session"""
        self.is_active = False
        self.revoked_at = datetime.utcnow()

    def update_last_used(self) -> None:
        """Update last used timestamp"""
        self.last_used_at = datetime.utcnow()