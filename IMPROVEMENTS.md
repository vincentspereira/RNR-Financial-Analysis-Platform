# Prioritized Improvement Plan

**Last Updated:** 2026-05-21
**Scope:** Features rated "complete" today, looking forward 1–6 months.

Two columns:
- **Impact** = expected real benefit if shipped (Critical / High / Medium / Low).
- **Effort** = engineering work needed (S = ≤1 day, M = 1–5 days, L = 1–3 weeks).

Listed in execution order — earlier items unblock or amplify later ones.

---

## Tier 1 — Ship within 1 week (post-IBKR)

### I-1. Wire Sentry into the FastAPI app — **Impact:** High **Effort:** S

`.env.production` already has `SENTRY_DSN` placeholder; the code never reads it.
Add the snippet in `SECURITY.md §5` to `backend/app/main.py` so production
errors are captured. Without this, your first real bug after going live will be
invisible until a user complains.

### I-2. Replace the broken `venv/` with a working one — **Impact:** High **Effort:** S

Current `venv` points to `C:\Program Files\Python313\python.exe` which doesn't
exist. The user has Python 3.14 at `C:\Python314\python.exe`. Recreate:

```powershell
Remove-Item -Recurse -Force venv
C:\Python314\python.exe -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r backend\requirements.txt
```

Without this, no `pytest`, `alembic`, or `uvicorn` will run.

### I-3. Persist paper-trading state to DB — **Impact:** Medium **Effort:** M

`backend/app/services/paper_trading/trading_engine.py` uses module-level dicts.
Move to DB-backed `PaperPortfolio` / `PaperOrder` / `PaperTrade` tables (mirror
the `ibkr_orders` model). This survives backend restarts and unlocks
multi-user history.

**Or:** mark the in-memory simulator as deprecated in favor of IBKR and remove
it from the nav. Cleaner for a single-user platform.

### I-4. Pin Redis to ≤ 7.2.x in `docker-compose.prod.yml` — **Impact:** Low (today) High (MAS-day-0) **Effort:** S

Redis 7.4+ moved to SSPL (source-available, not OSS, not MAS-portable). Pin to
`redis:7.2-alpine` now to avoid a surprise dependency rip when you start MAS
integration.

### I-5. Compute paper-trading performance from real trade history — **Impact:** Low **Effort:** S

`trading_engine.py` lines 261-264 still return `hash(user_id)`-derived
`avg_win`, `avg_loss`, `best_trade`, `worst_trade`. With persistence (I-3) you
can compute these from actual fills.

---

## Tier 2 — Ship within 1 month

### I-6. Replace `yfinance` with a licensed market-data feed — **Impact:** Medium (commercial blocker) **Effort:** M

For your own personal use, `yfinance` is fine. For MAS commercialization, Yahoo
Finance's TOS prohibits commercial redistribution. Pick one:

- **Polygon.io paid tier** — $99/mo for stocks, includes real-time WS. Best
  fit since you already have a streamer for Polygon.
- **IEX Cloud** — pay-as-you-go. Cheaper for low-volume.
- **EOD Historical Data** — flat $19.99/mo, broad coverage.
- **Tradier Market Data** — bundled if you ever move execution to Tradier.
- **Alpha Vantage Premium** — $50/mo to $250/mo.

Abstract `backend/app/services/data/yahoo_finance_client.py` behind a
`MarketDataProvider` protocol so the swap is a one-file change.

### I-7. Add a "best-available quote" fallback chain — **Impact:** Medium **Effort:** M

Today, if Polygon WS drops, the streamer stops. Build a chain:
`PolygonWS -> PolygonREST -> IBKR snapshot -> cached`. Already partially
modeled in `subscription_manager.py`. Pair with I-6.

### I-8. Persist ML / DL models to disk — **Impact:** Medium **Effort:** M

`deep_learning_service.py` retrains on every prediction. Add a `data/models/`
registry: `data/models/<symbol>/<arch>/v<n>.pt` with mtime-based staleness
(retrain if >7 days old). Bonus: expose a `/api/v1/analytics/models` admin
endpoint to view registry contents.

### I-9. Add WebSocket Redis backplane — **Impact:** Medium **Effort:** M

`websocket_manager` is single-process today. Add Redis pub/sub so multi-replica
deploys broadcast correctly. Required before horizontal scaling — not before.

### I-10. Add notifications transport (SMTP + Web Push) — **Impact:** Medium **Effort:** M

`notification_service.py` writes to DB but never sends out-of-band alerts. Add:
- SMTP transport (config already exists in `.env.example`).
- Web Push API (free, browser-native, no Twilio fees).
- Per-user channel preferences table.

