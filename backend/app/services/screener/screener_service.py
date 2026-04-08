"""
Stock screener service for filtering and screening stocks.

Provides preset screeners, custom filtering, and stock data generation.
"""
import hashlib
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.core.logging import get_logger
from app.schemas.screener import ScreenerFilter, ScreenerResult, PresetScreener

logger = get_logger("app.services.screener")

# Sector list
SECTORS = [
    "Technology", "Healthcare", "Financials", "Consumer Discretionary",
    "Consumer Staples", "Energy", "Industrials", "Materials",
    "Real Estate", "Utilities", "Communication Services",
]

EXCHANGES = ["NYSE", "NASDAQ", "AMEX"]

# Generate realistic mock stock data
MOCK_STOCKS: List[Dict[str, Any]] = []

_STOCK_DATA = [
    ("AAPL", "Apple Inc.", "Technology", 2800000000000, 175.0, 28.5, 0.55),
    ("MSFT", "Microsoft Corporation", "Technology", 2500000000000, 420.0, 35.2, 0.82),
    ("GOOGL", "Alphabet Inc.", "Communication Services", 1700000000000, 140.0, 25.1, 0.0),
    ("AMZN", "Amazon.com Inc.", "Consumer Discretionary", 1600000000000, 185.0, 62.3, 0.0),
    ("NVDA", "NVIDIA Corporation", "Technology", 1200000000000, 450.0, 65.8, 0.04),
    ("META", "Meta Platforms Inc.", "Communication Services", 900000000000, 480.0, 26.4, 0.50),
    ("TSLA", "Tesla Inc.", "Consumer Discretionary", 800000000000, 250.0, 78.2, 0.0),
    ("BRK.B", "Berkshire Hathaway Inc.", "Financials", 750000000000, 360.0, 8.5, 0.0),
    ("JPM", "JPMorgan Chase & Co.", "Financials", 500000000000, 195.0, 11.2, 2.50),
    ("V", "Visa Inc.", "Financials", 480000000000, 275.0, 30.1, 0.75),
    ("UNH", "UnitedHealth Group", "Healthcare", 450000000000, 520.0, 22.5, 1.35),
    ("JNJ", "Johnson & Johnson", "Healthcare", 400000000000, 155.0, 10.8, 3.05),
    ("WMT", "Walmart Inc.", "Consumer Staples", 380000000000, 165.0, 28.3, 1.45),
    ("XOM", "Exxon Mobil Corporation", "Energy", 420000000000, 105.0, 9.2, 3.60),
    ("PG", "Procter & Gamble Co.", "Consumer Staples", 350000000000, 160.0, 24.5, 2.45),
    ("MA", "Mastercard Inc.", "Financials", 370000000000, 460.0, 34.8, 0.55),
    ("HD", "The Home Depot Inc.", "Consumer Discretionary", 330000000000, 345.0, 23.1, 2.40),
    ("CVX", "Chevron Corporation", "Energy", 280000000000, 155.0, 10.5, 4.00),
    ("ABBV", "AbbVie Inc.", "Healthcare", 260000000000, 165.0, 16.2, 3.85),
    ("PFE", "Pfizer Inc.", "Healthcare", 160000000000, 28.0, 32.5, 5.80),
    ("BA", "The Boeing Company", "Industrials", 120000000000, 200.0, -15.2, 0.0),
    ("DIS", "The Walt Disney Co.", "Communication Services", 170000000000, 95.0, 72.3, 0.0),
    ("NFLX", "Netflix Inc.", "Communication Services", 220000000000, 620.0, 48.5, 0.0),
    ("INTC", "Intel Corporation", "Technology", 130000000000, 31.0, 85.5, 1.20),
    ("CSCO", "Cisco Systems Inc.", "Technology", 190000000000, 48.0, 15.3, 3.10),
    ("PEP", "PepsiCo Inc.", "Consumer Staples", 230000000000, 175.0, 25.1, 2.90),
    ("KO", "The Coca-Cola Co.", "Consumer Staples", 260000000000, 60.0, 23.8, 3.10),
    ("NKE", "Nike Inc.", "Consumer Discretionary", 150000000000, 98.0, 30.2, 1.35),
    ("MRK", "Merck & Co. Inc.", "Healthcare", 280000000000, 115.0, 18.5, 2.70),
    ("TMO", "Thermo Fisher Scientific", "Healthcare", 200000000000, 570.0, 32.1, 0.28),
    ("COST", "Costco Wholesale Corp.", "Consumer Staples", 300000000000, 720.0, 48.5, 0.55),
    ("AVGO", "Broadcom Inc.", "Technology", 550000000000, 1300.0, 28.3, 1.50),
    ("TXN", "Texas Instruments Inc.", "Technology", 170000000000, 175.0, 22.1, 2.55),
    ("LLY", "Eli Lilly and Company", "Healthcare", 700000000000, 780.0, 120.5, 0.75),
    ("ORCL", "Oracle Corporation", "Technology", 330000000000, 125.0, 36.2, 1.40),
    ("CRM", "Salesforce Inc.", "Technology", 250000000000, 275.0, 58.3, 0.55),
    ("ADBE", "Adobe Inc.", "Technology", 240000000000, 580.0, 42.1, 0.0),
    ("AMD", "Advanced Micro Devices", "Technology", 220000000000, 170.0, 280.0, 0.0),
    ("BMY", "Bristol-Myers Squibb", "Healthcare", 100000000000, 52.0, 22.8, 4.50),
    ("NEE", "NextEra Energy Inc.", "Utilities", 150000000000, 65.0, 21.3, 2.85),
    ("LIN", "Linde plc", "Materials", 180000000000, 420.0, 28.5, 1.25),
    ("PM", "Philip Morris International", "Consumer Staples", 160000000000, 95.0, 16.8, 5.20),
    ("UPS", "United Parcel Service", "Industrials", 130000000000, 150.0, 18.5, 3.80),
    ("RTX", "RTX Corporation", "Industrials", 120000000000, 90.0, 22.1, 2.45),
    ("T", "AT&T Inc.", "Communication Services", 120000000000, 17.0, 8.5, 6.50),
    ("VZ", "Verizon Communications", "Communication Services", 160000000000, 40.0, 8.2, 6.80),
    ("GS", "Goldman Sachs Group", "Financials", 140000000000, 470.0, 15.8, 2.60),
    ("CAT", "Caterpillar Inc.", "Industrials", 160000000000, 340.0, 16.2, 1.70),
    ("DE", "Deere & Company", "Industrials", 110000000000, 385.0, 18.5, 1.45),
    ("SQ", "Block Inc.", "Technology", 40000000000, 75.0, 85.2, 0.0),
]

