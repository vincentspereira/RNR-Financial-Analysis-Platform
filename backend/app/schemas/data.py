"""
Pydantic schemas for data ingestion endpoints
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field


class DataIngestionRequest(BaseModel):
    """Request schema for data ingestion"""
    symbol: str = Field(..., description="Stock symbol to ingest data for")
    force_update: bool = Field(False, description="Force update even if recent data exists")


class DataIngestionResponse(BaseModel):
    """Response schema for data ingestion"""
    symbol: str
    success: bool
    sources_used: List[str]
    data_ingested: Dict[str, Any]
    errors: List[str]


class BatchDataIngestionRequest(BaseModel):
    """Request schema for batch data ingestion"""
    symbols: List[str] = Field(..., description="List of stock symbols")
    force_update: bool = Field(False, description="Force update even if recent data exists")
    max_concurrent: int = Field(5, ge=1, le=10, description="Maximum concurrent ingestions")


class BatchDataIngestionResponse(BaseModel):
    """Response schema for batch data ingestion"""
    total_requested: int
    total_successful: int
    total_failed: int
    successful: List[DataIngestionResponse]
    failed: List[DataIngestionResponse]
    errors: List[str]


class CompanyDataResponse(BaseModel):
    """Response schema for company data"""
    company_id: UUID
    symbol: str
    name: str
    exchange: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    market_cap: Optional[float]
    last_updated: datetime
    data_sources: List[str]


class MarketDataResponse(BaseModel):
    """Response schema for market data"""
    symbol: str
    price_date: str
    open_price: Optional[float]
    high_price: Optional[float]
    low_price: Optional[float]
    close_price: Optional[float]
    volume: Optional[int]
    adjusted_close: Optional[float]


class FinancialStatementResponse(BaseModel):
    """Response schema for financial statements"""
    company_id: UUID
    statement_type: str
    period_type: str
    fiscal_year: int
    fiscal_quarter: Optional[int]
    report_date: str
    data: Dict[str, Any]


class DataSourceStatusResponse(BaseModel):
    """Response schema for data source status"""
    name: str
    is_active: bool
    last_successful_update: Optional[datetime]
    total_api_calls_today: int
    rate_limit_remaining: Optional[int]
    configuration: Dict[str, Any]


class DataSourcesStatusResponse(BaseModel):
    """Response schema for all data sources status"""
    sources: Dict[str, DataSourceStatusResponse]
    total_sources: int
    active_sources: int


class DataUpdateLogResponse(BaseModel):
    """Response schema for data update logs"""
    id: UUID
    data_source: str
    job_type: str
    status: str
    target_symbol: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    records_processed: Optional[int]
    error_message: Optional[str]
    metadata: Optional[Dict[str, Any]]


class ExternalApiLogResponse(BaseModel):
    """Response schema for external API logs"""
    id: UUID
    data_source: str
    endpoint: str
    request_params: Dict[str, Any]
    called_at: datetime
    completed_at: Optional[datetime]
    status_code: Optional[int]
    response_size: Optional[int]
    error_message: Optional[str]


class DataQualityReport(BaseModel):
    """Data quality report response"""
    symbol: str
    company_id: UUID
    last_updated: datetime
    data_completeness: Dict[str, float]  # Percentage completeness for each data type
    data_freshness: Dict[str, int]  # Days since last update for each data type
    data_sources: List[str]
    quality_score: float  # Overall quality score 0-100
    recommendations: List[str]


class DataIngestionStats(BaseModel):
    """Data ingestion statistics"""
    total_companies: int
    companies_updated_today: int
    companies_updated_this_week: int
    total_api_calls_today: int
    successful_ingestions_today: int
    failed_ingestions_today: int
    average_ingestion_time: float  # seconds
    data_sources_active: int
    data_sources_total: int