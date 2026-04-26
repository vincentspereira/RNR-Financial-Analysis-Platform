"""
Main financial calculator service that orchestrates all financial calculations
"""
from functools import lru_cache
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, FinancialStatement, FinancialRatio, MarketData
from app.core.logging import get_logger

logger = get_logger("app.services.calculator.financial_calculator")


class FinancialCalculator:
    """Main financial calculator service — receives sub-calculators via DI."""

    def __init__(
        self,
        ratio_calc=None,
        valuation_calc=None,
    ):
        if ratio_calc is None:
            from app.services.calculator.ratio_calculator import ratio_calculator
            ratio_calc = ratio_calculator
        if valuation_calc is None:
            from app.services.calculator.valuation_calculator import valuation_calculator
            valuation_calc = valuation_calculator

        self.ratio_calc = ratio_calc
        self.valuation_calc = valuation_calc
    
    async def get_company_financial_data(
        self,
        company_id: UUID,
        period_type: str,
        fiscal_year: int,
        fiscal_quarter: Optional[int],
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive financial data for a company
        
        Args:
            company_id: Company UUID
            period_type: 'quarterly' or 'annual'
            fiscal_year: Fiscal year
            fiscal_quarter: Fiscal quarter (for quarterly data)
            db: Database session
            
        Returns:
            Dictionary containing all financial data or None if not found
        """
        try:
            # Get financial statements
            stmt_query = select(FinancialStatement).where(
                FinancialStatement.company_id == company_id,
                FinancialStatement.period_type == period_type,
                FinancialStatement.fiscal_year == fiscal_year
            )
            
            if fiscal_quarter:
                stmt_query = stmt_query.where(FinancialStatement.fiscal_quarter == fiscal_quarter)
            
            result = await db.execute(stmt_query)
            statements = result.scalars().all()
            
            if not statements:
                return None
            
            # Combine all statement data
            financial_data = {}
            for statement in statements:
                financial_data.update(statement.data)
            
            # Get market data (latest available)
            market_query = select(MarketData).where(
                MarketData.company_id == company_id
            ).order_by(MarketData.price_date.desc()).limit(1)
            
            market_result = await db.execute(market_query)
            market_data = market_result.scalar_one_or_none()
            
            if market_data:
                financial_data.update({
                    'stock_price': float(market_data.close_price),
                    'volume': market_data.volume,
                    'market_date': market_data.price_date,
                })
            
            return financial_data
            
        except Exception as e:
            logger.error("Error getting financial data: %s", e, exc_info=True)
            return None
    
    async def calculate_financial_ratios(
        self,
        company_id: UUID,
        period_type: str,
        fiscal_year: int,
        fiscal_quarter: Optional[int],
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate all financial ratios for a company
        
        Args:
            company_id: Company UUID
            period_type: 'quarterly' or 'annual'
            fiscal_year: Fiscal year
            fiscal_quarter: Fiscal quarter (for quarterly data)
            db: Database session
            
        Returns:
            Dictionary containing all calculated ratios
        """
        # Get current period data
        current_data = await self.get_company_financial_data(
            company_id, period_type, fiscal_year, fiscal_quarter, db
        )
        
        if not current_data:
            return None
        
        # Get previous period data for growth calculations
        previous_data = None
        if period_type == 'quarterly' and fiscal_quarter and fiscal_quarter > 1:
            # Previous quarter
            previous_data = await self.get_company_financial_data(
                company_id, period_type, fiscal_year, fiscal_quarter - 1, db
            )
        elif period_type == 'quarterly' and fiscal_quarter == 1:
            # Q4 of previous year
            previous_data = await self.get_company_financial_data(
                company_id, period_type, fiscal_year - 1, 4, db
            )
        elif period_type == 'annual':
            # Previous year
            previous_data = await self.get_company_financial_data(
                company_id, period_type, fiscal_year - 1, None, db
            )
        
        # Calculate all ratios
        ratios = self.ratio_calc.calculate_all_ratios(current_data, previous_data)
        
        return {
            'company_id': str(company_id),
            'period_type': period_type,
            'fiscal_year': fiscal_year,
            'fiscal_quarter': fiscal_quarter,
            'calculation_date': datetime.now().date(),
            'ratios': ratios
        }
    
    async def save_calculated_ratios(
        self,
        ratios_data: Dict[str, Any],
        db: AsyncSession
    ) -> bool:
        """
        Save calculated ratios to database
        
        Args:
            ratios_data: Dictionary containing calculated ratios
            db: Database session
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Check if ratios already exist for this period
            existing_query = select(FinancialRatio).where(
                FinancialRatio.company_id == UUID(ratios_data['company_id']),
                FinancialRatio.period_type == ratios_data['period_type'],
                FinancialRatio.fiscal_year == ratios_data['fiscal_year'],
                FinancialRatio.fiscal_quarter == ratios_data['fiscal_quarter']
            )
            
            result = await db.execute(existing_query)
            existing_ratio = result.scalar_one_or_none()
            
            ratios = ratios_data['ratios']
            
            if existing_ratio:
                # Update existing ratios
                for key, value in ratios.items():
                    if hasattr(existing_ratio, key) and value is not None:
                        setattr(existing_ratio, key, value)
                existing_ratio.calculation_date = ratios_data['calculation_date']
            else:
                # Create new ratio record
                new_ratio = FinancialRatio(
                    company_id=UUID(ratios_data['company_id']),
                    period_type=ratios_data['period_type'],
                    fiscal_year=ratios_data['fiscal_year'],
                    fiscal_quarter=ratios_data['fiscal_quarter'],
                    calculation_date=ratios_data['calculation_date'],
                    **{k: v for k, v in ratios.items() if hasattr(FinancialRatio, k) and v is not None}
                )
                db.add(new_ratio)
            
            await db.commit()
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error("Error saving ratios: %s", e, exc_info=True)
            return False
    
    async def calculate_company_valuation(
        self,
        company_id: UUID,
        valuation_assumptions: Dict[str, Any],
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate comprehensive company valuation
        
        Args:
            company_id: Company UUID
            valuation_assumptions: Valuation assumptions and parameters
            db: Database session
            
        Returns:
            Dictionary containing valuation results
        """
        try:
            # Get latest financial data
            current_year = datetime.now().year
            financial_data = await self.get_company_financial_data(
                company_id, 'annual', current_year - 1, None, db
            )
            
            if not financial_data:
                return None
            
            # Get company info
            company_query = select(Company).where(Company.id == company_id)
            result = await db.execute(company_query)
            company = result.scalar_one_or_none()
            
            if not company:
                return None
            
            # Prepare market data
            market_data = {
                'shares_outstanding': valuation_assumptions.get('shares_outstanding', 1000000),
                'enterprise_value': valuation_assumptions.get('enterprise_value'),
                'pe_ratio': valuation_assumptions.get('pe_ratio'),
            }
            
            # Calculate fair value estimates
            fair_values = self.valuation_calc.calculate_fair_value_estimate(
                financial_data,
                market_data,
                valuation_assumptions
            )
            
            # Calculate quality scores
            altman_z = None
            if all(key in financial_data for key in [
                'working_capital', 'total_assets', 'retained_earnings', 
                'ebit', 'total_liabilities', 'revenue'
            ]):
                altman_z = self.valuation_calc.calculate_altman_z_score(
                    financial_data['working_capital'],
                    financial_data['total_assets'],
                    financial_data['retained_earnings'],
                    financial_data['ebit'],
                    market_data.get('market_cap', 0),
                    financial_data['total_liabilities'],
                    financial_data['revenue']
                )
            
            return {
                'company_id': str(company_id),
                'company_name': company.name,
                'company_symbol': company.symbol,
                'valuation_date': datetime.now().date(),
                'fair_value_estimates': fair_values,
                'quality_scores': {
                    'altman_z_score': altman_z
                },
                'assumptions_used': valuation_assumptions
            }
            
        except Exception as e:
            logger.error("Error calculating valuation: %s", e, exc_info=True)
            return None
    
    async def get_peer_comparison(
        self,
        company_id: UUID,
        peer_company_ids: List[UUID],
        period_type: str,
        fiscal_year: int,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        Get peer comparison analysis
        
        Args:
            company_id: Target company UUID
            peer_company_ids: List of peer company UUIDs
            period_type: 'quarterly' or 'annual'
            fiscal_year: Fiscal year
            db: Database session
            
        Returns:
            Dictionary containing peer comparison data
        """
        try:
            comparison_data = {}
            
            # Get data for target company
            target_ratios = await self.calculate_financial_ratios(
                company_id, period_type, fiscal_year, None, db
            )
            
            if not target_ratios:
                return None
            
            comparison_data['target_company'] = target_ratios
            comparison_data['peer_companies'] = []
            
            # Get data for peer companies
            for peer_id in peer_company_ids:
                peer_ratios = await self.calculate_financial_ratios(
                    peer_id, period_type, fiscal_year, None, db
                )
                
                if peer_ratios:
                    comparison_data['peer_companies'].append(peer_ratios)
            
            # Calculate peer averages and percentiles
            if comparison_data['peer_companies']:
                peer_stats = self._calculate_peer_statistics(comparison_data['peer_companies'])
                comparison_data['peer_statistics'] = peer_stats
            
            return comparison_data
            
        except Exception as e:
            logger.error("Error in peer comparison: %s", e, exc_info=True)
            return None
    
    def _calculate_peer_statistics(self, peer_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate peer statistics (averages, medians, percentiles)
        
        Args:
            peer_data: List of peer company ratio data
            
        Returns:
            Dictionary containing peer statistics
        """
        if not peer_data:
            return {}
        
        # Collect all ratio values
        ratio_values = {}
        for peer in peer_data:
            for ratio_name, ratio_value in peer.get('ratios', {}).items():
                if ratio_value is not None:
                    if ratio_name not in ratio_values:
                        ratio_values[ratio_name] = []
                    ratio_values[ratio_name].append(float(ratio_value))
        
        # Calculate statistics
        statistics = {}
        for ratio_name, values in ratio_values.items():
            if values:
                values.sort()
                n = len(values)
                
                statistics[ratio_name] = {
                    'count': n,
                    'average': sum(values) / n,
                    'median': values[n // 2] if n % 2 == 1 else (values[n // 2 - 1] + values[n // 2]) / 2,
                    'min': min(values),
                    'max': max(values),
                    'percentile_25': values[int(n * 0.25)],
                    'percentile_75': values[int(n * 0.75)],
                }
        
        return statistics


@lru_cache(maxsize=1)
def get_financial_calculator() -> FinancialCalculator:
    """FastAPI dependency — returns a cached FinancialCalculator instance."""
    return FinancialCalculator()