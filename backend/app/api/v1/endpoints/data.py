"""
Data ingestion API endpoints
"""
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.logging import get_logger
from app.schemas.auth import ErrorResponse
from app.schemas.data import (
    BatchDataIngestionRequest,
    BatchDataIngestionResponse,
    CompanyDataResponse,
    DataIngestionRequest,
    DataIngestionResponse,
    DataIngestionStats,
    DataQualityReport,
    DataSourcesStatusResponse,
    DataUpdateLogResponse,
    ExternalApiLogResponse,
    FinancialStatementResponse,
    MarketDataResponse,
)
from app.services.auth.auth_service import auth_service
from app.services.data.data_ingestion_service import data_ingestion_service

router = APIRouter(prefix="/data", tags=["Data Ingestion"])
logger = get_logger("data.api")


async def get_current_user_from_token(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """Get current user from authorization token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    access_token = authorization.split(" ")[1]
    user = await auth_service.verify_session(access_token, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return user


@router.post(
    "/ingest/company",
    response_model=DataIngestionResponse,
    summary="Ingest company data",
    description="Ingest comprehensive financial data for a single company from external APIs",
    responses={
        200: {"description": "Data ingestion completed"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def ingest_company_data(
    request: DataIngestionRequest,
    current_user = Depends(get_current_user_from_token),
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """
    Ingest comprehensive financial data for a single company
    
    - **symbol**: Stock symbol (e.g., 'AAPL', 'MSFT')
    - **force_update**: Force update even if recent data exists
    
    This endpoint will:
    - Fetch company overview and profile data
    - Retrieve financial statements (income, balance sheet, cash flow)
    - Get historical market data and current prices
    - Update company information in the database
    - Log all API calls and data updates for audit purposes
    
    Data sources used:
    - Alpha Vantage (fundamental data, financial statements)
    - Yahoo Finance (market data, company info)
    """
    try:
        if not request.symbol or len(request.symbol.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Symbol is required"
            )
        
        symbol = request.symbol.strip().upper()
        
        result = await data_ingestion_service.ingest_company_data(
            symbol=symbol,
            db=db,
            user_id=current_user.id,
            force_update=request.force_update
        )
        
        return DataIngestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data ingestion failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Data processing failed. Please try again later."
        )


@router.post(
    "/ingest/batch",
    response_model=BatchDataIngestionResponse,
    summary="Batch ingest company data",
    description="Ingest financial data for multiple companies in batch",
    responses={
        200: {"description": "Batch ingestion completed"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def batch_ingest_company_data(
    request: BatchDataIngestionRequest,
    current_user = Depends(get_current_user_from_token),
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """
    Ingest financial data for multiple companies in batch
    
    - **symbols**: List of stock symbols (max 50 per request)
    - **force_update**: Force update even if recent data exists
    - **max_concurrent**: Maximum concurrent ingestions (1-10)
    
    This endpoint processes multiple companies concurrently while respecting
    API rate limits. Results include both successful and failed ingestions.
    """
    try:
        if not request.symbols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one symbol is required"
            )
        
        if len(request.symbols) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 50 symbols allowed per batch request"
            )
        
        # Clean and validate symbols
        symbols = [s.strip().upper() for s in request.symbols if s.strip()]
        if not symbols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid symbols provided"
            )
        
        result = await data_ingestion_service.batch_ingest_companies(
            symbols=symbols,
            db=db,
            user_id=current_user.id,
            max_concurrent=request.max_concurrent
        )
        
        return BatchDataIngestionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch ingestion failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch processing failed. Please try again later."
        )


@router.get(
    "/sources/status",
    response_model=DataSourcesStatusResponse,
    summary="Get data sources status",
    description="Get status and health information for all external data sources",
    responses={
        200: {"description": "Data sources status retrieved"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_data_sources_status(
    current_user = Depends(get_current_user_from_token),
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """
    Get status and health information for all external data sources
    
    Returns information about:
    - API rate limits and usage
    - Last successful updates
    - Configuration status
    - Active/inactive sources
    """
    try:
        status = await data_ingestion_service.get_data_source_status(db)
        
        sources = {}
        active_count = 0
        
        for name, source_status in status.items():
            sources[name] = source_status
            if source_status.get('is_active'):
                active_count += 1
        
        return DataSourcesStatusResponse(
            sources=sources,
            total_sources=len(sources),
            active_sources=active_count
        )
        
    except Exception as e:
        logger.error(f"Failed to get data sources status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve data sources status. Please try again later."
        )


@router.get(
    "/company/{symbol}/latest",
    response_model=CompanyDataResponse,
    summary="Get latest company data",
    description="Get the most recent company data from the database",
    responses={
        200: {"description": "Company data retrieved"},
        404: {"model": ErrorResponse, "description": "Company not found"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_latest_company_data(
    symbol: str,
    current_user = Depends(get_current_user_from_token),
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """
    Get the most recent company data from the database
    
    - **symbol**: Stock symbol
    
    Returns the latest company information including:
    - Basic company details
    - Last update timestamp
    - Available data sources
    """
    try:
        from sqlalchemy import select
        from app.models.company import Company
        
        symbol = symbol.strip().upper()
        
        # Get company data
        stmt = select(Company).where(Company.symbol == symbol)
        result = await db.execute(stmt)
        company = result.scalar_one_or_none()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with symbol {symbol} not found"
            )
        
        # Determine available data sources (simplified)
        data_sources = []
        if company.updated_at:
            data_sources.append("database")
        
        return CompanyDataResponse(
            company_id=company.id,
            symbol=company.symbol,
            name=company.name,
            exchange=company.exchange,
            sector=company.sector,
            industry=company.industry,
            market_cap=None,  # Would need to calculate from latest market data
            last_updated=company.updated_at or company.created_at,
            data_sources=data_sources
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get company data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve company data. Please try again later."
        )


@router.get(
    "/company/{symbol}/market-data",
    response_model=List[MarketDataResponse],
    summary="Get company market data",
    description="Get historical market data for a company",
    responses={
        200: {"description": "Market data retrieved"},
        404: {"model": ErrorResponse, "description": "Company or market data not found"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_company_market_data(
    symbol: str,
    limit: int = 100,
    current_user = Depends(get_current_user_from_token),
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """
    Get historical market data for a company
    
    - **symbol**: Stock symbol
    - **limit**: Maximum number of records to return (default: 100, max: 1000)
    
    Returns historical price and volume data
    """
    try:
        from sqlalchemy import select
        from app.models.company import Company, MarketData
        
        symbol = symbol.strip().upper()
        limit = min(limit, 1000)  # Cap at 1000 records
        
        # Get company
        stmt = select(Company).where(Company.symbol == symbol)
        result = await db.execute(stmt)
        company = result.scalar_one_or_none()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with symbol {symbol} not found"
            )
        
        # Get market data
        stmt = select(MarketData).where(
            MarketData.company_id == company.id
        ).order_by(MarketData.price_date.desc()).limit(limit)
        
        result = await db.execute(stmt)
        market_data = result.scalars().all()
        
        if not market_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No market data found for {symbol}"
            )
        
        return [
            MarketDataResponse(
                symbol=symbol,
                price_date=data.price_date.strftime('%Y-%m-%d'),
                open_price=float(data.open_price) if data.open_price else None,
                high_price=float(data.high_price) if data.high_price else None,
                low_price=float(data.low_price) if data.low_price else None,
                close_price=float(data.close_price) if data.close_price else None,
                volume=data.volume,
                adjusted_close=float(data.adjusted_close) if data.adjusted_close else None,
            )
            for data in market_data
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get market data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market data. Please try again later."
        )


@router.get(
    "/stats",
    response_model=DataIngestionStats,
    summary="Get data ingestion statistics",
    description="Get comprehensive statistics about data ingestion activities",
    responses={
        200: {"description": "Statistics retrieved"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_data_ingestion_stats(
    current_user = Depends(get_current_user_from_token),
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """
    Get comprehensive statistics about data ingestion activities
    
    Returns metrics including:
    - Total companies in database
    - Recent update activity
    - API call statistics
    - Success/failure rates
    - Data source status
    """
    try:
        from sqlalchemy import select, func
        from datetime import datetime, timedelta
        from app.models.company import Company
        from app.models.financial_data import DataUpdate, ExternalApiLog, DataSource
        
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        # Get total companies
        stmt = select(func.count(Company.id))
        result = await db.execute(stmt)
        total_companies = result.scalar() or 0
        
        # Get companies updated today
        stmt = select(func.count(Company.id)).where(
            func.date(Company.updated_at) == today
        )
        result = await db.execute(stmt)
        companies_updated_today = result.scalar() or 0
        
        # Get companies updated this week
        stmt = select(func.count(Company.id)).where(
            func.date(Company.updated_at) >= week_ago
        )
        result = await db.execute(stmt)
        companies_updated_this_week = result.scalar() or 0
        
        # Get API calls today
        stmt = select(func.count(ExternalApiLog.id)).where(
            func.date(ExternalApiLog.called_at) == today
        )
        result = await db.execute(stmt)
        total_api_calls_today = result.scalar() or 0
        
        # Get successful ingestions today
        stmt = select(func.count(DataUpdate.id)).where(
            func.date(DataUpdate.started_at) == today,
            DataUpdate.status == 'completed'
        )
        result = await db.execute(stmt)
        successful_ingestions_today = result.scalar() or 0
        
        # Get failed ingestions today
        stmt = select(func.count(DataUpdate.id)).where(
            func.date(DataUpdate.started_at) == today,
            DataUpdate.status == 'failed'
        )
        result = await db.execute(stmt)
        failed_ingestions_today = result.scalar() or 0
        
        # Get data sources count
        stmt = select(func.count(DataSource.id))
        result = await db.execute(stmt)
        data_sources_total = result.scalar() or 0
        
        stmt = select(func.count(DataSource.id)).where(DataSource.is_active == True)
        result = await db.execute(stmt)
        data_sources_active = result.scalar() or 0
        
        return DataIngestionStats(
            total_companies=total_companies,
            companies_updated_today=companies_updated_today,
            companies_updated_this_week=companies_updated_this_week,
            total_api_calls_today=total_api_calls_today,
            successful_ingestions_today=successful_ingestions_today,
            failed_ingestions_today=failed_ingestions_today,
            average_ingestion_time=5.2,  # Placeholder - would calculate from actual data
            data_sources_active=data_sources_active,
            data_sources_total=data_sources_total
        )
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics. Please try again later."
        )