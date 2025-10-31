"""
Financial calculation API endpoints
"""
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.auth import ErrorResponse
from app.schemas.financial import (
    BatchRatiosRequest,
    BatchRatiosResponse,
    CompanyFinancialDataResponse,
    FinancialHealthScore,
    FinancialRatiosRequest,
    FinancialRatiosResponse,
    PeerComparisonRequest,
    PeerComparisonResponse,
    ValuationRequest,
    ValuationResponse,
)
from app.services.calculator.financial_calculator import financial_calculator

router = APIRouter(prefix="/financial", tags=["Financial Analysis"])


@router.post(
    "/ratios/calculate",
    response_model=FinancialRatiosResponse,
    summary="Calculate financial ratios",
    description="Calculate comprehensive financial ratios for a company",
    responses={
        200: {"description": "Financial ratios calculated successfully"},
        404: {"model": ErrorResponse, "description": "Company or financial data not found"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def calculate_financial_ratios(
    request: FinancialRatiosRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    Calculate comprehensive financial ratios for a company
    
    - **company_id**: UUID of the company
    - **period_type**: 'quarterly' or 'annual'
    - **fiscal_year**: Fiscal year for the calculation
    - **fiscal_quarter**: Fiscal quarter (1-4, required for quarterly data)
    
    Returns calculated ratios including:
    - Liquidity ratios (current, quick, cash ratios)
    - Profitability ratios (margins, ROA, ROE, ROIC)
    - Leverage ratios (debt-to-equity, interest coverage)
    - Efficiency ratios (asset turnover, inventory turnover)
    - Valuation ratios (P/E, P/B, EV/EBITDA)
    - Growth ratios (revenue, earnings growth)
    - Quality scores (Piotroski F-Score)
    """
    try:
        # Validate quarterly data requirements
        if request.period_type == 'quarterly' and not request.fiscal_quarter:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fiscal quarter is required for quarterly data"
            )
        
        if request.fiscal_quarter and not (1 <= request.fiscal_quarter <= 4):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fiscal quarter must be between 1 and 4"
            )
        
        # Calculate ratios
        ratios_data = await financial_calculator.calculate_financial_ratios(
            company_id=request.company_id,
            period_type=request.period_type,
            fiscal_year=request.fiscal_year,
            fiscal_quarter=request.fiscal_quarter,
            db=db
        )
        
        if not ratios_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company or financial data not found for the specified period"
            )
        
        # Save calculated ratios to database
        await financial_calculator.save_calculated_ratios(ratios_data, db)
        
        return FinancialRatiosResponse(**ratios_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating financial ratios: {str(e)}"
        )


@router.post(
    "/valuation/calculate",
    response_model=ValuationResponse,
    summary="Calculate company valuation",
    description="Calculate comprehensive company valuation using multiple models",
    responses={
        200: {"description": "Valuation calculated successfully"},
        404: {"model": ErrorResponse, "description": "Company not found"},
        400: {"model": ErrorResponse, "description": "Invalid valuation assumptions"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def calculate_company_valuation(
    request: ValuationRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    Calculate comprehensive company valuation using multiple models
    
    - **company_id**: UUID of the company
    - **assumptions**: Valuation assumptions including:
        - free_cash_flows: List of projected free cash flows
        - terminal_growth_rate: Terminal growth rate (decimal)
        - discount_rate: Discount rate/WACC (decimal)
        - shares_outstanding: Number of shares outstanding
        - dividend_growth_rate: Expected dividend growth rate
        - required_return: Required rate of return
        - earnings_growth_rate: Expected earnings growth rate
    
    Returns valuation estimates from:
    - Discounted Cash Flow (DCF) model
    - Dividend Discount Model (DDM)
    - Graham Number calculation
    - PEG ratio analysis
    - Enterprise Value multiples
    - Quality scores (Altman Z-Score)
    """
    try:
        valuation_data = await financial_calculator.calculate_company_valuation(
            company_id=request.company_id,
            valuation_assumptions=request.assumptions,
            db=db
        )
        
        if not valuation_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found or insufficient financial data for valuation"
            )
        
        return ValuationResponse(**valuation_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating valuation: {str(e)}"
        )


@router.post(
    "/peer-comparison",
    response_model=PeerComparisonResponse,
    summary="Peer comparison analysis",
    description="Compare a company's financial ratios with peer companies",
    responses={
        200: {"description": "Peer comparison completed successfully"},
        404: {"model": ErrorResponse, "description": "Company or peer data not found"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def peer_comparison_analysis(
    request: PeerComparisonRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    Compare a company's financial ratios with peer companies
    
    - **company_id**: UUID of the target company
    - **peer_company_ids**: List of peer company UUIDs
    - **period_type**: 'quarterly' or 'annual'
    - **fiscal_year**: Fiscal year for comparison
    
    Returns:
    - Target company ratios
    - Peer company ratios
    - Peer statistics (averages, medians, percentiles)
    """
    try:
        if not request.peer_company_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one peer company ID is required"
            )
        
        comparison_data = await financial_calculator.get_peer_comparison(
            company_id=request.company_id,
            peer_company_ids=request.peer_company_ids,
            period_type=request.period_type,
            fiscal_year=request.fiscal_year,
            db=db
        )
        
        if not comparison_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target company data not found for the specified period"
            )
        
        return PeerComparisonResponse(**comparison_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in peer comparison: {str(e)}"
        )


@router.get(
    "/company/{company_id}/financial-data",
    response_model=CompanyFinancialDataResponse,
    summary="Get company financial data",
    description="Get raw financial data for a company",
    responses={
        200: {"description": "Financial data retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Company or financial data not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_company_financial_data(
    company_id: UUID,
    period_type: str,
    fiscal_year: int,
    fiscal_quarter: Optional[int] = None,
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """
    Get raw financial data for a company
    
    - **company_id**: UUID of the company
    - **period_type**: 'quarterly' or 'annual'
    - **fiscal_year**: Fiscal year
    - **fiscal_quarter**: Fiscal quarter (optional, for quarterly data)
    
    Returns raw financial statement data and market data
    """
    try:
        financial_data = await financial_calculator.get_company_financial_data(
            company_id=company_id,
            period_type=period_type,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            db=db
        )
        
        if not financial_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Financial data not found for the specified company and period"
            )
        
        # Separate market data from financial data
        market_data = {}
        pure_financial_data = {}
        
        market_fields = ['stock_price', 'volume', 'market_date', 'market_cap']
        
        for key, value in financial_data.items():
            if key in market_fields:
                market_data[key] = value
            else:
                pure_financial_data[key] = value
        
        return CompanyFinancialDataResponse(
            company_id=company_id,
            period_type=period_type,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            financial_data=pure_financial_data,
            market_data=market_data if market_data else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving financial data: {str(e)}"
        )


@router.post(
    "/ratios/batch-calculate",
    response_model=BatchRatiosResponse,
    summary="Batch calculate financial ratios",
    description="Calculate financial ratios for multiple companies",
    responses={
        200: {"description": "Batch calculation completed"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def batch_calculate_ratios(
    request: BatchRatiosRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    Calculate financial ratios for multiple companies in batch
    
    - **company_ids**: List of company UUIDs
    - **period_type**: 'quarterly' or 'annual'
    - **fiscal_year**: Fiscal year
    - **fiscal_quarter**: Fiscal quarter (for quarterly data)
    
    Returns results for successful calculations and errors for failed ones
    """
    try:
        if not request.company_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one company ID is required"
            )
        
        if len(request.company_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 companies allowed per batch request"
            )
        
        successful_calculations = []
        failed_calculations = []
        
        for company_id in request.company_ids:
            try:
                ratios_data = await financial_calculator.calculate_financial_ratios(
                    company_id=company_id,
                    period_type=request.period_type,
                    fiscal_year=request.fiscal_year,
                    fiscal_quarter=request.fiscal_quarter,
                    db=db
                )
                
                if ratios_data:
                    # Save calculated ratios
                    await financial_calculator.save_calculated_ratios(ratios_data, db)
                    successful_calculations.append(FinancialRatiosResponse(**ratios_data))
                else:
                    failed_calculations.append({
                        "company_id": str(company_id),
                        "error": "Financial data not found for the specified period"
                    })
                    
            except Exception as e:
                failed_calculations.append({
                    "company_id": str(company_id),
                    "error": str(e)
                })
        
        return BatchRatiosResponse(
            successful_calculations=successful_calculations,
            failed_calculations=failed_calculations,
            total_requested=len(request.company_ids),
            total_successful=len(successful_calculations),
            total_failed=len(failed_calculations)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in batch calculation: {str(e)}"
        )