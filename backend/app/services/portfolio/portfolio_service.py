"""
Portfolio Service - Portfolio Management Operations
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal
import uuid


class PortfolioService:
    """Service for portfolio management operations"""
    
    def __init__(self):
        """Initialize portfolio service"""
        self.portfolios = {}  # In-memory storage for testing
    
    async def create_portfolio(self, user_id: str, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new portfolio"""
        portfolio_id = str(uuid.uuid4())
        portfolio = {
            "id": portfolio_id,
            "user_id": user_id,
            "name": portfolio_data.get("name", "My Portfolio"),
            "description": portfolio_data.get("description", ""),
            "total_value": Decimal("0.00"),
            "cash_balance": Decimal(portfolio_data.get("cash_balance", "0.00")),
            "holdings": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True
        }
        
        self.portfolios[portfolio_id] = portfolio
        return portfolio
    
    async def get_portfolio(self, portfolio_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get portfolio by ID"""
        portfolio = self.portfolios.get(portfolio_id)
        if portfolio and portfolio["user_id"] == user_id:
            return portfolio
        return None
    
    async def get_portfolios(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all portfolios for a user"""
        return [
            portfolio for portfolio in self.portfolios.values()
            if portfolio["user_id"] == user_id and portfolio["is_active"]
        ]
    
    async def get_portfolios_paginated(self, user_id: str, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Get paginated portfolios for a user"""
        user_portfolios = await self.get_portfolios(user_id)
        total = len(user_portfolios)
        portfolios = user_portfolios[skip:skip + limit]
        
        return {
            "portfolios": portfolios,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": skip + limit < total
        }
    
    async def update_portfolio(self, portfolio_id: str, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update portfolio"""
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None
        
        # Update allowed fields
        allowed_fields = ["name", "description", "cash_balance"]
        for field in allowed_fields:
            if field in update_data:
                portfolio[field] = update_data[field]
        
        portfolio["updated_at"] = datetime.now(timezone.utc).isoformat()
        return portfolio
    
    async def delete_portfolio(self, portfolio_id: str, user_id: str) -> bool:
        """Delete portfolio (soft delete)"""
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return False
        
        portfolio["is_active"] = False
        portfolio["updated_at"] = datetime.now(timezone.utc).isoformat()
        return True
    
    async def add_holding(self, portfolio_id: str, user_id: str, holding_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add holding to portfolio"""
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None
        
        holding = {
            "id": str(uuid.uuid4()),
            "symbol": holding_data["symbol"],
            "quantity": Decimal(str(holding_data["quantity"])),
            "purchase_price": Decimal(str(holding_data["purchase_price"])),
            "current_price": Decimal(str(holding_data.get("current_price", holding_data["purchase_price"]))),
            "purchase_date": holding_data.get("purchase_date", datetime.now(timezone.utc).isoformat()),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        portfolio["holdings"].append(holding)
        portfolio["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Recalculate total value
        await self._recalculate_portfolio_value(portfolio)
        
        return holding
    
    async def remove_holding(self, portfolio_id: str, user_id: str, holding_id: str) -> bool:
        """Remove holding from portfolio"""
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return False
        
        original_count = len(portfolio["holdings"])
        portfolio["holdings"] = [h for h in portfolio["holdings"] if h["id"] != holding_id]
        
        if len(portfolio["holdings"]) < original_count:
            portfolio["updated_at"] = datetime.now(timezone.utc).isoformat()
            await self._recalculate_portfolio_value(portfolio)
            return True
        
        return False
    
    async def update_holding(self, portfolio_id: str, user_id: str, holding_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update holding in portfolio"""
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None
        
        for holding in portfolio["holdings"]:
            if holding["id"] == holding_id:
                # Update allowed fields
                allowed_fields = ["quantity", "current_price"]
                for field in allowed_fields:
                    if field in update_data:
                        holding[field] = Decimal(str(update_data[field]))
                
                portfolio["updated_at"] = datetime.now(timezone.utc).isoformat()
                await self._recalculate_portfolio_value(portfolio)
                return holding
        
        return None
    
    async def get_portfolio_performance(self, portfolio_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get portfolio performance metrics"""
        portfolio = await self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None
        
        total_invested = sum(
            holding["quantity"] * holding["purchase_price"]
            for holding in portfolio["holdings"]
        )
        
        current_value = sum(
            holding["quantity"] * holding["current_price"]
            for holding in portfolio["holdings"]
        )
        
        gain_loss = current_value - total_invested
        gain_loss_percentage = (gain_loss / total_invested * 100) if total_invested > 0 else Decimal("0.00")
        
        return {
            "portfolio_id": portfolio_id,
            "total_invested": float(total_invested),
            "current_value": float(current_value),
            "cash_balance": float(portfolio["cash_balance"]),
            "total_portfolio_value": float(current_value + portfolio["cash_balance"]),
            "gain_loss": float(gain_loss),
            "gain_loss_percentage": float(gain_loss_percentage),
            "number_of_holdings": len(portfolio["holdings"])
        }
    
    async def get_portfolio_with_holdings(self, portfolio_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get portfolio with holdings (alias for get_portfolio)"""
        return await self.get_portfolio(portfolio_id, user_id)
    
    async def _recalculate_portfolio_value(self, portfolio: Dict[str, Any]) -> None:
        """Recalculate portfolio total value"""
        holdings_value = sum(
            holding["quantity"] * holding["current_price"]
            for holding in portfolio["holdings"]
        )
        
        portfolio["total_value"] = holdings_value + portfolio["cash_balance"]


# Global instance
portfolio_service = PortfolioService()

# Module-level functions for backward compatibility
async def create_portfolio(user_id: str, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new portfolio"""
    return await portfolio_service.create_portfolio(user_id, portfolio_data)

async def get_portfolio(portfolio_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get portfolio by ID"""
    return await portfolio_service.get_portfolio(portfolio_id, user_id)

async def get_portfolios(user_id: str) -> List[Dict[str, Any]]:
    """Get all portfolios for a user"""
    return await portfolio_service.get_portfolios(user_id)

async def get_portfolios_paginated(user_id: str, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
    """Get paginated portfolios for a user"""
    return await portfolio_service.get_portfolios_paginated(user_id, skip, limit)

async def update_portfolio(portfolio_id: str, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update portfolio"""
    return await portfolio_service.update_portfolio(portfolio_id, user_id, update_data)

async def delete_portfolio(portfolio_id: str, user_id: str) -> bool:
    """Delete portfolio"""
    return await portfolio_service.delete_portfolio(portfolio_id, user_id)

async def add_holding(portfolio_id: str, user_id: str, holding_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Add holding to portfolio"""
    return await portfolio_service.add_holding(portfolio_id, user_id, holding_data)

async def get_portfolio_with_holdings(portfolio_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get portfolio with holdings (alias for get_portfolio)"""
    return await portfolio_service.get_portfolio(portfolio_id, user_id)