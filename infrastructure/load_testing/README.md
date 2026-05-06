# Load Testing Infrastructure

## Setup

```bash
pip install locust
```

## Run

### Quick smoke test (10 users)
```bash
locust -f infrastructure/load_testing/locustfile.py --host=http://localhost:8000 -u 10 -r 2 --headless -t 60s
```

### Medium test (1,000 users)
```bash
locust -f infrastructure/load_testing/locustfile.py --host=http://localhost:8000 -u 1000 -r 50 --headless -t 5m
```

### Full scale test (10,000 users)
```bash
locust -f infrastructure/load_testing/locustfile.py --host=http://localhost:8000 -u 10000 -r 200 --headless -t 10m
```

### Distributed mode (for large-scale tests)
```bash
# Master node
locust -f infrastructure/load_testing/locustfile.py --master --host=http://localhost:8000

# Worker nodes (run on separate machines/containers)
locust -f infrastructure/load_testing/locustfile.py --worker --master-host=<master-ip>
```

### Web UI
```bash
locust -f infrastructure/load_testing/locustfile.py --host=http://localhost:8000
# Open http://localhost:8089
```

## Targets

| Metric | Target | Acceptable |
|--------|--------|-----------|
| Avg response time | <50ms | <100ms |
| P95 response time | <100ms | <200ms |
| P99 response time | <200ms | <500ms |
| Error rate | <0.1% | <1% |
| Throughput | >10K RPS | >5K RPS |

## User Profiles

| Profile | Weight | Behavior |
|---------|--------|----------|
| ReadOnlyUser | 5 | Browsing companies, market data, financials |
| ActiveTrader | 2 | Portfolio management, paper trading, analytics |
| PowerUser | 1 | ML predictions, optimization, reports |

## Tags

Filter tests by tag:
```bash
locust --tags read          # Only read endpoints
locust --tags compute       # Only compute-heavy endpoints
locust --tags write         # Only write endpoints
locust --exclude-tags compute  # Everything except compute
```
