# Security Posture & Hardening Guide

**Last Updated:** 2026-05-21
**Audit basis:** `docs/Comprehensive Production Readiness Review.md` (2026-04-06) cross-checked against the current `main` branch.

---

## Headline

The April 2026 production-readiness review flagged three critical security issues. As of this audit:

| Original critique | Status today | Evidence |
|---|---|---|
| S-C1: Real prod credentials committed to git | **REMEDIATED** — `.env` files are now in `.gitignore` and not in `git ls-files`; only `*.env.example` is tracked. `git log -- .env backend/.env ...` returns no commits. | `.gitignore` lines 506-512; `git ls-files \| grep .env` |
| S-C2: WebSocket endpoints lacked authentication | **REMEDIATED** — `/ws` handshake now rejects connections without a valid JWT in `?token=...`; all admin POST endpoints have `Depends(get_current_user)` plus admin role check. | `backend/app/api/v1/endpoints/websocket.py` lines 17-30 (handshake), 73-187 (admin endpoints) |
| S-C3: `SECRET_KEY` defaulted to a weak placeholder | **REMEDIATED** — `Settings.validate_secret_key()` raises `ValueError` if `SECRET_KEY` is empty or the legacy placeholder. | `backend/app/core/config.py` lines 29-38 |

**Conclusion:** No code change is required to close the original critical findings. The remaining work is operational: rotate any keys that exist in local `.env` files (in case they were ever pasted into chat history or backup), and adopt a secrets manager for production.

---

## Operational Hardening Required Before Production

### 1. Rotate every credential in local `.env` files

Your local `.env` files contain real-looking API keys for at least: Z.ai, Gemini, DeepSeek, OpenRouter, Requesty, Brave Search, Alpha Vantage, Alpaca, OANDA, Binance, Finnhub, Polygon, Twelve Data, Nasdaq Data, Gmail SMTP.

While these are not in git history, treat **any key that has ever sat in a plaintext file on a developer laptop** as compromised, and rotate them:

| Service | Where to rotate | Notes |
|---|---|---|
| Z.ai GLM | https://platform.z.ai/ | Revoke `56b25fee...` |
| Google Gemini | https://aistudio.google.com/apikey | Revoke `AIzaSy...` |
| DeepSeek | https://platform.deepseek.com/ | Revoke `sk-e0cdb06b...` |
| OpenRouter | https://openrouter.ai/keys | Revoke `sk-or-v1-187ca8eb...` |
| Brave Search | https://api-dashboard.search.brave.com/app/keys | Revoke `BSA5uLy...` |
| Alpha Vantage | https://www.alphavantage.co/support/#api-key | Free keys are not really rotatable; regenerate by signing up with a new email or contacting support. |
| Alpaca | https://app.alpaca.markets/paper/dashboard/overview | Revoke `PKO...` (paper key — low risk but still rotate) |
| OANDA | OANDA fxTrade web UI > API access | Revoke `1dd93de1...` |
| Binance | https://www.binance.com/en/my/settings/api-management | Revoke `aiGTlY4Wyup...` immediately if not whitelisted to a fixed IP. |
| Finnhub | https://finnhub.io/dashboard | Revoke `d0vjl3hr...` |
| Polygon | https://polygon.io/dashboard/api-keys | Revoke `SUIpnMuKM...` |
| Twelve Data | https://twelvedata.com/account/api-keys | Revoke `f0e7e718...` |
| Nasdaq Data Link | https://data.nasdaq.com/account/profile | Revoke `bx2hhqd...` |
| Gmail SMTP app password | https://myaccount.google.com/apppasswords | Revoke `vkid nfqn phcr rvpp`; generate a new app password if you keep using SMTP. |

After rotation, only place new keys in:
- Local development: `.env` (already gitignored)
- Production: a secrets manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault, or GitHub Actions encrypted secrets for CI/CD).

### 2. Add pre-commit secret scanning

Install one of these and run on every commit:

```bash
# Option A: detect-secrets
pip install detect-secrets
detect-secrets scan > .secrets.baseline
# Then add to .pre-commit-config.yaml

# Option B: gitleaks (binary, no Python needed)
# Download from https://github.com/gitleaks/gitleaks
gitleaks detect --source . --no-banner
```

