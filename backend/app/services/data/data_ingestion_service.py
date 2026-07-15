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
from app.core.config import settings
from app.models.audit import AuditLog
from app.models.company import Company, FinancialStatement, MarketData
from app.models.financial_data import DataSource, DataUpdate, ExternalApiLog
from app.services.data.alpha_vantage_client import alpha_vantage_client
from app.core.logging import get_logger

logger = get_logger("app.services.data.data_ingestion")
from app.services.data.yahoo_finance_client import yahoo_finance_client
from app.services.data.sec_edgar_client import sec_edgar_client
from app.services.data.financial_modeling_prep_client import financial_modeling_prep_client


class DataIngestionService:
    """
    Main data ingestion service
    """

    def __init__(self):
        """Initialize data ingestion service"""
        self.alpha_vantage = alpha_vantage_client
        self.yahoo_finance = yahoo_finance_client
        self.sec_edgar = sec_edgar_client
        self.fmp = financial_modeling_prep_client

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
                symbols=[symbol],
                started_at=datetime.now(),
                parameters={'force_update': force_update}
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

            # Ingest from Yahoo Finance (gated — Yahoo TOS prohibits commercial
            # use; disable via YFINANCE_ENABLED=false in production / MAS paths).
            yf_success = False
            if settings.YFINANCE_ENABLED:
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

            # Create new company record (exchange is NOT NULL)
            company = Company(
                id=uuid4(),
                symbol=symbol.upper(),
                name=f"Company {symbol.upper()}",
                exchange='UNKNOWN',
                is_active=True
            )
            db.add(company)
            await db.flush()

            return company

        except Exception as e:
            logger.error("Error getting/creating company %s: %s", symbol, e, exc_info=True)
            return None

    def _build_api_log(
        self,
        data_source: str,
        endpoint: str,
        method: str,
        request_params: Optional[dict],
        start_time: datetime,
        status_code: int,
        response_size_bytes: int = 0,
        error_message: Optional[str] = None,
    ) -> ExternalApiLog:
        """Build a complete ExternalApiLog with all required fields"""
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        return ExternalApiLog(
            id=uuid4(),
            data_source=data_source,
            endpoint=endpoint,
            method=method,
            request_params=request_params,
            status_code=status_code,
            response_time_ms=int(elapsed),
            response_size_bytes=response_size_bytes,
            error_message=error_message,
        )

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
                start_time = datetime.now()

                # Get company overview
                overview = await av.get_company_overview(symbol)
                status_code = 200 if overview else 404
                api_log = self._build_api_log(
                    data_source='alpha_vantage',
                    endpoint='company_overview',
                    method='GET',
                    request_params={'symbol': symbol},
                    start_time=start_time,
                    status_code=status_code,
                    response_size_bytes=len(str(overview)) if overview else 0,
                )
                db.add(api_log)

                if overview:
                    # Update company record with overview data (only columns that exist)
                    stmt = update(Company).where(Company.id == company_id).values(
                        name=overview.get('name') or f"Company {symbol}",
                        description=overview.get('description'),
                        cik=overview.get('cik'),
                        exchange=overview.get('exchange') or 'UNKNOWN',
                        sector=overview.get('sector'),
                        industry=overview.get('industry'),
                        headquarters=overview.get('address'),
                        market_cap=overview.get('market_cap'),
                        updated_at=datetime.now()
                    )
                    await db.execute(stmt)
                    results['company_overview'] = True

                # Get income statements
                income_statements = await av.get_income_statement(symbol)
                if income_statements:
                    await self._save_financial_statements(
                        company_id, income_statements, 'income_statement', 'alpha_vantage', db
                    )
                    results['income_statements'] = len(income_statements)

                # Get balance sheets
                balance_sheets = await av.get_balance_sheet(symbol)
                if balance_sheets:
                    await self._save_financial_statements(
                        company_id, balance_sheets, 'balance_sheet', 'alpha_vantage', db
                    )
                    results['balance_sheets'] = len(balance_sheets)

                # Get cash flow statements
                cash_flows = await av.get_cash_flow(symbol)
                if cash_flows:
                    await self._save_financial_statements(
                        company_id, cash_flows, 'cash_flow', 'alpha_vantage', db
                    )
                    results['cash_flows'] = len(cash_flows)

                # Get daily prices
                daily_prices = await av.get_daily_prices(symbol)
                if daily_prices and daily_prices.get('prices'):
                    await self._save_market_data(
                        company_id, daily_prices['prices'], 'alpha_vantage', db
                    )
                    results['daily_prices'] = len(daily_prices['prices'])

                return results if results else None

        except Exception as e:
            logger.error("Error ingesting Alpha Vantage data for %s: %s", symbol, e, exc_info=True)
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
            start_time = datetime.now()

            # Get stock info
            stock_info = await self.yahoo_finance.get_stock_info(symbol)
            status_code = 200 if stock_info else 404
            api_log = self._build_api_log(
                data_source='yahoo_finance',
                endpoint='stock_info',
                method='GET',
                request_params={'symbol': symbol},
                start_time=start_time,
                status_code=status_code,
                response_size_bytes=len(str(stock_info)) if stock_info else 0,
            )
            db.add(api_log)

            if stock_info:
                # Update company record with Yahoo Finance data (only columns that exist)
                stmt = update(Company).where(Company.id == company_id).values(
                    name=stock_info.get('long_name') or stock_info.get('short_name') or f"Company {symbol}",
                    exchange=stock_info.get('exchange') or 'UNKNOWN',
                    sector=stock_info.get('sector'),
                    industry=stock_info.get('industry'),
                    website=stock_info.get('website'),
                    description=stock_info.get('business_summary'),
                    employees=stock_info.get('full_time_employees'),
                    updated_at=datetime.now()
                )
                await db.execute(stmt)
                results['stock_info'] = True

            # Get historical data
            historical_data = await self.yahoo_finance.get_historical_data(symbol)
            if historical_data:
                await self._save_market_data(company_id, historical_data, 'yahoo_finance', db)
                results['historical_data'] = len(historical_data)

            # Get financials
            financials = await self.yahoo_finance.get_financials(symbol)
            if financials:
                # Save income statements
                if 'income_statements' in financials:
                    await self._save_financial_statements(
                        company_id, financials['income_statements'], 'income_statement', 'yahoo_finance', db
                    )
                    results['income_statements'] = len(financials['income_statements'])

                # Save balance sheets
                if 'balance_sheets' in financials:
                    await self._save_financial_statements(
                        company_id, financials['balance_sheets'], 'balance_sheet', 'yahoo_finance', db
                    )
                    results['balance_sheets'] = len(financials['balance_sheets'])

                # Save cash flows
                if 'cash_flows' in financials:
                    await self._save_financial_statements(
                        company_id, financials['cash_flows'], 'cash_flow', 'yahoo_finance', db
                    )
                    results['cash_flows'] = len(financials['cash_flows'])

            return results if results else None

        except Exception as e:
            logger.error("Error ingesting Yahoo Finance data for %s: %s", symbol, e, exc_info=True)
            return None

    async def _save_financial_statements(
        self,
        company_id: UUID,
        statements: List[Dict[str, Any]],
        statement_type: str,
        data_source: str,
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
                        data=statement_data,
                        data_source=data_source
                    )
                    db.add(financial_statement)

        except Exception as e:
            logger.error("Error saving financial statements: %s", e, exc_info=True)

    async def _save_market_data(
        self,
        company_id: UUID,
        price_data: List[Dict[str, Any]],
        data_source: str,
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
                    existing.volume = price_record.get('volume', 0)
                    existing.adjusted_close = price_record.get('adjusted_close')
                    existing.updated_at = datetime.now()
                else:
                    # Create new market data
                    close = price_record.get('close') or price_record.get('adjusted_close') or 0
                    volume = price_record.get('volume', 0)
                    market_data = MarketData(
                        id=uuid4(),
                        company_id=company_id,
                        price_date=price_date,
                        open_price=price_record.get('open'),
                        high_price=price_record.get('high'),
                        low_price=price_record.get('low'),
                        close_price=close,
                        volume=volume,
                        adjusted_close=price_record.get('adjusted_close'),
                        data_source=data_source
                    )
                    db.add(market_data)

        except Exception as e:
            logger.error("Error saving market data: %s", e, exc_info=True)

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
                    'last_successful_update': source.updated_at.isoformat() if source.updated_at else None,
                    'total_api_calls_today': 0,
                    'rate_limit_remaining': source.rate_limit_per_day,
                    'configuration': source.configuration
                }

            return status

        except Exception as e:
            logger.error("Error getting data source status: %s", e, exc_info=True)
            return {}


# Global data ingestion service instance
data_ingestion_service = DataIngestionService()
