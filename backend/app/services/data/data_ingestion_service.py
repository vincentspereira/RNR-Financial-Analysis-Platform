"""
Main data ingestion service that orchestrates data collection from multiple sources
"""
import asyncio
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.audit import AuditLog
from app.models.company import Company, FinancialStatement, MarketData
from app.models.financial_data import DataSource, DataUpdate, ExternalApiLog
from app.services.data.alpha_vantage_client import alpha_vantage_client
from app.services.data.yahoo_finance_client import yahoo_finance_client


class DataIngestionService:
    """
    Main data ingestion service
    """
    
    def __init__(self):
        """Initialize data ingestion service"""
        self.alpha_vantage = alpha_vantage_client
        self.yahoo_finance = yahoo_finance_client
    
    async def ingest_company_data(
        self,
        symbol: str,
        db: AsyncSession,
        user_id: Optional[UUID] = None,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """
        Ingest comprehensive company data from multiple sources
        
        Args:
            symbol: Stock symbol
            db: Database session
            user_id: User ID for audit logging
            force_update: Force update even if recent data exists
            
        Returns:
            Dictionary with ingestion results
        """
        results = {
            'symbol': symbol,
            'success': False,
            'sources_used': [],
            'data_ingested': {},
            'errors': []
        }
        
        try:
            # Check if company exists
            company = await self._get_or_create_company(symbol, db)
            if not company:
                results['errors'].append("Failed to create/find company record")
                return results
            
            # Log data update start
            data_update = DataUpdate(
                id=uuid4(),
                data_source='multiple',
                job_type='company_data_ingestion',
                status='running',
                target_symbol=symbol,
                started_at=datetime.now(),
                metadata={'force_update': force_update}
            )
            db.add(data_update)
            await db.flush()
            
            # Ingest from Alpha Vantage
            av_success = await self._ingest_alpha_vantage_data(
                symbol, company.id, db, data_update.id
            )
            if av_success:
                results['sources_used'].append('alpha_vantage')
                results['data_ingested']['alpha_vantage'] = av_success
            
            # Ingest from Yahoo Finance
            yf_success = await self._ingest_yahoo_finance_data(
                symbol, company.id, db, data_update.id
            )
            if yf_success:
                results['sources_used'].append('yahoo_finance')
                results['data_ingested']['yahoo_finance'] = yf_success
            
            # Update data update record
            data_update.status = 'completed' if (av_success or yf_success) else 'failed'
            data_update.completed_at = datetime.now()
            data_update.records_processed = len(results['sources_used'])
            
            # Create audit log
            if user_id:
                audit_log = AuditLog.create_log(
                    action="data_ingestion",
                    resource_type="company_data",
                    user_id=user_id,
                    resource_id=company.id,
                    audit_metadata={
                        'symbol': symbol,
                        'sources_used': results['sources_used'],
                        'force_update': force_update
                    },
                    compliance_category="SOX"
                )
                db.add(audit_log)
            
            await db.commit()
            
            results['success'] = len(results['sources_used']) > 0
            
        except Exception as e:
            await db.rollback()
            results['errors'].append(f"Data ingestion failed: {str(e)}")
            
            # Update data update record with error
            if 'data_update' in locals():
                data_update.status = 'failed'
                data_update.completed_at = datetime.now()
                data_update.error_message = str(e)
                await db.commit()
        
        return results
    
    async def _get_or_create_company(self, symbol: str, db: AsyncSession) -> Optional[Company]:
        """Get existing company or create new one"""
        try:
            # Check if company exists
            stmt = select(Company).where(Company.symbol == symbol.upper())
            result = await db.execute(stmt)
            company = result.scalar_one_or_none()
            
            if company:
                return company
            
            # Create new company record
            company = Company(
                id=uuid4(),
                symbol=symbol.upper(),
                name=f"Company {symbol.upper()}",  # Will be updated with real data
                is_active=True
            )
            db.add(company)
            await db.flush()
            
            return company
            
        except Exception as e:
            print(f"Error getting/creating company {symbol}: {e}")
            return None
    
    async def _ingest_alpha_vantage_data(
        self,
        symbol: str,
        company_id: UUID,
        db: AsyncSession,
        data_update_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Ingest data from Alpha Vantage"""
        try:
            async with self.alpha_vantage as av:
                results = {}
                
                # Log API call start
                api_log = ExternalApiLog(
                    id=uuid4(),
                    data_source='alpha_vantage',
                    endpoint='company_overview',
                    request_params={'symbol': symbol},
                    called_at=datetime.now()
                )
                db.add(api_log)
                
                # Get company overview
                overview = await av.get_company_overview(symbol)
                if overview:
                    # Update company record with overview data
                    stmt = update(Company).where(Company.id == company_id).values(
                        name=overview.get('name') or f"Company {symbol}",
                        description=overview.get('description'),
                        cik=overview.get('cik'),
                        exchange=overview.get('exchange'),
                        currency=overview.get('currency'),
                        country=overview.get('country'),
                        sector=overview.get('sector'),
                        industry=overview.get('industry'),
                        address=overview.get('address'),
                        fiscal_year_end=overview.get('fiscal_year_end'),
                        updated_at=datetime.now()
                    )
                    await db.execute(stmt)
                    results['company_overview'] = True
                
                # Update API log
                api_log.completed_at = datetime.now()
                api_log.status_code = 200 if overview else 404
                api_log.response_size = len(str(overview)) if overview else 0
                
                # Get income statements
                income_statements = await av.get_income_statement(symbol)
                if income_statements:
                    await self._save_financial_statements(
                        company_id, income_statements, 'income_statement', db
                    )
                    results['income_statements'] = len(income_statements)
                
                # Get balance sheets
                balance_sheets = await av.get_balance_sheet(symbol)
                if balance_sheets:
                    await self._save_financial_statements(
                        company_id, balance_sheets, 'balance_sheet', db
                    )
                    results['balance_sheets'] = len(balance_sheets)
                
                # Get cash flow statements
                cash_flows = await av.get_cash_flow(symbol)
                if cash_flows:
                    await self._save_financial_statements(
                        company_id, cash_flows, 'cash_flow', db
                    )
                    results['cash_flows'] = len(cash_flows)
                
                # Get daily prices
                daily_prices = await av.get_daily_prices(symbol)
                if daily_prices and daily_prices.get('prices'):
                    await self._save_market_data(
                        company_id, daily_prices['prices'], db
                    )
                    results['daily_prices'] = len(daily_prices['prices'])
                
                return results if results else None
                
        except Exception as e:
            print(f"Error ingesting Alpha Vantage data for {symbol}: {e}")
            return None
    
    async def _ingest_yahoo_finance_data(
        self,
        symbol: str,
        company_id: UUID,
        db: AsyncSession,
        data_update_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Ingest data from Yahoo Finance"""
        try:
            results = {}
            
            # Log API call start
            api_log = ExternalApiLog(
                id=uuid4(),
                data_source='yahoo_finance',
                endpoint='stock_info',
                request_params={'symbol': symbol},
                called_at=datetime.now()
            )
            db.add(api_log)
            
            # Get stock info
            stock_info = await self.yahoo_finance.get_stock_info(symbol)
            if stock_info:
                # Update company record with Yahoo Finance data
                stmt = update(Company).where(Company.id == company_id).values(
                    name=stock_info.get('long_name') or stock_info.get('short_name') or f"Company {symbol}",
                    exchange=stock_info.get('exchange'),
                    currency=stock_info.get('currency'),
                    country=stock_info.get('country'),
                    sector=stock_info.get('sector'),
                    industry=stock_info.get('industry'),
                    website=stock_info.get('website'),
                    business_summary=stock_info.get('business_summary'),
                    full_time_employees=stock_info.get('full_time_employees'),
                    updated_at=datetime.now()
                )
                await db.execute(stmt)
                results['stock_info'] = True
            
            # Update API log
            api_log.completed_at = datetime.now()
            api_log.status_code = 200 if stock_info else 404
            api_log.response_size = len(str(stock_info)) if stock_info else 0
            
            # Get historical data
            historical_data = await self.yahoo_finance.get_historical_data(symbol)
            if historical_data:
                await self._save_market_data(company_id, historical_data, db)
                results['historical_data'] = len(historical_data)
            
            # Get financials
            financials = await self.yahoo_finance.get_financials(symbol)
            if financials:
                # Save income statements
                if 'income_statements' in financials:
                    await self._save_financial_statements(
                        company_id, financials['income_statements'], 'income_statement', db
                    )
                    results['income_statements'] = len(financials['income_statements'])
                
                # Save balance sheets
                if 'balance_sheets' in financials:
                    await self._save_financial_statements(
                        company_id, financials['balance_sheets'], 'balance_sheet', db
                    )
                    results['balance_sheets'] = len(financials['balance_sheets'])
                
                # Save cash flows
                if 'cash_flows' in financials:
                    await self._save_financial_statements(
                        company_id, financials['cash_flows'], 'cash_flow', db
                    )
                    results['cash_flows'] = len(financials['cash_flows'])
            
            return results if results else None
            
        except Exception as e:
            print(f"Error ingesting Yahoo Finance data for {symbol}: {e}")
            return None
    
    async def _save_financial_statements(
        self,
        company_id: UUID,
        statements: List[Dict[str, Any]],
        statement_type: str,
        db: AsyncSession
    ):
        """Save financial statements to database"""
        try:
            for statement_data in statements:
                # Extract date information
                date_field = statement_data.get('fiscal_date_ending') or statement_data.get('date')
                if not date_field:
                    continue
                
                # Parse date
                if isinstance(date_field, str):
                    report_date = datetime.strptime(date_field, '%Y-%m-%d').date()
                else:
                    report_date = date_field
                
                # Determine fiscal year and quarter
                fiscal_year = report_date.year
                fiscal_quarter = None  # Assume annual data for now
                
                # Check if statement already exists
                stmt = select(FinancialStatement).where(
                    FinancialStatement.company_id == company_id,
                    FinancialStatement.statement_type == statement_type,
                    FinancialStatement.fiscal_year == fiscal_year,
                    FinancialStatement.period_type == 'annual'
                )
                result = await db.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing statement
                    existing.data = statement_data
                    existing.updated_at = datetime.now()
                else:
                    # Create new statement
                    financial_statement = FinancialStatement(
                        id=uuid4(),
                        company_id=company_id,
                        statement_type=statement_type,
                        period_type='annual',
                        fiscal_year=fiscal_year,
                        fiscal_quarter=fiscal_quarter,
                        report_date=report_date,
                        data=statement_data
                    )
                    db.add(financial_statement)
                    
        except Exception as e:
            print(f"Error saving financial statements: {e}")
    
    async def _save_market_data(
        self,
        company_id: UUID,
        price_data: List[Dict[str, Any]],
        db: AsyncSession
    ):
        """Save market data to database"""
        try:
            for price_record in price_data[:100]:  # Limit to recent 100 records
                # Extract date
                date_field = price_record.get('date')
                if not date_field:
                    continue
                
                # Parse date
                if isinstance(date_field, str):
                    price_date = datetime.strptime(date_field, '%Y-%m-%d').date()
                else:
                    price_date = date_field
                
                # Check if market data already exists
                stmt = select(MarketData).where(
                    MarketData.company_id == company_id,
                    MarketData.price_date == price_date
                )
                result = await db.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing data
                    existing.open_price = price_record.get('open')
                    existing.high_price = price_record.get('high')
                    existing.low_price = price_record.get('low')
                    existing.close_price = price_record.get('close') or price_record.get('adjusted_close')
                    existing.volume = price_record.get('volume')
                    existing.adjusted_close = price_record.get('adjusted_close')
                    existing.updated_at = datetime.now()
                else:
                    # Create new market data
                    market_data = MarketData(
                        id=uuid4(),
                        company_id=company_id,
                        price_date=price_date,
                        open_price=price_record.get('open'),
                        high_price=price_record.get('high'),
                        low_price=price_record.get('low'),
                        close_price=price_record.get('close') or price_record.get('adjusted_close'),
                        volume=price_record.get('volume'),
                        adjusted_close=price_record.get('adjusted_close')
                    )
                    db.add(market_data)
                    
        except Exception as e:
            print(f"Error saving market data: {e}")
    
    async def batch_ingest_companies(
        self,
        symbols: List[str],
        db: AsyncSession,
        user_id: Optional[UUID] = None,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        Batch ingest data for multiple companies
        
        Args:
            symbols: List of stock symbols
            db: Database session
            user_id: User ID for audit logging
            max_concurrent: Maximum concurrent ingestions
            
        Returns:
            Batch ingestion results
        """
        results = {
            'total_requested': len(symbols),
            'successful': [],
            'failed': [],
            'errors': []
        }
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        _results_lock = asyncio.Lock()
        
        async def ingest_single(symbol: str):
            async with semaphore:
                try:
                    result = await self.ingest_company_data(symbol, db, user_id)
                    async with _results_lock:
                        if result['success']:
                            results['successful'].append(result)
                        else:
                            results['failed'].append(result)
                except Exception as e:
                    async with _results_lock:
                        results['failed'].append({
                            'symbol': symbol,
                            'success': False,
                            'errors': [str(e)]
                        })
        
        # Run batch ingestion
        tasks = [ingest_single(symbol) for symbol in symbols]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        results['total_successful'] = len(results['successful'])
        results['total_failed'] = len(results['failed'])
        
        return results
    
    async def get_data_source_status(self, db: AsyncSession) -> Dict[str, Any]:
        """Get status of all data sources"""
        try:
            # Get data sources
            stmt = select(DataSource)
            result = await db.execute(stmt)
            data_sources = result.scalars().all()
            
            status = {}
            for source in data_sources:
                status[source.name] = {
                    'is_active': source.is_active,
                    'last_successful_update': source.last_successful_update,
                    'total_api_calls_today': source.total_api_calls_today,
                    'rate_limit_remaining': source.rate_limit_remaining,
                    'configuration': source.configuration
                }
            
            return status
            
        except Exception as e:
            print(f"Error getting data source status: {e}")
            return {}


# Global data ingestion service instance
data_ingestion_service = DataIngestionService()