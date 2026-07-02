# Feature-Level License Inventory

**Last Updated:** 2026-05-21
**Owner:** Vincent S. Pereira
**Platform License:** Proprietary - All Rights Reserved (see `LICENSE`)

This document maps each major feature of the Financial Analysis Platform to its
**direct third-party dependencies** and their licenses, so that the Multi-Agent
System (MAS) — or any other project owned by the Owner — can decide whether to
incorporate that feature without licensing conflict.

> **Reading guide:**
> - **MAS-OK** = safe to incorporate into MAS (commercial, closed-source product). Plain attribution required at most.
> - **MAS-OK (attrib.)** = same as above but with an attribution / NOTICE file requirement.
> - **MAS-CAUTION** = legally usable but watch the terms-of-service for the underlying data (not the code).
> - **MAS-AVOID** = copyleft (LGPL/GPL/AGPL) or restrictive TOS that conflicts with a commercial product. Replace before integrating.

---

## License Compatibility Cheat Sheet

| License | Commercial Use | Closed-Source Use | Attribution | MAS Verdict |
|---|---|---|---|---|
| MIT | Yes | Yes | Notice required | MAS-OK (attrib.) |
| BSD-2 / BSD-3 | Yes | Yes | Notice required | MAS-OK (attrib.) |
| Apache-2.0 | Yes | Yes | Notice + state changes | MAS-OK (attrib.) |
| ISC | Yes | Yes | Notice required | MAS-OK (attrib.) |
| Python-2.0 (PSF) | Yes | Yes | Notice required | MAS-OK (attrib.) |
| LGPL-2.1+ / LGPL-3+ | Yes (dynamic link only) | Yes (dynamic link only) | Yes + source on request | MAS-CAUTION (link, do not embed) |
| MPL-2.0 | Yes | Yes (file-level copyleft) | Notice + source of MPL files | MAS-CAUTION |
| GPL-2 / GPL-3 | Yes | NO (taints whole product) | Yes + source | MAS-AVOID |
| AGPL-3 | Yes | NO (even SaaS triggers source) | Yes + source | MAS-AVOID |
| Vendor TOS (Alpha Vantage, Yahoo, IBKR, Stripe etc.) | Varies | Code OK, **data** may be restricted | Per TOS | MAS-CAUTION |

---

## Feature 1: Authentication & Authorization

**Source paths:** `backend/app/services/auth/`, `backend/app/core/auth.py`, `backend/app/api/v1/endpoints/auth.py`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `fastapi` | 0.104.1+ | MIT | MAS-OK (attrib.) | Web framework |
| `python-jose[cryptography]` | 3.3.0 | MIT | MAS-OK (attrib.) | JWT issue/verify |
| `passlib[bcrypt]` | 1.7.4 | BSD-3-Clause | MAS-OK (attrib.) | Password hashing |
| `bcrypt` | 4.0.1 | Apache-2.0 | MAS-OK (attrib.) | Hash backend |
| `python-multipart` | 0.0.6 | Apache-2.0 | MAS-OK (attrib.) | Form parsing |
| `pydantic` | 2.5.0+ | MIT | MAS-OK (attrib.) | Schema validation |
| `redis` | 5.0.1 | MIT | MAS-OK (attrib.) | Session / lockout state |

**MAS verdict:** **Fully portable.** All MIT/BSD/Apache. Carry a NOTICE file listing these licenses.

---

## Feature 2: Financial Calculator (Ratios, DCF, DDM, Graham)

**Source paths:** `backend/app/services/calculator/`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `numpy` | 1.26.0+ | BSD-3-Clause | MAS-OK (attrib.) | Numerical core |
| `pandas` | 2.2.0+ | BSD-3-Clause | MAS-OK (attrib.) | DataFrames |
| `scipy` | 1.11.4 | BSD-3-Clause | MAS-OK (attrib.) | Optimization / stats |

**MAS verdict:** **Fully portable.** Pure BSD stack. The financial formulas themselves are not copyrightable.

---

## Feature 3: Portfolio Management & Optimization