for symbol, name, sector, mcap, price, pe, div_yield in _STOCK_DATA:
    _r = random.Random(hashlib.md5(symbol.encode()).hexdigest()[:8])
    MOCK_STOCKS.append({
        "symbol": symbol,
        "company_name": name,
        "sector": sector,
        "exchange": _r.choice(EXCHANGES),
        "market_cap": mcap,
        "price": price,
        "pe_ratio": pe if pe > 0 else None,
        "dividend_yield": div_yield if div_yield > 0 else None,
        "price_change_1d": round(_r.uniform(-5, 5), 2),
        "price_change_1y": round(_r.uniform(-30, 60), 2),
        "volume": _r.randint(1000000, 50000000),
    })


# Preset screeners
PRESET_SCREENERS: Dict[str, PresetScreener] = {
    "value": PresetScreener(
        name="Value Stocks",
        description="Low P/E ratio with high dividend yield - classic value investing",
        filters=ScreenerFilter(pe_ratio_max=15, dividend_yield_min=2, sort_by="pe_ratio", sort_order="asc"),
    ),
    "growth": PresetScreener(
        name="Growth Stocks",
        description="Companies with high revenue growth potential",
        filters=ScreenerFilter(revenue_growth_min=20, sort_by="market_cap", sort_order="desc"),
    ),
    "dividend": PresetScreener(
        name="High Dividend",
        description="Stocks with dividend yield above 3%",
        filters=ScreenerFilter(dividend_yield_min=3, sort_by="dividend_yield", sort_order="desc"),
    ),
    "momentum": PresetScreener(
        name="Momentum",
        description="Strong 1-year price performance",
        filters=ScreenerFilter(price_change_1y_min=20, sort_by="price_change_1y", sort_order="desc"),
    ),
    "undervalued": PresetScreener(
        name="Undervalued",
        description="Low P/E ratio indicating potential undervaluation",
        filters=ScreenerFilter(pe_ratio_max=12, sort_by="pe_ratio", sort_order="asc"),
    ),
    "large_cap": PresetScreener(
        name="Large Cap",
        description="Companies with market cap above $10B",
        filters=ScreenerFilter(market_cap_min=10000000000, sort_by="market_cap", sort_order="desc"),
    ),
}

