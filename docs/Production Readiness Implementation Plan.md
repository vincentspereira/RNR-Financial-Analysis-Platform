# Production Readiness Implementation Plan

**Generated:** April 6, 2026
**Based on:** Comprehensive Production Readiness Review

---

## How to Use This Plan

Each task includes exact file paths, specific code changes, and verification steps. Claude Code should execute phases sequentially, completing all tasks in a phase before moving to the next.

---

## PHASE 1 — STABILIZE (Critical Fixes)

### Task 1.1: Remove Committed Credentials & Secure Secrets

**Priority:** P0 | **Risk:** Data breach if skipped

**Step 1 — Create `.env.example` files (safe templates without real values):**

Create `backend/.env.example`:
```
SECRET_KEY=change-me-to-a-random-string
DATABASE_URL=postgresql://user:password@localhost:5432/financial_analysis_dev
REDIS_URL=redis://localhost:6379/0
ALPHA_VANTAGE_API_KEY=your-api-key-here
ENVIRONMENT=development
DEBUG=true
```

Create `frontend/.env.example`:
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

**Step 2 — Untrack `.env` files from git:**
```bash
git rm --cached backend/.env
git rm --cached backend/.env.production
git rm --cached frontend/.env
git rm --cached .env 2>/dev/null || true
```

**Step 3 — Verify `.gitignore` covers all env files.** The existing `.gitignore` already has entries. Verify with:
```bash
git status  # .env files should NOT appear
```

**Step 4 — Purge credential history:**
```bash
pip install git-filter-repo
git filter-repo --invert-paths --path backend/.env --path backend/.env.production --path frontend/.env
```

