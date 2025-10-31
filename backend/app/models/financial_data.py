"""
Financial data management and external API integration models
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DataSource(Base):
    """
    Configuration and metadata for external data sources
    """
    __tablename__ = "data_sources"

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Data source information
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # API configuration
    api_key_required: Mapped[bool] = mapped_column(default=True, nullable=False)
    rate_limit_per_minute: Mapped[Optional[int]] = mapped_column(Integer)
    rate_limit_per_day: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Data types provided
    provides_market_data: Mapped[bool] = mapped_column(default=False, nullable=False)
    provides_fundamental_data: Mapped[bool] = mapped_column(default=False, nullable=False)
    provides_news_data: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Status and configuration
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    priority: Mapped[int] = mapped_column(default=1, nullable=False)  # Lower number = higher priority
    configuration: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
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

    def __repr__(self) -> str:
        return f"<DataSource(name='{self.name}', provider='{self.provider}', active={self.is_active})>"


class DataUpdate(Base):
    """
    Track data update jobs and their status
    """
    __tablename__ = "data_updates"

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Update job information
    job_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        index=True
    )  # 'market_data', 'financial_statements', 'company_info'
    data_source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Job parameters
    symbols: Mapped[Optional[list]] = mapped_column(JSONB)  # List of symbols to update
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Job status
    status: Mapped[str] = mapped_column(
        String(20), 
        default="pending", 
        nullable=False, 
        index=True
    )  # 'pending', 'running', 'completed', 'failed'
    
    # Job results
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Job metadata
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    def __repr__(self) -> str:
        return (
            f"<DataUpdate(id={self.id}, type='{self.job_type}', "
            f"source='{self.data_source}', status='{self.status}')>"
        )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> Optional[float]:
        """Calculate success rate as percentage"""
        if self.records_processed > 0:
            return (self.records_updated / self.records_processed) * 100
        return None


class ExternalApiLog(Base):
    """
    Log external API calls for monitoring and debugging
    """
    __tablename__ = "external_api_logs"

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # API call information
    data_source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)  # GET, POST, etc.
    
    # Request details
    request_params: Mapped[Optional[dict]] = mapped_column(JSONB)
    request_headers: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Response details
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    response_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    is_rate_limited: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ExternalApiLog(source='{self.data_source}', "
            f"endpoint='{self.endpoint}', status={self.status_code})>"
        )

    @property
    def is_successful(self) -> bool:
        """Check if API call was successful"""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if API call had client error"""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if API call had server error"""
        return self.status_code >= 500


class ScreeningResult(Base):
    """
    Store results from market screening operations
    """
    __tablename__ = "screening_results"

    # Primary key
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Screening information
    screen_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    screen_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        index=True
    )  # 'value', 'growth', 'quality', 'momentum', 'custom'
    
    # Screen parameters
    criteria: Mapped[dict] = mapped_column(JSONB, nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    # Results
    total_companies_screened: Mapped[int] = mapped_column(Integer, nullable=False)
    companies_passed: Mapped[int] = mapped_column(Integer, nullable=False)
    results: Mapped[list] = mapped_column(JSONB, nullable=False)  # List of company IDs and scores
    
    # Performance metrics
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # User and session information
    user_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ScreeningResult(name='{self.screen_name}', "
            f"type='{self.screen_type}', passed={self.companies_passed})>"
        )

    @property
    def pass_rate(self) -> float:
        """Calculate screening pass rate as percentage"""
        if self.total_companies_screened > 0:
            return (self.companies_passed / self.total_companies_screened) * 100
        return 0.0

    @property
    def execution_time_seconds(self) -> float:
        """Get execution time in seconds"""
        return self.execution_time_ms / 1000.0