**Source paths:** `backend/app/services/portfolio/`, `backend/app/services/analysis/portfolio_optimization.py`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `numpy` | 1.26+ | BSD-3-Clause | MAS-OK (attrib.) | |
| `pandas` | 2.2+ | BSD-3-Clause | MAS-OK (attrib.) | |
| `scipy.optimize` | 1.11+ | BSD-3-Clause | MAS-OK (attrib.) | Efficient frontier solver |
| `scikit-learn` | 1.3.2 | BSD-3-Clause | MAS-OK (attrib.) | Optional: clustering |

**MAS verdict:** **Fully portable.**

---

## Feature 4: Market Data Ingestion

**Source paths:** `backend/app/services/data/`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `httpx` | 0.25.2 | BSD-3-Clause | MAS-OK (attrib.) | Async HTTP |
| `aiohttp` | 3.9.1 | Apache-2.0 | MAS-OK (attrib.) | Async HTTP (alt) |
| `requests` | 2.31.0 | Apache-2.0 | MAS-OK (attrib.) | Sync HTTP |
| `requests-ratelimiter` | 0.4.2 | MIT | MAS-OK (attrib.) | Rate limiting |
| `yfinance` | 0.2.33+ | Apache-2.0 | **MAS-CAUTION** | **Code is Apache-2.0, but Yahoo Finance's TOS prohibits commercial redistribution of the data. For MAS commercial use, replace with a licensed data vendor (Polygon, IEX Cloud, Tradier, EOD Historical Data, FMP, Alpha Vantage paid tier).** |
| `beautifulsoup4` | 4.12.2 | MIT | MAS-OK (attrib.) | HTML parsing for SEC EDGAR |
| `lxml` | 4.9.3 | BSD-3-Clause | MAS-OK (attrib.) | XML parsing |
| Alpha Vantage API (data) | n/a | Vendor TOS | **MAS-CAUTION** | Free tier prohibits redistribution; commercial tier required for monetization. |
| Financial Modeling Prep API | n/a | Vendor TOS | **MAS-CAUTION** | Commercial license required. |
| SEC EDGAR (data) | n/a | Public Domain (US Govt) | MAS-OK | US federal works are public domain. Follow EDGAR fair-access rules (User-Agent, rate limit). |

**MAS verdict:** **Code portable; data is the constraint.** When porting to MAS, swap `yfinance` for a commercially-licensed feed and confirm Alpha Vantage/FMP plans cover commercial redistribution.

---

## Feature 5: Real-Time Market Data Streaming (Polygon.io)

**Source paths:** `backend/app/services/market_data/`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `websockets` | 15.0+ | BSD-3-Clause | MAS-OK (attrib.) | |
| Polygon.io API (data) | n/a | Vendor TOS | **MAS-CAUTION** | Paid tier required for real-time + commercial redistribution. |

**MAS verdict:** **Code portable; ensure Polygon plan permits commercial use.**

---

## Feature 6: Technical Analysis & Indicators

**Source paths:** `backend/app/services/analysis/technical_indicators.py`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `numpy` | 1.26+ | BSD-3-Clause | MAS-OK (attrib.) | |
| `pandas` | 2.2+ | BSD-3-Clause | MAS-OK (attrib.) | |

**MAS verdict:** **Fully portable.** Implementations appear to be in-house (no `ta-lib` or `pandas-ta` dependency detected). Verify before porting; if `ta-lib` is added later, note that `ta-lib` itself is BSD-2-Clause (MAS-OK).

---

## Feature 7: Backtesting Engine

**Source paths:** `backend/app/services/backtesting/`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `numpy` | 1.26+ | BSD-3-Clause | MAS-OK (attrib.) | |
| `pandas` | 2.2+ | BSD-3-Clause | MAS-OK (attrib.) | |

**MAS verdict:** **Fully portable.**

---

## Feature 8: ML / Deep-Learning Analytics

**Source paths:** `backend/app/services/analytics/ml_service.py`, `backend/app/services/analytics/deep_learning_service.py`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `scikit-learn` | 1.3.2 | BSD-3-Clause | MAS-OK (attrib.) | Classical ML |
| `numpy` | 1.26+ | BSD-3-Clause | MAS-OK (attrib.) | |
| `pandas` | 2.2+ | BSD-3-Clause | MAS-OK (attrib.) | |
| `scipy` | 1.11+ | BSD-3-Clause | MAS-OK (attrib.) | |