**Step 5 — Add pre-commit secret scanning.** Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```
Run: `pip install pre-commit && pre-commit install && detect-secrets scan > .secrets.baseline`

**Step 6 — Rotate all exposed credentials** (manual — user must do this):
- Generate new `SECRET_KEY` with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- Change PostgreSQL password
- Change Redis password
- Update all API keys

---

### Task 1.2: Add Authentication to Financial Endpoints

**Priority:** P0 | **File:** `backend/app/api/v1/endpoints/financial.py`

**Step 1 — Read the current file** to see all endpoint signatures.

**Step 2 — Add the auth dependency import** at the top of the file:
```python
from app.core.auth import get_current_user_from_token
```

**Step 3 — Add `current_user: dict = Depends(get_current_user_from_token)` parameter to EVERY endpoint:**
- `calculate_financial_ratios` (line ~41)
- `calculate_valuation` 
- `peer_comparison`
- `get_company_financial_data`
- `batch_calculate_ratios`

Each endpoint signature changes from:
```python
async def calculate_financial_ratios(
    request: FinancialRatiosRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
```
To:
```python
async def calculate_financial_ratios(
    request: FinancialRatiosRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: dict = Depends(get_current_user_from_token),
):
```

**Verification:** Start the server and confirm unauthenticated requests to `/api/v1/financial/ratios/calculate` return 401.

---

### Task 1.3: Add Authentication & Authorization to WebSocket Endpoints

**Priority:** P0 | **Files:** `backend/app/api/v1/endpoints/websocket.py`, `backend/app/core/websocket.py`

**Step 1 — Add auth dependency to admin endpoints** in `websocket.py`:

For `broadcast_message` (line ~67), `notify_user` (line ~108), `update_market_data` (line ~135), `update_portfolio`:
```python
from app.core.auth import get_current_user_from_token

@router.post("/ws/broadcast")
async def broadcast_message(
    message: str,
    channel: str = None,
    room_id: str = None,
    user_id: str = None,
    current_user: dict = Depends(get_current_user_from_token),
):
```

**Step 2 — Add role check for admin endpoints** — after the user is authenticated, verify they have admin role:
```python
if current_user.get("role") != "admin":
    raise HTTPException(status_code=403, detail="Admin access required")
```

**Step 3 — Add JWT validation at WebSocket handshake** in the `/ws` endpoint. Modify to accept token as query parameter:
```python
from app.core.auth import decode_token

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    user = await decode_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return
    # ... rest of handler
```

**Step 4 — Remove or gate the test page** (line ~387 in websocket.py). Remove the `get_test_page` endpoint entirely, or wrap it:
```python
if not settings.DEBUG:
    raise HTTPException(status_code=404)
```

**Step 5 — Fix the XSS in the test page** if keeping it for dev. Change `innerHTML` to `textContent`:
```javascript
messagesDiv.textContent += `[${timestamp}] ${message}\n`;
```

---

### Task 1.4: Replace Pickle with orjson in Cache Layer

**Priority:** P0 | **File:** `backend/app/core/cache.py`

**Step 1 — Add `orjson` to `backend/requirements-core.txt`:**
```
orjson==3.9.10
```

**Step 2 — Replace pickle usage in cache.py.** Change the import block:
```python
# REMOVE: import pickle
# REMOVE: import json
import orjson
```

**Step 3 — Replace `_serialize_value` (line ~58):**
```python
def _serialize_value(self, value: Any) -> bytes:
    """Serialize value for storage using orjson"""
    return orjson.dumps(value, default=str)
```

**Step 4 — Replace `_deserialize_value` (line ~65):**
```python
def _deserialize_value(self, value: bytes) -> Any:
    """Deserialize value from storage"""
    if value is None:
        return None
    return orjson.loads(value)
```

**Step 5 — Remove all fallback pickle paths** in the file. Search for `pickle` and replace all occurrences.

---

### Task 1.5: Fix Runtime-Breaking Bugs

**Priority:** P0

#### Bug B-3: Monitoring calls non-existent public method
**File:** `backend/app/api/v1/endpoints/monitoring.py` line 24
**Fix:** Change `collect_system_metrics()` to `_collect_system_metrics()` — or better, make it public in `monitoring.py`:
```python
# In monitoring.py, rename _collect_system_metrics to collect_system_metrics
```

#### Bug B-4: Duplicate MetricsCollector instances
**File:** `backend/app/core/monitoring.py` lines 190 and 469
**Fix:** Remove the duplicate at line 469 (`metrics_collector = MetricsCollector()`). Update `endpoints/monitoring.py` imports to use the instance at line 190. Find all imports of `metrics_collector` and ensure they point to the correct instance at line 190.

#### Bug B-5: Audit async context manager crash
**File:** `backend/app/core/audit.py` line 139
**Current:** `async with get_async_session() as db:` — this is wrong because `get_async_session` is an async generator, not an async context manager.
**Fix:**
```python
# Replace the try block at line 138:
async for db in get_async_session():
    audit_log = AuditLog(...)
    db.add(audit_log)
    await db.commit()
    break  # Only get one session
```

#### Bug B-6: Raw SQL needs text() wrapper
**File:** `backend/app/core/database.py` line 131
**Fix:**
```python
from sqlalchemy import text
# Line 131: change to
await conn.execute(text("SELECT 1"))
```

#### Bug B-7: ValidationError shadows Pydantic
**File:** `backend/app/core/validation.py` line 13
**Fix:** Rename the custom class:
```python
class InputValidationError(Exception):
    """Custom validation error"""
    pass
```
Then update all references to `ValidationError` within this file to `InputValidationError`. Keep the Pydantic import `from pydantic import ... ValidationError` as-is.

#### Bug B-11: error_tracking.py date arithmetic
**File:** `backend/app/core/error_tracking.py` line 304
**Fix:** Replace `now.replace(day=...)` with proper timedelta:
```python
from datetime import timedelta
cutoff = now - timedelta(days=30)
```

#### Bug B-12: error_tracking.py negative hour
**File:** `backend/app/core/error_tracking.py` line 286
**Fix:** Replace `now.replace(hour=now.hour-1)` with:
```python
one_hour_ago = now - timedelta(hours=1)
```

#### Bug B-14: logging.py traceback produces list not string
**File:** `backend/app/core/logging.py` line 55
**Fix:**
```python
"traceback": ''.join(traceback.format_exception(*record.exc_info))
```

#### Bug B-15: Concurrent dict mutation in batch ingestion
**File:** `backend/app/services/data/data_ingestion_service.py` line 462
**Fix:** Add `asyncio.Lock`:
```python
def __init__(self):
    self._results_lock = asyncio.Lock()
```
Wrap results updates:
```python
async with self._results_lock:
    results['success'] += 1  # or whatever mutation
```

---

### Task 1.6: Fix Duplicate get_sync_session in database.py

**File:** `backend/app/core/database.py` lines 104 and 156

**Fix:** Remove the second definition (lines 156-169). Keep only the first one (lines 104-119). The second one uses `yield` which makes it a generator dependency, while the first returns the session directly. Decide which pattern is needed and keep one.

**Recommended:** Keep the generator version (lines 156-169) since it matches FastAPI's `Depends()` pattern, and remove lines 104-119.

---

### Task 1.7: Fix Missing Python Dependencies

**File:** `backend/requirements-core.txt`

**Add these missing packages:**
```
aiohttp==3.9.1
yfinance==0.2.33
numpy==1.26.2
pandas==2.1.4
scikit-learn==1.3.2
psutil==5.9.7
requests-ratelimiter==0.4.1
orjson==3.9.10
msgpack==1.0.7
```

**Verification:** Run `pip install -r requirements-core.txt` and confirm no errors.

---

### Task 1.8: Fix Frontend Compile-Breaking Issues

#### F-1: Remove SCSS config referencing missing file
**File:** `frontend/vite.config.ts` lines 67-71
**Fix:** Remove the entire `preprocessorOptions.scss` block since `src/styles/variables.scss` doesn't exist:
```typescript
// REMOVE these lines:
preprocessorOptions: {
  scss: {
    additionalData: `@import "@/styles/variables.scss";`,
  },
},
```

#### F-2: Fix terser — not installed
**File:** `frontend/vite.config.ts` line 35
**Fix:** Either install terser (`npm install -D terser`) or switch to esbuild minification:
```typescript
minify: 'esbuild',  // esbuild is built into Vite, no install needed
// Remove terserOptions block
```

#### F-3: Fix missing accessibility exports
**File:** `frontend/src/utils/accessibility.ts`
**Fix:** Export the hooks that `AccessibleComponents.tsx` imports (`useFocusTrap`, `useAnnouncer`, `useKeyboardNavigation`). Read the file first, then add the missing exports.

#### F-4: Disable source maps in production
**File:** `frontend/vite.config.ts` line 33
**Fix:** Make it conditional:
```typescript
sourcemap: process.env.NODE_ENV !== 'production',
```

---

### Task 1.9: Standardize Password Policy

**Priority:** P1

**Step 1 — Set minimum to 12 everywhere:**

| File | Change |
|------|--------|
| `backend/app/schemas/auth.py` line ~14 | Change `min_length=8` to `min_length=12` |
| `backend/app/core/validation.py` line ~82 | Change `8` to `12` in InputValidator |
| `frontend/src/components/auth/LoginForm.tsx` line ~22 | Change `minLength={6}` to `minLength={12}` |
| `frontend/src/components/auth/RegisterForm.tsx` line ~27 | Change `minLength={8}` to `minLength={12}` |

`backend/app/core/security.py` already has `MIN_PASSWORD_LENGTH = 12` — this is the source of truth.

**Step 2 — Remove demo credentials from production UI:**
**File:** `frontend/src/components/auth/LoginForm.tsx` lines ~177-184
**Fix:** Gate behind dev mode:
```tsx
{import.meta.env.DEV && (
  <div className="text-xs text-gray-500">
    <p>Demo: demo@example.com / Demo123!</p>
  </div>
)}
```

---

### Task 1.10: Fix Error Message Information Leakage

**Priority:** P1 | **Files:** Multiple

**Pattern to fix** — replace `detail=f"...: {str(e)}"` with generic messages:

**File:** `backend/app/api/v1/endpoints/data.py`
Replace all instances of:
```python
detail=f"Data ingestion failed: {str(e)}"
```
With:
```python
detail="Data processing failed. Please try again later."
# And add: logger.error(f"Data ingestion failed: {str(e)}", exc_info=True)
```

**File:** `backend/app/api/v1/endpoints/financial.py`
Replace all instances of:
```python
detail=f"Error calculating financial ratios: {str(e)}"
```
With:
```python
detail="Calculation failed. Please try again later."
# And add: logger.error(f"Financial ratio calculation error: {str(e)}", exc_info=True)
```

**File:** `backend/app/services/auth/auth_service.py`
Replace:
```python
return None, f"Registration failed: {str(e)}"
```
With:
```python
logger.error(f"Registration failed: {str(e)}", exc_info=True)
return None, "Registration failed. Please try again."
```

**Apply the same pattern everywhere** `str(e)` appears in user-facing responses.

---

### Task 1.11: Replace print() with Structured Logging

**Priority:** P1

Search the entire backend for `print(` calls and replace with the project's logging system:
```bash
grep -rn "print(" backend/app/ --include="*.py"
```

For each occurrence:
```python
# BEFORE:
print(f"Some message: {value}")

# AFTER:
from app.core.logging import get_logger
logger = get_logger("app.module_name")
logger.logger.info(f"Some message: {value}")
```

---

## PHASE 2 — REAL FUNCTIONALITY

### Task 2.1: Rewrite PortfolioService with Database Integration

**File:** `backend/app/services/portfolio/portfolio_service.py`

**Current:** Uses `self.portfolios = {}` in-memory dict (line 15).

**Fix — Complete rewrite to use SQLAlchemy:**

```python
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.database import get_async_session
from app.models.portfolio import Portfolio, PortfolioHolding

logger = get_logger("app.portfolio")


class PortfolioService:
    """Service for portfolio management operations using database"""

    async def create_portfolio(self, db: AsyncSession, user_id: str, portfolio_data: Dict) -> Dict:
        portfolio = Portfolio(
            user_id=user_id,
            name=portfolio_data.get("name", "My Portfolio"),
            description=portfolio_data.get("description", ""),
            cash_balance=Decimal(portfolio_data.get("cash_balance", "0.00")),
        )
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)
        return portfolio

    async def get_portfolio(self, db: AsyncSession, portfolio_id: str, user_id: str) -> Optional[Dict]:
        result = await db.execute(
            select(Portfolio).where(
                and_(
                    Portfolio.id == portfolio_id,
                    Portfolio.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_portfolios(self, db: AsyncSession, user_id: str) -> List[Dict]:
        result = await db.execute(
            select(Portfolio).where(
                and_(Portfolio.user_id == user_id, Portfolio.is_active == True)
            )
        )
        return list(result.scalars().all())

    async def update_portfolio(self, db: AsyncSession, portfolio_id: str, user_id: str, data: Dict) -> Optional[Dict]:
        portfolio = await self.get_portfolio(db, portfolio_id, user_id)
        if not portfolio:
            return None
        for key, value in data.items():
            if hasattr(portfolio, key) and key != 'id':
                setattr(portfolio, key, value)
        portfolio.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(portfolio)
        return portfolio

    async def delete_portfolio(self, db: AsyncSession, portfolio_id: str, user_id: str) -> bool:
        portfolio = await self.get_portfolio(db, portfolio_id, user_id)
        if not portfolio:
            return False
        portfolio.is_active = False
        await db.commit()
        return True


portfolio_service = PortfolioService()
```

**Also update:** All endpoint files that call `portfolio_service` to pass `db` session.

---

### Task 2.2: Fix DataIngestionService Field Mismatches

**File:** `backend/app/services/data/data_ingestion_service.py`

**Step 1 — Read the Company model** (`backend/app/models/company.py`) to see actual column names.

**Step 2 — Fix the DataUpdate model references.** The service tries to set `target_symbol` (line 70) and `metadata` (line 72) which may not exist on the model. Check `backend/app/models/` for the actual schema.

**Step 3 — Fix field references** around lines 184-198 where `currency`, `country`, `business_summary`, `full_time_employees` are set. Either:
- Add these columns to the Company model via a new Alembic migration, OR
- Store them in a JSON `metadata` column if one exists

**Step 4 — Create Alembic migration** for any new columns:
```bash
cd backend
alembic revision --autogenerate -m "add_missing_company_fields"
alembic upgrade head
```

---

### Task 2.3: Replace Frontend Mock Data with Real API Calls

This is the largest task. Apply systematically to each page.

**Pattern for every page:**

1. Replace `setTimeout(() => { setData(MOCK_DATA) }, 1000)` with `react-query` fetch calls
2. Use the existing `apiService` from `frontend/src/services/api.ts`
3. Add error handling with the existing `ErrorBoundary`

**File-by-file changes:**

| File | Mock Data to Replace | API Endpoint |
|------|---------------------|--------------|
| `pages/Dashboard.tsx` | Hardcoded stats & charts | `GET /api/v1/analytics/dashboard` |
| `pages/Analysis.tsx` | Hardcoded company data | `GET /api/v1/data/companies/{id}` |
| `pages/Portfolio.tsx` | Hardcoded positions | `GET /api/v1/portfolio/` |
| `pages/Watchlist.tsx` | Hardcoded watchlist | `GET /api/v1/watchlist/` |
| `pages/Analytics.tsx` | Hardcoded predictions | `GET /api/v1/analytics/predictions` |
| `pages/DataManagement.tsx` | Hardcoded sources | `GET /api/v1/data/sources` |

**For each page, replace this pattern:**
```tsx
// BEFORE:
useEffect(() => {
  setTimeout(() => {
    setData(MOCK_DATA);
    setLoading(false);
  }, 1000);
}, []);
```

**With this:**
```tsx
// AFTER:
import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/services/api';

const { data, isLoading, error } = useQuery({
  queryKey: ['dashboard'],
  queryFn: () => apiService.get('/api/v1/analytics/dashboard'),
  retry: 3,
  retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
});
```

---

### Task 2.4: Implement Real PDF Report Generation

**File:** `backend/app/services/report/pdf_generator.py`

**Step 1 — Add dependency:**
```
# requirements-core.txt
reportlab==4.0.7
```

**Step 2 — Replace mock PDF content** (line ~123, `b"Mock PDF content..."`):
```python
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from io import BytesIO

async def generate_report(self, report_data: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(report_data.get("title", "Financial Report"), styles['Title']))
    elements.append(Spacer(1, 12))

    # Content sections
    for section in report_data.get("sections", []):
        elements.append(Paragraph(section["heading"], styles['Heading2']))
        elements.append(Paragraph(section["content"], styles['Normal']))
        elements.append(Spacer(1, 8))

    doc.build(elements)
    return buffer.getvalue()
```

---

### Task 2.5: Implement Refresh Token Rotation

**File:** `backend/app/services/auth/auth_service.py`

**Step 1 — Add refresh token storage.** Create a model or use Redis:
```python
# In auth_service.py refresh_token method (line ~349):
async def refresh_token(self, refresh_token: str) -> dict:
    # 1. Decode and validate the old token
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return None, "Invalid refresh token"

    # 2. Check if token was already used (detect replay)
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    if await self._is_token_revoked(token_hash):
        # Token reuse detected — revoke entire token family
        await self._revoke_token_family(payload["sub"])
        return None, "Token reuse detected. Please re-authenticate."

    # 3. Revoke the old token
    await self._revoke_token(token_hash)

    # 4. Issue new token pair
    new_access = create_access_token(payload["sub"])
    new_refresh = create_refresh_token(payload["sub"])

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }, None
```

**Step 2 — Add token revocation storage** using Redis (already available):
```python
async def _revoke_token(self, token_hash: str):
    """Store revoked token in Redis with TTL matching token expiry"""
    from app.core.cache import cache_manager
    await cache_manager.redis_client.setex(
        f"revoked_token:{token_hash}", 
        7 * 24 * 3600,  # 7 days
        "1"
    )

async def _is_token_revoked(self, token_hash: str) -> bool:
    from app.core.cache import cache_manager
    return await cache_manager.redis_client.exists(f"revoked_token:{token_hash}")
```

---

### Task 2.6: Implement Redis-Backed Rate Limiting

**File:** `backend/app/core/security.py` lines 192-231

**Replace the in-memory `RateLimiter` with Redis-backed version:**

```python
import redis.asyncio as redis
from app.core.config import settings

class RateLimiter:
    """Redis-backed distributed rate limiter"""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        if not self.redis:
            self.redis = redis.from_url(settings.REDIS_URL)
        return self.redis

    async def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Sliding window rate limit check"""
        r = await self._get_redis()
        pipe = r.pipeline()
        now = time.time()
        window_key = f"rate_limit:{key}"

        pipe.zremrangebyscore(window_key, 0, now - window)
        pipe.zadd(window_key, {str(now): now})
        pipe.zcard(window_key)
        pipe.expire(window_key, window)

        results = await pipe.execute()
        count = results[2]

        return count <= limit


rate_limiter = RateLimiter()
```

**Also add** `import time` at the top and create `rate_limiter` as a module-level singleton.

---

### Task 2.7: Implement Account Lockout

**File:** `backend/app/services/auth/auth_service.py`

**Add lockout check to the login method:**

```python
async def login(self, email: str, password: str, ip_address: str = None):
    # Check if account is locked
    lockout_key = f"login_attempts:{email}"
    attempts = await self._get_failed_attempts(lockout_key)

    if attempts >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
        lockout_remaining = await self._get_lockout_remaining(lockout_key)
        return None, f"Account locked. Try again in {lockout_remaining} minutes."

    # ... existing password verification ...

    # On failed password:
    await self._increment_failed_attempts(lockout_key)

    # On successful login:
    await self._clear_failed_attempts(lockout_key)
```

Use Redis for distributed lockout storage with TTL matching `LOCKOUT_DURATION_MINUTES`.

---

### Task 2.8: Add Comprehensive Backend Tests

**Create test files:**

```
backend/tests/
  conftest.py          # Fixtures: test DB, test client, mock user
  test_auth.py         # Auth flows: register, login, refresh, lockout
  test_financial.py    # Financial calculations: ratios, valuation, batch
  test_portfolio.py    # CRUD operations, authorization checks
  test_data.py         # Data ingestion, validation, error handling
  test_websocket.py    # Connection, auth, message handling
  test_security.py     # Rate limiting, token expiry, input validation
  test_cache.py        # Cache hit/miss, serialization, TTL
```

**conftest.py pattern:**
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.core.database import get_async_session, Base

TEST_DB_URL = "postgresql+asyncpg://test:test@localhost:5432/financial_analysis_test"

@pytest.fixture
async def test_db():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession)
    yield session_factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def client(test_db):
    async def override_session():
        async for session in test_db():
            yield session
    app.dependency_overrides[get_async_session] = override_session
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
async def auth_token(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@test.com", "password": "TestPass123!@#",
        "full_name": "Test User"
    })
    return response.json()["access_token"]
```

**Minimum test coverage targets:**
- Auth: 15 tests (register, login, refresh, lockout, validation)
- Financial: 10 tests (ratio calculations, edge cases, batch limits)
- Portfolio: 10 tests (CRUD, authorization, data integrity)
- Security: 8 tests (rate limiting, XSS prevention, SQL injection)

---

### Task 2.9: Fix Frontend Tests

**File:** `frontend/src/components/auth/LoginForm.test.tsx`

**Step 1 — Read the actual `api.ts` service** to understand the real API method names.

**Step 2 — Fix mock setup** — the test mocks `apiService.auth.login` but the actual API service likely has a different method structure. Align with reality.

**Step 3 — Fix assertions** — update to match actual DOM elements:
- Check for actual button text (not "sign up")
- Remove assertions for non-existent "Remember me" checkbox
- Fix aria-label references

---

## PHASE 3 — PRODUCTION HARDENING

### Task 3.1: Create Missing Infrastructure Files

#### nginx.conf
**Create:** `infrastructure/nginx/nginx.conf`
```nginx
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name _;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Frontend
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API proxy
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket proxy
    location /api/v1/ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

#### Database init script
**Create:** `infrastructure/database/init.sql`
```sql
-- Initial database setup
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO financial_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO financial_app;
```

---

### Task 3.2: Fix Docker Compose & Dockerfiles

**File:** `frontend/Dockerfile`

**Fix the npm ci issue (line 11):**
```dockerfile
# Install ALL dependencies (including devDependencies for build)
RUN npm ci && npm cache clean --force

# Build the application
RUN npm run build

# Remove devDependencies after build
RUN npm prune --production
```

**Fix port (nginx serves on 80, not 3030):**
```dockerfile
EXPOSE 80
HEALTHCHECK CMD curl -f http://localhost:80/health || exit 1
```

**File:** `docker-compose.prod.yml`

**Fix exposed DB/Redis ports** — remove `ports:` or bind to 127.0.0.1:
```yaml
postgres:
  # DO NOT expose to host in production
  # ports:
  #   - "5432:5432"
  expose:
    - "5432"
```

**Add resource limits:**
```yaml
backend:
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '1.0'
      reservations:
        memory: 512M
        cpus: '0.5'
```

---

### Task 3.3: Fix Kubernetes Manifests

**File:** `infrastructure/kubernetes/production/backend-deployment.yaml`

**Add namespace:**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
```

**Add secrets:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: database-secret
  namespace: production
type: Opaque
stringData:
  DATABASE_URL: "postgresql+asyncpg://..."
  SECRET_KEY: "..."
```

**Add HPA:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

**Add NetworkPolicy:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: nginx-ingress
      ports:
        - port: 8000
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - port: 5432
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - port: 6379
```

**Add Ingress:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: platform-ingress
  namespace: production
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - platform.example.com
      secretName: platform-tls
  rules:
    - host: platform.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend-service
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
```

**Fix frontend env vars:** Change `REACT_APP_*` to `VITE_*`.

---

### Task 3.4: Fix CI/CD Pipeline

**File:** `.github/workflows/ci-cd-pipeline.yml`

**Step 1 — Consolidate into one pipeline file** (remove or merge `comprehensive-testing.yml`).

**Step 2 — Fix security scans to actually fail:**
```yaml
- name: Security scan
  run: |
    bandit -r backend/app/ -f json -o bandit-report.json
    safety check --json --output safety-report.json
    # DO NOT add || true
```

**Step 3 — Fix YAML indentation** in the `comprehensive-tests` job (7 spaces → 6 spaces for `env` key).

**Step 4 — Fix Python version consistency** — use 3.11 everywhere.

**Step 5 — Remove references to non-existent test directories:**
```
integration_tests/
tests/contract/
tests/compliance/
system_tests/
```

**Step 6 — Replace deprecated `actions/create-release@v1`** with a manual release process or use `softprops/action-gh-release`.

---

### Task 3.5: Add Monitoring Stack

**Create:** `infrastructure/monitoring/grafana/`
- `datasources.yml` — Prometheus datasource
- `dashboards/` — Dashboard JSON configs

**Create:** `infrastructure/monitoring/alertmanager.yml`
```yaml
route:
  receiver: 'email'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h
receivers:
  - name: 'email'
    email_configs:
      - to: 'ops@example.com'
        from: 'alerts@platform.com'
        smarthost: 'smtp.example.com:587'
```

---

### Task 3.6: Clean Up Unused Frontend Dependencies

**Step 1 — Decide on chart library:** Keep `recharts` OR `chart.js/react-chartjs-2`, not both. Remove the unused one from `package.json` and `vite.config.ts`.

**Step 2 — Decide on Redux:** Either:
- Remove `@reduxjs/toolkit` and `react-redux` from `package.json` (if using react-query for state), OR
- Implement actual Redux store for global state

**Step 3 — Remove `terser` config** if switching to esbuild (Task 1.8).

---

### Task 3.7: Fix Additional Security Medium Findings

| ID | Fix |
|----|-----|
| M-1 | CSP: Remove `unsafe-inline` and `unsafe-eval` from `core/middleware.py` lines 41-43. Use nonce-based CSP. |
| M-2 | Token storage: Move from localStorage to httpOnly cookies. Update `frontend/src/services/api.ts` lines 64-80 to use cookie-based auth. |
| M-4 | Account lockout: Implemented in Task 2.7. |
| M-5 | JWT fallback: Remove random fallback in `core/config.py` line 30. Fail fast if SECRET_KEY is not set: `SECRET_KEY: str = os.environ["SECRET_KEY"]` |
| M-6 | CORS: Fix wildcard fallback in `core/middleware.py` lines 325-327. Default to empty list, not `["*"]`. |
| M-7 | Debug mode: Change default to `DEBUG: bool = False` in `core/config.py` line 27. |
| M-8 | CSRF: Add CSRF middleware for state-changing requests, or ensure all mutations require JWT in header (not cookie). |

---

## PHASE 4 — WORLD-CLASS FEATURES (Ongoing)

### Task 4.1: Real-time Market Data Pipeline
- Integrate Polygon.io or IEX Cloud WebSocket API
- Replace `MarketDataStreamer` in `core/websocket.py` with real feed
- Add subscription management per user
- Implement data normalization and validation

### Task 4.2: Technical Analysis Engine
- Add TA-Lib or pandas-ta to requirements
- Create `backend/app/services/analysis/technical_indicators.py`
- Implement 50+ indicators (RSI, MACD, Bollinger, Ichimoku, etc.)
- Add API endpoints under `/api/v1/analysis/technical`

### Task 4.3: Portfolio Optimization
- Implement Monte Carlo simulation
- Add VaR/CVaR calculations
- Build efficient frontier computation
- Create Sharpe/Sortino ratio calculators

### Task 4.4: Backtesting Framework
- Create `backend/app/services/backtesting/` module
- Implement strategy engine with event-driven architecture
- Add slippage and transaction cost models
- Build equity curve and benchmark comparison

### Task 4.5: Sentiment Analysis
- Integrate news API feeds (NewsAPI, Finnhub)
- Add NLP processing pipeline (HuggingFace transformers)
- Create sentiment scoring per ticker
- Build aggregated sentiment dashboard

### Task 4.6: Billing & Subscription (Stripe)
- Integrate Stripe SDK
- Create subscription models in DB
- Add usage tracking and metering
- Implement tiered plan management

---

## EXECUTION ORDER SUMMARY

| Phase | Tasks | Estimated Effort | Priority |
|-------|-------|-----------------|----------|
| Phase 1 (Stabilize) | 1.1 - 1.11 | 1-2 weeks | P0-P1 |
| Phase 2 (Real Functionality) | 2.1 - 2.9 | 2-4 weeks | P1-P2 |
| Phase 3 (Production Hardening) | 3.1 - 3.7 | 2-3 weeks | P2-P3 |
| Phase 4 (World-Class) | 4.1 - 4.6 | Ongoing | P3 |

---

## VERIFICATION CHECKLIST

After completing each phase, verify:

### Phase 1 Verification
- [ ] `git log` shows no `.env` files in history
- [ ] Unauthenticated requests to `/api/v1/financial/*` return 401
- [ ] Unauthenticated requests to `/ws/broadcast` return 401
- [ ] `python -c "from app.core.cache import CacheManager"` succeeds with orjson
- [ ] `pytest backend/tests/` passes all tests
- [ ] `npm run build` in frontend succeeds without errors
- [ ] No `print()` statements remain in backend code
- [ ] No `str(e)` in any user-facing error response

### Phase 2 Verification
- [ ] Portfolio CRUD operations persist to database
- [ ] Data ingestion creates real company records
- [ ] Frontend pages load data from API (not setTimeout mocks)
- [ ] PDF reports contain real data (not "Mock PDF content")
- [ ] Refresh token rotation works (old token rejected after use)
- [ ] Rate limiting backed by Redis
- [ ] Account lockout after 5 failed attempts
- [ ] 50+ backend tests passing

### Phase 3 Verification
- [ ] `docker compose up` starts all services without errors
- [ ] `kubectl apply -f infrastructure/kubernetes/` succeeds
- [ ] nginx.conf exists and proxies correctly
- [ ] CI/CD pipeline runs green on a test commit
- [ ] Security scans fail on critical/high findings
- [ ] Grafana dashboards load with real metrics
- [ ] No `unsafe-inline` or `unsafe-eval` in CSP headers

---

*Plan generated: April 6, 2026*
*For use with Claude Code to systematically implement production readiness improvements*