### I-11. Bring backend test coverage from ~5 tests to ≥ 50 — **Impact:** Medium **Effort:** L

Focus areas (highest blast-radius first):
- Auth service (login, refresh, lockout, RBAC)
- Financial calculator (ratios, DCF, DDM)
- IBKR safety gate (limits, day rollover, race conditions)
- Order manager (place, cancel, sync) with `ib_async` mocked.

---

## Tier 3 — Ship within 3 months

### I-12. Replace Grafana ≥ 8.0 (AGPL) — **Impact:** Low (today) Medium (MAS) **Effort:** M

Options listed in `LICENSES.md` Feature 20. Pick one before MAS public release.

### I-13. Add FinBERT to sentiment service — **Impact:** Low **Effort:** M

Boost sentiment accuracy from ~70% (VADER-style) to ~90% (FinBERT). Use the
PyTorch-optional pattern from `deep_learning_service.py`.

### I-14. Implement `cancel_order` for paper-trading market orders — **Impact:** Low **Effort:** S

Currently returns 501. With I-3 (persistence), this becomes trivial — just
mark the order cancelled before it fills.

### I-15. Add a "kill switch" admin endpoint — **Impact:** Medium **Effort:** S

`POST /api/v1/admin/kill-switch` that:
- Sets `IBKR_READONLY=true` in-memory (env override).
- Cancels all open IBKR orders for all users.
- Logs to audit.

Useful as a panic button when an algo goes rogue.

### I-16. Add a model-deployment guard for IBKR — **Impact:** Medium **Effort:** M

Add an `IBKRGuard` middleware: if any model output deviates >N standard
deviations from training distribution, AUTO-flip IBKR to read-only mode.
Pair with I-15.

### I-17. Audit log tamper detection — **Impact:** Medium **Effort:** M

`audit.py` already computes integrity hashes. Add a weekly background task
that walks the chain backwards and alerts on hash mismatches. SOX requires
this.

### I-18. Frontend test coverage ≥ 40% — **Impact:** Low **Effort:** L

Current frontend tests reference outdated APIs per the April review. Rewrite
against the current React Query patterns.

---

## Tier 4 — Strategic / Optional

### I-19. Multi-broker abstraction — **Impact:** Medium (MAS) **Effort:** L

Today `paper_trading` is in-memory and `ibkr` is IBKR-specific. Extract a
`BrokerAdapter` protocol with implementations for IBKR, Alpaca, Tradier,
TD Ameritrade (now Schwab API), Robinhood unofficial. MAS positioning play.

### I-20. Strategy authoring framework — **Impact:** Medium **Effort:** L

Today's backtesting engine has 6 hardcoded strategy types. Move to a
"user-defined strategy" model where users upload a Python function and the
backtester sandboxes it. Significant scope, but it's the natural extension
of the platform.

### I-21. Mobile app completeness — **Impact:** Low **Effort:** L

The graph shows mobile screens but the directory wasn't visible to me in this
sweep. Confirm whether the React Native app is functional or just stubs.

### I-22. Real-time portfolio P&L via IBKR — **Impact:** Medium **Effort:** M

Subscribe to IBKR's `accountUpdates` and `portfolio` events; push deltas via
WebSocket to the frontend. Today, account summary is polled every 15s.

### I-23. Tax-lot accounting — **Impact:** Medium (US tax) **Effort:** L

Wash-sale tracking, lot selection (FIFO/LIFO/specific-ID), and Form 8949
output. Real users will demand this come tax season.

### I-24. Documentation freshness — **Impact:** Low **Effort:** S

The April production-readiness review is outdated (~6 weeks). The recent
context (LICENSE, LICENSES.md, SECURITY.md, FEATURE_AUDIT.md, IBKR_SETUP.md
from this engagement) supersedes it. Consider archiving the older review
under `docs/archive/`.

---

## What I'd ship in the next 7 days (concrete)

If I had a week to spend on this codebase tomorrow morning, in priority order:

1. **Day 1 morning:** I-2 (rebuild venv) + I-1 (Sentry).
2. **Day 1 afternoon:** Manual end-to-end test of IBKR flow with real TWS.
   Fix anything that breaks.
3. **Day 2:** I-3 (DB persistence for paper_trading) OR remove paper_trading
   from the nav — pick one.
4. **Day 3:** I-4 (pin Redis) + I-5 (real perf metrics if I-3 chosen).
5. **Day 4-5:** I-11 — write at least 30 unit tests covering auth, calculator,
   IBKR safety gate, IBKR order manager (with `ib_async` mocked).
6. **Day 6:** I-7 (best-available quote fallback) — cheap win that improves
   reliability.
7. **Day 7:** I-15 (kill switch admin endpoint). Critical before live trading.

Everything else is iterative.
