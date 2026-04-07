"""
Portfolio Service - Portfolio Management Operations with Database Integration
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.portfolio import Portfolio, PortfolioHolding, Transaction

logger = get_logger("app.portfolio")


class PortfolioService:
    """Service for portfolio management operations using database"""

    async def create_portfolio(
        self, db: AsyncSession, user_id: str, portfolio_data: Dict[str, Any]
    ) -> Portfolio:
        """Create a new portfolio"""
        portfolio = Portfolio(
            user_id=user_id if isinstance(user_id, UUID) else UUID(user_id),
            name=portfolio_data.get("name", "My Portfolio"),
            description=portfolio_data.get("description", ""),
            cash_balance=Decimal(str(portfolio_data.get("cash_balance", "0.00"))),
            is_active=True,
        )
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)
        logger.logger.info("Created portfolio %s for user %s", portfolio.id, user_id)
        return portfolio

    async def get_portfolio(
        self, db: AsyncSession, portfolio_id: str, user_id: str
    ) -> Optional[Portfolio]:
        """Get portfolio by ID with holdings eagerly loaded"""
        uid = user_id if isinstance(user_id, UUID) else UUID(user_id)
        pid = portfolio_id if isinstance(portfolio_id, UUID) else UUID(portfolio_id)

        stmt = (
            select(Portfolio)
            .options(selectinload(Portfolio.holdings))
            .where(and_(Portfolio.id == pid, Portfolio.user_id == uid))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_portfolios(
        self, db: AsyncSession, user_id: str
    ) -> List[Portfolio]:
        """Get all active portfolios for a user"""
        uid = user_id if isinstance(user_id, UUID) else UUID(user_id)
        stmt = (
            select(Portfolio)
            .options(selectinload(Portfolio.holdings))
            .where(and_(Portfolio.user_id == uid, Portfolio.is_active == True))
            .order_by(Portfolio.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_portfolios_paginated(
        self, db: AsyncSession, user_id: str, skip: int = 0, limit: int = 10
    ) -> Dict[str, Any]:
        """Get paginated portfolios for a user"""
        uid = user_id if isinstance(user_id, UUID) else UUID(user_id)

        # Count total
        count_stmt = select(func.count()).select_from(Portfolio).where(
            and_(Portfolio.user_id == uid, Portfolio.is_active == True)
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        # Fetch page
        stmt = (
            select(Portfolio)
            .options(selectinload(Portfolio.holdings))
            .where(and_(Portfolio.user_id == uid, Portfolio.is_active == True))
            .order_by(Portfolio.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        portfolios = list(result.scalars().all())

        return {
            "portfolios": portfolios,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": skip + limit < total,
        }

    async def update_portfolio(
        self, db: AsyncSession, portfolio_id: str, user_id: str, data: Dict[str, Any]
    ) -> Optional[Portfolio]:
        """Update portfolio"""
        portfolio = await self.get_portfolio(db, portfolio_id, user_id)
        if not portfolio:
            return None

        allowed_fields = ["name", "description", "cash_balance"]
        for key in allowed_fields:
            if key in data:
                if key == "cash_balance":
                    setattr(portfolio, key, Decimal(str(data[key])))
                else:
                    setattr(portfolio, key, data[key])

        portfolio.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(portfolio)
        return portfolio

    async def delete_portfolio(
        self, db: AsyncSession, portfolio_id: str, user_id: str
    ) -> bool:
        """Soft delete portfolio"""
        portfolio = await self.get_portfolio(db, portfolio_id, user_id)
        if not portfolio:
            return False
        portfolio.is_active = False
        portfolio.updated_at = datetime.now(timezone.utc)
        await db.commit()
        logger.logger.info("Deleted portfolio %s", portfolio_id)
        return True

    async def add_holding(
        self, db: AsyncSession, portfolio_id: str, user_id: str, holding_data: Dict[str, Any]
    ) -> Optional[PortfolioHolding]:
        """Add holding to portfolio"""
        portfolio = await self.get_portfolio(db, portfolio_id, user_id)
        if not portfolio:
            return None

        symbol = holding_data["symbol"].upper()
        purchase_date = holding_data.get("purchase_date")
        if isinstance(purchase_date, str):
            purchase_date = date.fromisoformat(purchase_date)
        elif not purchase_date:
            purchase_date = date.today()

        # Check if holding already exists for this symbol
        existing = None
        for h in portfolio.holdings:
            if h.symbol == symbol:
                existing = h
                break

        if existing:
            # Average in: update shares and average cost
            old_total = existing.shares * existing.average_cost
            new_shares = Decimal(str(holding_data["quantity"]))
            new_price = Decimal(str(holding_data["purchase_price"]))
            new_total = new_shares * new_price
            total_shares = existing.shares + new_shares
            existing.average_cost = (old_total + new_total) / total_shares
            existing.shares = total_shares
            existing.last_purchase_date = purchase_date
            await db.commit()
            await db.refresh(existing)
            return existing

        # New holding — we need a company_id. Use a placeholder if not provided.
        company_id = holding_data.get("company_id")
        if not company_id:
            from app.models.company import Company
            stmt = select(Company).where(Company.symbol == symbol)
            result = await db.execute(stmt)
            company = result.scalar_one_or_none()
            if company:
                company_id = company.id
            else:
                # Create minimal company record
                company = Company(
                    id=uuid4(),
                    symbol=symbol,
                    name=f"Company {symbol}",
                    exchange="UNKNOWN",
                    is_active=True,
                )
                db.add(company)
                await db.flush()
                company_id = company.id

        holding = PortfolioHolding(
            id=uuid4(),
            portfolio_id=portfolio.id if isinstance(portfolio.id, UUID) else UUID(portfolio.id),
            company_id=company_id if isinstance(company_id, UUID) else UUID(company_id),
            symbol=symbol,
            shares=Decimal(str(holding_data["quantity"])),
            average_cost=Decimal(str(holding_data["purchase_price"])),
            current_price=Decimal(str(holding_data.get("current_price", holding_data["purchase_price"]))),
            first_purchase_date=purchase_date,
            last_purchase_date=purchase_date,
        )
        db.add(holding)
        await db.commit()
        await db.refresh(holding)

        # Recalculate portfolio value
        await self._recalculate_portfolio_value(db, portfolio)

        return holding

    async def remove_holding(
        self, db: AsyncSession, portfolio_id: str, user_id: str, holding_id: str
    ) -> bool:
        """Remove holding from portfolio"""
        portfolio = await self.get_portfolio(db, portfolio_id, user_id)
        if not portfolio:
            return False

        hid = holding_id if isinstance(holding_id, UUID) else UUID(holding_id)
        stmt = select(PortfolioHolding).where(
            and_(PortfolioHolding.id == hid, PortfolioHolding.portfolio_id == portfolio.id)
        )
        result = await db.execute(stmt)
        holding = result.scalar_one_or_none()
        if not holding:
            return False

        await db.delete(holding)
        await db.commit()

        await self._recalculate_portfolio_value(db, portfolio)
        return True

    async def update_holding(
        self, db: AsyncSession, portfolio_id: str, user_id: str, holding_id: str, update_data: Dict[str, Any]
    ) -> Optional[PortfolioHolding]:
        """Update holding in portfolio"""
        portfolio = await self.get_portfolio(db, portfolio_id, user_id)
        if not portfolio:
            return None

        hid = holding_id if isinstance(holding_id, UUID) else UUID(holding_id)
        stmt = select(PortfolioHolding).where(
            and_(PortfolioHolding.id == hid, PortfolioHolding.portfolio_id == portfolio.id)
        )
        result = await db.execute(stmt)
        holding = result.scalar_one_or_none()
        if not holding:
            return None

        allowed_fields = ["shares", "current_price"]
        for field in allowed_fields:
            if field in update_data:
                setattr(holding, field, Decimal(str(update_data[field])))

        holding.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(holding)

        await self._recalculate_portfolio_value(db, portfolio)
        return holding

    async def get_portfolio_performance(
        self, db: AsyncSession, portfolio_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get portfolio performance metrics"""
        portfolio = await self.get_portfolio(db, portfolio_id, user_id)
        if not portfolio:
            return None

        total_invested = sum(h.shares * h.average_cost for h in portfolio.holdings)
        current_value = sum(
            h.shares * h.current_price for h in portfolio.holdings if h.current_price
        )
        gain_loss = current_value - total_invested
        gain_loss_pct = (gain_loss / total_invested * 100) if total_invested > 0 else Decimal("0.00")

        return {
            "portfolio_id": str(portfolio.id),
            "total_invested": float(total_invested),
            "current_value": float(current_value),
            "cash_balance": float(portfolio.cash_balance),
            "total_portfolio_value": float(current_value + portfolio.cash_balance),
            "gain_loss": float(gain_loss),
            "gain_loss_percentage": float(gain_loss_pct),
            "number_of_holdings": len(portfolio.holdings),
        }

    async def get_portfolio_with_holdings(
        self, db: AsyncSession, portfolio_id: str, user_id: str
    ) -> Optional[Portfolio]:
        """Get portfolio with holdings"""
        return await self.get_portfolio(db, portfolio_id, user_id)

    async def _recalculate_portfolio_value(
        self, db: AsyncSession, portfolio: Portfolio
    ) -> None:
        """Recalculate portfolio total value from holdings"""
        stmt = select(PortfolioHolding).where(
            PortfolioHolding.portfolio_id == portfolio.id
        )
        result = await db.execute(stmt)
        holdings = list(result.scalars().all())

        holdings_value = sum(
            h.shares * (h.current_price or h.average_cost) for h in holdings
        )
        portfolio.total_value = holdings_value + portfolio.cash_balance
        portfolio.updated_at = datetime.now(timezone.utc)
        await db.commit()