### 3. Enforce HTTPS in production

`backend/app/main.py` lines 282-300 already loads SSL certs when `ENVIRONMENT=production`. Confirm `SSL_CERT_FILE` / `SSL_KEY_FILE` are set in the prod environment and that any reverse proxy (Nginx/Caddy/ALB) terminates TLS with HSTS enabled.

### 4. Tighten the CORS allow-list

`backend/app/main.py` line 137 uses `allow_methods=["*"]` and `allow_headers=["*"]`. For production:

```python
allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
allow_headers=["Authorization", "Content-Type", "X-Requested-With"]
```

And lock `BACKEND_CORS_ORIGINS` to your real frontend domain, e.g. `https://app.example.com` — no wildcards.

### 5. Add Sentry (or equivalent) for production error tracking

`backend/.env.production` already has a `SENTRY_DSN=CHANGE_ME_SENTRY_DSN` placeholder but no code wires Sentry up. Add:

```python
# backend/app/main.py (top of file)
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

if settings.ENVIRONMENT == "production" and settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
    )
```

### 6. Audit the audit log

`backend/app/core/audit.py` writes compliance-relevant events (auth, data access, financial actions). Confirm:
- Audit rows are append-only (no UPDATE/DELETE permissions on the `audit_logs` table for the application role).
- Logs are shipped off-host within 24h (compliance: SOX 7-year retention).
- Integrity hashes are verified weekly (or use append-only object storage like S3 Object Lock).

### 7. IBKR-specific hardening (added with Phase 3)

When the IBKR integration ships:
- Backend connects to `127.0.0.1:7497` (TWS Paper); never expose TWS over the network.
- TWS API setting "Read-Only API" should be off only for accounts you intend to trade. For paper, on is recommended initially.
- TWS "Trusted IPs" should list only `127.0.0.1`.
- Order placement endpoints (`POST /api/v1/ibkr/orders`) must require authentication AND a per-user IBKR client-id binding stored in the DB.
- Add per-user daily order count and dollar-volume caps (kill switch) in case of bugs.

### 8. Rate-limit auth endpoints aggressively

`backend/app/main.py` already adds `RateLimitingMiddleware`. Confirm `/api/v1/auth/login` and `/api/v1/auth/register` get the auth-specific limit (`AUTH_RATE_LIMIT_PER_MINUTE=10` from `.env.production`) and not just the default 60/min.

### 9. Run a security baseline locally

```bash
# Backend
cd backend
venv/Scripts/pip install bandit safety
venv/Scripts/bandit -r app/ -ll
venv/Scripts/safety check

# Frontend
cd frontend
npm audit --omit=dev
```

These should be CI gates with a clean baseline before each release.

### 10. Periodic security review cadence

- **Weekly:** review audit log anomalies, failed login spikes, rate-limit triggers.
- **Monthly:** run `bandit`, `safety`, `npm audit`, rotate any high-risk secrets.
- **Quarterly:** dependency upgrades, penetration test (OWASP ZAP + manual review of auth flow).
- **Annual:** full SOC2 / GDPR review with external auditor (if commercializing).

---

## Vulnerability Disclosure

This is currently a single-developer proprietary platform. If you receive a security report from a third party (e.g., when MAS goes public), publish a SECURITY.md at the MAS level with:

```
To report a vulnerability, email security@your-domain.com with PGP-encrypted details.
We aim to acknowledge within 48 hours and patch critical issues within 7 days.
```

---

## Open Tracked Risks (deferred — not blockers for IBKR Paper Trading)

| Risk | Severity | Owner | ETA |
|---|---|---|---|
| Test coverage is low (~5 backend tests) | Medium | dev | Phase 4 |
| `40-50% stub/mock code` per old review — needs re-audit | Medium | dev | Phase 2 of this engagement |
| No Sentry / external error tracking wired up | Medium | dev | Phase 4 |
| Replace `yfinance` for commercial use | Medium (MAS only) | dev | Pre-MAS-merge |
| Pin Redis ≤ 7.2 or migrate to Valkey | Low (MAS only) | dev | Pre-MAS-merge |
| Grafana ≥ 8.0 AGPL exposure for MAS | Low (MAS only) | dev | Pre-MAS-merge |