**Watch-list (NOT currently imported, but commonly added):**

| Potential addition | License | Verdict | Notes |
|---|---|---|---|
| `torch` (PyTorch) | BSD-3-Clause | MAS-OK (attrib.) | |
| `tensorflow` | Apache-2.0 | MAS-OK (attrib.) | |
| `transformers` (HuggingFace) | Apache-2.0 | MAS-OK (attrib.) | Models themselves may have different licenses |
| `Prophet` (Meta) | MIT | MAS-OK (attrib.) | |
| Specific HuggingFace models | Per-model | **MAS-CAUTION** | Many are CC-BY-NC (no commercial), Llama-2/3 (custom), Stable Diffusion (CreativeML-OpenRAIL). Audit each model. |

**MAS verdict:** **Code portable.** If you fine-tune third-party LLMs, audit each model's license.

---

## Feature 9: Sentiment Analysis (News + NLP)

**Source paths:** `backend/app/services/sentiment/`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `nltk` | 3.9.2 | Apache-2.0 | MAS-OK (attrib.) | Code only |
| NLTK data corpora | varies | **MAS-CAUTION** | Some corpora (e.g., `treebank`) require licenses; lexicons (VADER) are MIT. |
| News API / vendor | n/a | Vendor TOS | **MAS-CAUTION** | If using NewsAPI.org or similar, paid plan needed for commercial. |

**MAS verdict:** **Code portable; check downloaded NLTK data corpora and any news vendor TOS.**

---

## Feature 10: Report Generation (PDF)

**Source paths:** `backend/app/services/report/`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `reportlab` | 4.0.7 | BSD-3-Clause (open-source edition) | MAS-OK (attrib.) | **The open-source `reportlab` library on PyPI is BSD; the commercial "ReportLab PLUS" is paid. The PyPI package is fine for MAS.** |

**MAS verdict:** **Fully portable.**

---

## Feature 11: Stock Screener

**Source paths:** `backend/app/services/screener/`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `sqlalchemy` | 2.0.23 | MIT | MAS-OK (attrib.) | |
| `pandas` | 2.2+ | BSD-3-Clause | MAS-OK (attrib.) | |

**MAS verdict:** **Fully portable.**

---

## Feature 12: Notifications & Alerts

**Source paths:** `backend/app/services/notifications/`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `sqlalchemy` | 2.0.23 | MIT | MAS-OK (attrib.) | |
| SMTP (Python stdlib) | n/a | PSF | MAS-OK (attrib.) | |

**MAS verdict:** **Fully portable.**

---

## Feature 13: Billing & Subscriptions (Stripe)

**Source paths:** `backend/app/services/billing/`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `stripe` (Python SDK) | 7.8.0 | MIT | MAS-OK (attrib.) | |
| Stripe API & dashboard | n/a | Stripe TOS | MAS-OK with account | Standard payment processing terms apply. |

**MAS verdict:** **Fully portable.** Stripe is the de-facto SaaS payment standard.

---

## Feature 14: Audit Logging & Compliance (SOX/GDPR/PCI-DSS)

**Source paths:** `backend/app/core/audit.py`, `backend/app/models/audit.py`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `sqlalchemy` | 2.0+ | MIT | MAS-OK (attrib.) | |
| `pydantic` | 2.5+ | MIT | MAS-OK (attrib.) | |

**MAS verdict:** **Fully portable.** Compliance frameworks themselves are not licensed; the *code that implements them* is in-house.

---

## Feature 15: Paper Trading Engine (In-Memory Simulator)

**Source paths:** `backend/app/services/paper_trading/`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| Python stdlib only | n/a | PSF | MAS-OK (attrib.) | |

**MAS verdict:** **Fully portable.** Note: this is a toy simulator with hardcoded prices — for MAS, replace with IBKR paper trading (see Feature 17).

---

## Feature 16: WebSocket Real-Time Layer