# Global instance
portfolio_service = PortfolioService()

# Module-level functions for backward compatibility
async def create_portfolio(db: AsyncSession, user_id: str, portfolio_data: Dict[str, Any]) -> Portfolio:
    return await portfolio_service.create_portfolio(db, user_id, portfolio_data)

async def get_portfolio(db: AsyncSession, portfolio_id: str, user_id: str) -> Optional[Portfolio]:
    return await portfolio_service.get_portfolio(db, portfolio_id, user_id)

async def get_portfolios(db: AsyncSession, user_id: str) -> List[Portfolio]:
    return await portfolio_service.get_portfolios(db, user_id)

async def get_portfolios_paginated(db: AsyncSession, user_id: str, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
    return await portfolio_service.get_portfolios_paginated(db, user_id, skip, limit)

async def update_portfolio(db: AsyncSession, portfolio_id: str, user_id: str, update_data: Dict[str, Any]) -> Optional[Portfolio]:
    return await portfolio_service.update_portfolio(db, portfolio_id, user_id, update_data)

async def delete_portfolio(db: AsyncSession, portfolio_id: str, user_id: str) -> bool:
    return await portfolio_service.delete_portfolio(db, portfolio_id, user_id)

async def add_holding(db: AsyncSession, portfolio_id: str, user_id: str, holding_data: Dict[str, Any]) -> Optional[PortfolioHolding]:
    return await portfolio_service.add_holding(db, portfolio_id, user_id, holding_data)

async def get_portfolio_with_holdings(db: AsyncSession, portfolio_id: str, user_id: str) -> Optional[Portfolio]:
    return await portfolio_service.get_portfolio_with_holdings(db, portfolio_id, user_id)
