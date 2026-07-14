"""
Locust load testing suite for the RNR Financial Analysis Platform.

Targets:
  - 10,000 concurrent users
  - 50ms average API response time
  - <1% error rate under load

Run:
  locust -f infrastructure/load_testing/locustfile.py --host=http://localhost:8000

Dashboard: http://localhost:8089
"""
import json
import random
import time
from locust import HttpUser, task, between, events, tag
from locust.runners import MasterRunner, WorkerRunner


# Sample test data
SAMPLE_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM",
    "V", "JNJ", "WMT", "PG", "UNH", "MA", "HD", "DIS", "PYPL",
    "BAC", "ADBE", "CRM", "NFLX", "CMCSA", "XOM", "PFE", "TMO",
]

SAMPLE_PORTFOLIOS = [
    {"AAPL": 0.25, "MSFT": 0.20, "GOOGL": 0.15, "AMZN": 0.15, "NVDA": 0.25},
    {"JPM": 0.30, "V": 0.25, "MA": 0.25, "BAC": 0.20},
    {"JNJ": 0.20, "UNH": 0.20, "PFE": 0.20, "TMO": 0.20, "PG": 0.20},
]


class PlatformUser(HttpUser):
    """Simulates a typical platform user behavior."""

    wait_time = between(1, 5)
    abstract = True

    def on_start(self):
        """Authenticate at the start of each simulated user session."""
        self.token = None
        self.headers = {}
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "loadtest@example.com",
                "password": "LoadTest123!",
            },
            name="/api/v1/auth/login",
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token") or data.get("token")
            if self.token:
                self.headers = {"Authorization": f"Bearer {self.token}"}

    def _get(self, path: str, name: str = None, **kwargs):
        return self.client.get(
            path,
            headers=self.headers,
            name=name or path,
            **kwargs,
        )


class ReadOnlyUser(PlatformUser):
    """User who only reads data — highest traffic pattern."""

    weight = 5

    @task(10)
    @tag("read", "companies")
    def get_companies(self):
        symbol = random.choice(SAMPLE_SYMBOLS)
        self._get(f"/api/v1/companies?symbol={symbol}", name="/api/v1/companies")

    @task(8)
    @tag("read", "market-data")
    def get_market_data(self):
        symbol = random.choice(SAMPLE_SYMBOLS)
        self._get(f"/api/v1/market-data/{symbol}", name="/api/v1/market-data/[symbol]")

    @task(5)
    @tag("read", "financials")
    def get_financial_statements(self):
        symbol = random.choice(SAMPLE_SYMBOLS)
        self._get(f"/api/v1/financial-statements/{symbol}", name="/api/v1/financial-statements/[symbol]")

    @task(4)
    @tag("read", "screener")
    def run_screener(self):
        self._get("/api/v1/screener?sector=Technology&min_market_cap=1000000000",
                   name="/api/v1/screener")

    @task(3)
    @tag("read", "technical")
    def get_technical_analysis(self):
        symbol = random.choice(SAMPLE_SYMBOLS)
        self._get(f"/api/v1/technical-analysis/{symbol}?indicators=sma,rsi,macd",
                   name="/api/v1/technical-analysis/[symbol]")

    @task(2)
    @tag("read", "sentiment")
    def get_sentiment(self):
        symbol = random.choice(SAMPLE_SYMBOLS)
        self._get(f"/api/v1/sentiment/{symbol}", name="/api/v1/sentiment/[symbol]")


class ActiveTrader(PlatformUser):
    """User who actively manages portfolios and trades."""

    weight = 2

    @task(6)
    @tag("read", "portfolio")
    def get_portfolio(self):
        self._get("/api/v1/portfolios", name="/api/v1/portfolios")

    @task(5)
    @tag("read", "analytics")
    def get_analytics(self):
        self._get("/api/v1/analytics/overview", name="/api/v1/analytics/overview")

    @task(4)
    @tag("read", "risk")
    def get_risk_assessment(self):
        self._get("/api/v1/risk/assessment", name="/api/v1/risk/assessment")

    @task(3)
    @tag("write", "trade")
    def paper_trade(self):
        symbol = random.choice(SAMPLE_SYMBOLS)
        self.client.post(
            "/api/v1/paper-trading/orders",
            json={
                "symbol": symbol,
                "side": random.choice(["buy", "sell"]),
                "quantity": random.randint(1, 100),
                "order_type": "market",
            },
            headers=self.headers,
            name="/api/v1/paper-trading/orders",
        )

    @task(2)
    @tag("read", "backtesting")
    def run_backtest(self):
        self.client.post(
            "/api/v1/backtesting/run",
            json={
                "symbol": random.choice(SAMPLE_SYMBOLS),
                "strategy": "sma_crossover",
                "start_date": "2024-01-01",
                "end_date": "2025-01-01",
            },
            headers=self.headers,
            name="/api/v1/backtesting/run",
        )


class PowerUser(PlatformUser):
    """Heavy user — hits ML, optimization, and reporting endpoints."""

    weight = 1

    @task(5)
    @tag("compute", "ml")
    def get_ml_prediction(self):
        symbol = random.choice(SAMPLE_SYMBOLS)
        self._get(f"/api/v1/analytics/ml/predict/{symbol}?days_ahead=30",
                   name="/api/v1/analytics/ml/predict/[symbol]")

    @task(4)
    @tag("compute", "optimization")
    def optimize_portfolio(self):
        portfolio = random.choice(SAMPLE_PORTFOLIOS)
        self.client.post(
            "/api/v1/portfolio-optimization/optimize",
            json={"holdings": portfolio, "risk_tolerance": 0.5},
            headers=self.headers,
            name="/api/v1/portfolio-optimization/optimize",
        )

    @task(3)
    @tag("compute", "report")
    def generate_report(self):
        self.client.post(
            "/api/v1/reports/generate",
            json={
                "type": "portfolio_summary",
                "format": "json",
            },
            headers=self.headers,
            name="/api/v1/reports/generate",
        )

    @task(2)
    @tag("read", "monitoring")
    def get_performance_stats(self):
        self._get("/health/performance", name="/health/performance")


# --- Event listeners for custom metrics ---

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track requests that exceed the 50ms target."""
    if exception is None and response_time > 50:
        # Locust logs this automatically, but we can add custom handling
        pass


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary stats after test."""
    if isinstance(environment.runner, (MasterRunner, WorkerRunner)):
        return

    stats = environment.stats
    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)
    print(f"Total requests:  {stats.total.num_requests}")
    print(f"Total failures:  {stats.total.num_failures}")
    print(f"Error rate:      {stats.total.fail_ratio * 100:.1f}%")
    print(f"Median RT:       {stats.total.median_response_time:.1f}ms")
    print(f"95th %ile RT:    {stats.total.get_response_time_percentile(0.95):.1f}ms")
    print(f"99th %ile RT:    {stats.total.get_response_time_percentile(0.99):.1f}ms")
    print(f"Avg RT:          {stats.total.avg_response_time:.1f}ms")
    print(f"RPS:             {stats.total.total_rps:.1f}")

    if stats.total.avg_response_time > 50:
        print(f"\n⚠  Average response time ({stats.total.avg_response_time:.0f}ms) exceeds 50ms target!")
    else:
        print(f"\n✓  Average response time meets 50ms target!")

    if stats.total.fail_ratio > 0.01:
        print(f"⚠  Error rate ({stats.total.fail_ratio * 100:.1f}%) exceeds 1% threshold!")
    else:
        print(f"✓  Error rate within 1% threshold!")

    print("=" * 60 + "\n")