**Source paths:** `backend/app/core/websocket.py`, `backend/app/api/v1/endpoints/websocket.py`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `fastapi` WebSocket | MIT | MIT | MAS-OK (attrib.) | |
| `websockets` | 15.0+ | BSD-3-Clause | MAS-OK (attrib.) | |

**MAS verdict:** **Fully portable.**

---

## Feature 17: IBKR Integration (NEW — Phase 3)

**Source paths:** `backend/app/services/ibkr/` (to be added)

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `ib-async` | latest | **BSD-2-Clause** | MAS-OK (attrib.) | Active community fork of ib_insync. |
| Interactive Brokers TWS / IB Gateway | n/a | **IBKR EULA + API TOS** | **MAS-CAUTION** | TWS/Gateway are free but proprietary IBKR software. The IBKR API Non-Commercial / Commercial License Agreement applies. For MAS commercial product distribution, **review the IBKR API license terms** — generally OK if your end users run their own TWS, but if you redistribute or operate accounts on behalf of others, IBKR may require an enterprise licensing arrangement. |
| Interactive Brokers market data | n/a | **Per-exchange subscription fees** | **MAS-CAUTION** | Real-time market data subscriptions are per-account, per-exchange. Cannot be redistributed. |

**MAS verdict:** **Code portable; legal/commercial review of IBKR licensing required before MAS public release.** For personal use and small-scale paper trading: fine.

---

## Feature 18: Frontend (React PWA)

**Source paths:** `frontend/src/`, `frontend/package.json`

| Dependency | Version | License | Verdict | Notes |
|---|---|---|---|---|
| `react`, `react-dom` | 18.2+ | MIT | MAS-OK (attrib.) | |
| `react-router-dom` | 6.20+ | MIT | MAS-OK (attrib.) | |
| `@tanstack/react-query` | 5.8+ | MIT | MAS-OK (attrib.) | |
| `axios` | 1.6+ | MIT | MAS-OK (attrib.) | |
| `chart.js` + `react-chartjs-2` | 4.4 / 5.2 | MIT | MAS-OK (attrib.) | |
| `date-fns` | 2.30+ | MIT | MAS-OK (attrib.) | |
| `lucide-react` | 0.294+ | ISC | MAS-OK (attrib.) | Icon library |
| `react-hook-form` | 7.48+ | MIT | MAS-OK (attrib.) | |
| `@hookform/resolvers` | 3.3+ | MIT | MAS-OK (attrib.) | |
| `zod` | 3.22+ | MIT | MAS-OK (attrib.) | Runtime validation |
| `react-hot-toast` | 2.4+ | MIT | MAS-OK (attrib.) | |
| `@headlessui/react` | 1.7+ | MIT | MAS-OK (attrib.) | |
| `tailwindcss` | 3.3+ | MIT | MAS-OK (attrib.) | |
| `tailwind-merge` | 3.3+ | MIT | MAS-OK (attrib.) | |
| `clsx` | 2.1+ | MIT | MAS-OK (attrib.) | |
| `autoprefixer` | 10.4+ | MIT | MAS-OK (attrib.) | |
| `postcss` | 8.4+ | MIT | MAS-OK (attrib.) | |
| `vite` | 5.0+ | MIT | MAS-OK (attrib.) | |
| `@vitejs/plugin-react` | 4.1+ | MIT | MAS-OK (attrib.) | |
| `typescript` | 5.2+ | Apache-2.0 | MAS-OK (attrib.) | |
| `eslint` and plugins | 8.53+ | MIT | MAS-OK (attrib.) | Dev only |
| `prettier` | 3.1+ | MIT | MAS-OK (attrib.) | Dev only |
| `vitest`, `@testing-library/*` | varies | MIT | MAS-OK (attrib.) | Dev only |
| `jsdom` | 23+ | MIT | MAS-OK (attrib.) | Dev only |

**MAS verdict:** **Fully portable.** The entire frontend stack is MIT/ISC/Apache-2.0.

---

## Feature 19: Mobile App (React Native)

**Source paths:** `mobile/` (if present)

The mobile screens visible in the graph (`Mobile App Entry`, `Mobile Markets Screen`, etc.) imply React Native. Standard RN stack:

| Dependency | License | Verdict |
|---|---|---|
| `react-native` | MIT | MAS-OK (attrib.) |
| `@react-navigation/*` | MIT | MAS-OK (attrib.) |
| `react-native-reanimated` | MIT | MAS-OK (attrib.) |
| `expo` (if used) | MIT | MAS-OK (attrib.) |

**MAS verdict:** **Fully portable** (subject to confirming actual installed packages).

---

## Feature 20: Infrastructure / Deployment

**Source paths:** `docker-compose*.yml`, `infrastructure/`

| Component | License | Verdict | Notes |
|---|---|---|---|
| Docker / Docker Compose | Apache-2.0 | MAS-OK (attrib.) | |
| PostgreSQL | PostgreSQL License (BSD-style) | MAS-OK (attrib.) | |
| TimescaleDB (community ed.) | Apache-2.0 | MAS-OK (attrib.) | **TimescaleDB has a separate `tsl` directory under TSL (proprietary) license — community features only are Apache. Confirm you're not using TSL-only features.** |
| Redis (Community Edition, 7.x) | BSD-3-Clause | MAS-OK (attrib.) | **Redis ≥ 7.4 moved to a dual SSPL/RSAL license. For MAS commercial use, pin to ≤ 7.2.x (BSD), or use Valkey (BSD fork), or use ElastiCache.** |
| Nginx | BSD-2-Clause | MAS-OK (attrib.) | |
| Prometheus | Apache-2.0 | MAS-OK (attrib.) | |
| Grafana OSS | AGPL-3.0 (as of 8.x onward) | **MAS-CAUTION** | **Grafana's open-source edition switched from Apache-2.0 to AGPL-3.0 in v8.0. AGPL is a SaaS-trigger copyleft — if MAS exposes Grafana over a network, MAS source may need to be released. Mitigations: use Grafana Cloud, use Grafana ≤ 7.5 (Apache), or replace with a permissively-licensed dashboard (e.g., Apache Superset, which is Apache-2.0).** |

**MAS verdict:** **Re-evaluate Redis and Grafana before MAS commercialization.** Other infrastructure components are safe.

---

## Top-Level MAS Portability Verdict

| Verdict bucket | Action |
|---|---|
| **Fully portable today** | Features 1, 2, 3, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 18, 19 |
| **Portable code, replace data feed** | Features 4 (yfinance/Alpha Vantage/FMP), 5 (Polygon), 9 (news vendor) |
| **Portable code, review broker licensing** | Feature 17 (IBKR) |
| **Re-evaluate infra component** | Feature 20 (Redis ≥ 7.4 SSPL, Grafana ≥ 8.0 AGPL) |

**Recommended action items before merging into MAS:**

1. **Replace `yfinance`** with a commercially-licensed market data feed (Polygon paid tier, IEX Cloud, Tradier Market Data, EOD Historical Data, or Alpha Vantage Premium).
2. **Pin Redis to ≤ 7.2.x** in `docker-compose.prod.yml`, OR migrate to Valkey 7.2.x+ (drop-in BSD fork), OR use AWS ElastiCache / Redis Cloud (no embed concern).
3. **Replace Grafana ≥ 8.0** with Grafana ≤ 7.5 (Apache), or use Grafana Cloud (no embed), or Apache Superset.
4. **Review IBKR API TOS** with a legal advisor if you intend to operate IBKR connections on behalf of MAS customers.
5. **Generate a `NOTICE.md`** file containing every attribution-required notice (MIT, BSD, Apache, ISC). A `pip-licenses` and `license-checker` sweep at build time will collect these automatically — see `scripts/generate_notices.sh` (to be added).

---

## Generating Up-to-Date Licenses

Run these from the project root to refresh the dependency list:

```bash
# Backend (Python)
pip install pip-licenses
pip-licenses --format=markdown --output-file=docs/python_licenses.md \
             --with-urls --with-license-file --no-license-path

# Frontend (Node)
cd frontend
npx license-checker --production --json --out ../docs/node_licenses.json
```

These auto-generated reports complement (but do not replace) this feature-level
inventory: this document is the human-readable MAS portability decision matrix;
the auto-generated reports are the comprehensive raw data.