# User saved screeners (in-memory)
_saved_screeners: Dict[str, List[Dict]] = {}


class ScreenerService:
    """Stock screening and filtering service."""

    def run_screener(self, filters: ScreenerFilter, preset_name: Optional[str] = None) -> Dict:
        """Apply filters to stock universe and return matching results."""
        results = []

        for stock in MOCK_STOCKS:
            score = 0.0
            matches = True

            if filters.market_cap_min and stock["market_cap"] < filters.market_cap_min:
                matches = False
            if filters.market_cap_max and stock["market_cap"] > filters.market_cap_max:
                matches = False
            if filters.sector and stock["sector"] not in filters.sector:
                matches = False
            if filters.pe_ratio_min is not None and (stock["pe_ratio"] is None or stock["pe_ratio"] < filters.pe_ratio_min):
                matches = False
            if filters.pe_ratio_max is not None and (stock["pe_ratio"] is None or stock["pe_ratio"] > filters.pe_ratio_max):
                matches = False
            if filters.dividend_yield_min is not None and (stock["dividend_yield"] is None or stock["dividend_yield"] < filters.dividend_yield_min):
                matches = False
            if filters.price_change_1y_min is not None and (stock["price_change_1y"] is None or stock["price_change_1y"] < filters.price_change_1y_min):
                matches = False
            if filters.revenue_growth_min is not None:
                mock_growth = random.uniform(0, 50)
                if mock_growth < filters.revenue_growth_min:
                    matches = False
            if filters.rsi_14_min is not None or filters.rsi_14_max is not None:
                rsi = random.uniform(20, 80)
                if filters.rsi_14_min is not None and rsi < filters.rsi_14_min:
                    matches = False
                if filters.rsi_14_max is not None and rsi > filters.rsi_14_max:
                    matches = False

            if not matches:
                continue

            # Calculate relevance score
            if stock["pe_ratio"] and stock["pe_ratio"] < 20:
                score += 20
            if stock["dividend_yield"] and stock["dividend_yield"] > 2:
                score += 15
            if stock["price_change_1y"] and stock["price_change_1y"] > 10:
                score += 20
            if stock["market_cap"] > 100000000000:
                score += 15
            score += random.uniform(0, 30)

            results.append(ScreenerResult(
                symbol=stock["symbol"],
                company_name=stock["company_name"],
                sector=stock["sector"],
                exchange=stock["exchange"],
                market_cap=stock["market_cap"],
                price=stock["price"],
                pe_ratio=stock["pe_ratio"],
                dividend_yield=stock["dividend_yield"],
                price_change_1d=stock["price_change_1d"],
                price_change_1y=stock["price_change_1y"],
                volume=stock["volume"],
                score=round(score, 1),
            ))

        # Sort results
        sort_field = filters.sort_by
        reverse = filters.sort_order == "desc"
        results.sort(
            key=lambda x: getattr(x, sort_field, 0) or 0,
            reverse=reverse,
        )

        total = len(results)
        results = results[:filters.limit]

        return {
            "total_results": total,
            "results": results,
            "preset_name": preset_name,
        }

    def get_presets(self) -> List[PresetScreener]:
        """Get all preset screeners."""
        return list(PRESET_SCREENERS.values())

    def get_preset(self, name: str) -> Optional[PresetScreener]:
        """Get a specific preset screener."""
        return PRESET_SCREENERS.get(name)

    def save_screener(self, user_id: str, name: str, filters: ScreenerFilter) -> Dict:
        """Save a custom screener for a user."""
        screener_id = str(uuid4())
        if user_id not in _saved_screeners:
            _saved_screeners[user_id] = []
        _saved_screeners[user_id].append({
            "id": screener_id,
            "name": name,
            "filters": filters.model_dump(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"id": screener_id, "name": name, "message": "Screener saved successfully"}

    def get_user_screeners(self, user_id: str) -> List[Dict]:
        """Get all saved screeners for a user."""
        return _saved_screeners.get(user_id, [])

    def delete_screener(self, user_id: str, screener_id: str) -> bool:
        """Delete a saved screener."""
        if user_id in _saved_screeners:
            _saved_screeners[user_id] = [
                s for s in _saved_screeners[user_id] if s["id"] != screener_id
            ]
            return True
        return False


screener_service = ScreenerService()
