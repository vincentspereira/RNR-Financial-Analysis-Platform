"""
Analytics Service - Portfolio and Financial Analytics
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import statistics
import math


class AnalyticsService:
    """Service for portfolio and financial analytics"""
    
    def __init__(self):
        """Initialize analytics service"""
        pass
    
    async def calculate_portfolio_performance(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive portfolio performance metrics"""
        if not portfolio or not portfolio.get("holdings"):
            return {
                "total_value": 0.0,
                "total_gain_loss": 0.0,
                "total_gain_loss_percentage": 0.0,
                "daily_change": 0.0,
                "daily_change_percentage": 0.0,
                "holdings_count": 0,
                "diversification_score": 0.0,
                "risk_score": 0.0
            }
        
        holdings = portfolio["holdings"]
        total_invested = sum(
            Decimal(str(holding["quantity"])) * Decimal(str(holding["purchase_price"]))
            for holding in holdings
        )
        
        current_value = sum(
            Decimal(str(holding["quantity"])) * Decimal(str(holding["current_price"]))
            for holding in holdings
        )
        
        gain_loss = current_value - total_invested
        gain_loss_percentage = (gain_loss / total_invested * 100) if total_invested > 0 else Decimal("0.00")
        
        # Calculate diversification score (simplified)
        unique_symbols = len(set(holding["symbol"] for holding in holdings))
        diversification_score = min(unique_symbols / 10.0, 1.0) * 100  # Max score at 10+ holdings
        
        # Calculate risk score (simplified volatility measure)
        if len(holdings) > 1:
            prices = [float(holding["current_price"]) for holding in holdings]
            price_variance = statistics.variance(prices) if len(prices) > 1 else 0
            risk_score = min(math.sqrt(price_variance) / statistics.mean(prices) * 100, 100) if statistics.mean(prices) > 0 else 0
        else:
            risk_score = 50.0  # Medium risk for single holding
        
        return {
            "total_value": float(current_value),
            "total_invested": float(total_invested),
            "total_gain_loss": float(gain_loss),
            "total_gain_loss_percentage": float(gain_loss_percentage),
            "daily_change": float(gain_loss * Decimal("0.01")),  # Mock daily change
            "daily_change_percentage": float(gain_loss_percentage * Decimal("0.01")),
            "holdings_count": len(holdings),
            "diversification_score": diversification_score,
            "risk_score": risk_score,
            "cash_balance": float(portfolio.get("cash_balance", 0)),
            "total_portfolio_value": float(current_value + Decimal(str(portfolio.get("cash_balance", 0))))
        }
    
    async def get_comprehensive_analysis(self, portfolio_id: str) -> Dict[str, Any]:
        """Get comprehensive portfolio analysis"""
        # Mock comprehensive analysis
        return {
            "portfolio_id": portfolio_id,
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "performance_metrics": {
                "total_return": 15.5,
                "annualized_return": 12.3,
                "volatility": 18.2,
                "sharpe_ratio": 0.85,
                "max_drawdown": -8.5,
                "beta": 1.1
            },
            "risk_metrics": {
                "var_95": -5.2,  # Value at Risk 95%
                "cvar_95": -7.8,  # Conditional VaR 95%
                "risk_score": 65,
                "risk_level": "moderate"
            },
            "allocation_analysis": {
                "sector_allocation": {
                    "Technology": 35.0,
                    "Healthcare": 20.0,
                    "Finance": 15.0,
                    "Consumer": 20.0,
                    "Other": 10.0
                },
                "asset_allocation": {
                    "Stocks": 85.0,
                    "Bonds": 10.0,
                    "Cash": 5.0
                }
            },
            "recommendations": [
                "Consider rebalancing to reduce technology exposure",
                "Add more defensive positions to reduce volatility",
                "Increase cash position for upcoming opportunities"
            ],
            "next_review_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }
    
    async def calculate_risk_metrics(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate portfolio risk metrics"""
        if not portfolio or not portfolio.get("holdings"):
            return {
                "var_95": 0.0,
                "cvar_95": 0.0,
                "volatility": 0.0,
                "beta": 1.0,
                "risk_score": 0.0,
                "risk_level": "low"
            }
        
        holdings = portfolio["holdings"]
        
        # Simplified risk calculations
        total_value = sum(
            Decimal(str(holding["quantity"])) * Decimal(str(holding["current_price"]))
            for holding in holdings
        )
        
        # Mock volatility calculation
        volatility = min(len(holdings) * 2.5, 25.0)  # Higher with more holdings, capped at 25%
        
        # Mock VaR calculation (5% worst case scenario)
        var_95 = float(total_value) * -0.05 * (volatility / 20.0)
        cvar_95 = var_95 * 1.5  # Conditional VaR typically 1.5x VaR
        
        # Risk score based on volatility
        risk_score = min(volatility * 3, 100)
        
        if risk_score < 30:
            risk_level = "low"
        elif risk_score < 70:
            risk_level = "moderate"
        else:
            risk_level = "high"
        
        return {
            "var_95": var_95,
            "cvar_95": cvar_95,
            "volatility": volatility,
            "beta": 1.0 + (volatility - 15) / 100,  # Mock beta calculation
            "risk_score": risk_score,
            "risk_level": risk_level
        }
    
    async def get_performance_attribution(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """Get performance attribution analysis"""
        if not portfolio or not portfolio.get("holdings"):
            return {
                "total_return": 0.0,
                "security_selection": 0.0,
                "asset_allocation": 0.0,
                "interaction_effect": 0.0,
                "top_contributors": [],
                "top_detractors": []
            }
        
        holdings = portfolio["holdings"]
        
        # Mock performance attribution
        contributors = []
        detractors = []
        
        for holding in holdings:
            quantity = Decimal(str(holding["quantity"]))
            purchase_price = Decimal(str(holding["purchase_price"]))
            current_price = Decimal(str(holding["current_price"]))
            
            gain_loss = (current_price - purchase_price) * quantity
            contribution = float(gain_loss)
            
            holding_perf = {
                "symbol": holding["symbol"],
                "contribution": contribution,
                "weight": float(quantity * current_price),
                "return": float((current_price - purchase_price) / purchase_price * 100)
            }
            
            if contribution > 0:
                contributors.append(holding_perf)
            else:
                detractors.append(holding_perf)
        
        # Sort by contribution
        contributors.sort(key=lambda x: x["contribution"], reverse=True)
        detractors.sort(key=lambda x: x["contribution"])
        
        total_return = sum(h["contribution"] for h in contributors + detractors)
        
        return {
            "total_return": total_return,
            "security_selection": total_return * 0.7,  # Mock attribution
            "asset_allocation": total_return * 0.2,
            "interaction_effect": total_return * 0.1,
            "top_contributors": contributors[:5],
            "top_detractors": detractors[:5]
        }
    
    async def generate_portfolio_report(self, portfolio_id: str) -> Dict[str, Any]:
        """Generate comprehensive portfolio report"""
        return {
            "report_id": f"report_{portfolio_id}_{int(datetime.now(timezone.utc).timestamp())}",
            "portfolio_id": portfolio_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_type": "comprehensive",
            "sections": {
                "executive_summary": {
                    "total_value": 125000.00,
                    "total_return": 15.5,
                    "risk_level": "moderate",
                    "recommendation": "maintain current allocation"
                },
                "performance": {
                    "ytd_return": 12.3,
                    "one_year_return": 15.5,
                    "three_year_return": 8.7,
                    "inception_return": 11.2
                },
                "holdings": {
                    "count": 15,
                    "top_holdings": [
                        {"symbol": "AAPL", "weight": 8.5},
                        {"symbol": "MSFT", "weight": 7.2},
                        {"symbol": "GOOGL", "weight": 6.8}
                    ]
                },
                "risk_analysis": {
                    "volatility": 18.2,
                    "sharpe_ratio": 0.85,
                    "max_drawdown": -8.5
                }
            },
            "charts": {
                "performance_chart": "base64_encoded_chart_data",
                "allocation_chart": "base64_encoded_chart_data",
                "risk_chart": "base64_encoded_chart_data"
            }
        }


# Global instance
analytics_service = AnalyticsService()