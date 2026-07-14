# IBKR Paper Trading — Setup Guide

This document walks you through connecting the RNR Financial Analysis Platform's
backend to your Interactive Brokers Paper Trading account via Trader Workstation
(TWS). End state: you can place real (paper) orders from the IBKR Trading page
in the web UI, and every order is persisted to the platform database.

**Time required:** ~20 minutes, one-time setup.

---

## Prerequisites

1. **An Interactive Brokers account.** Sign up at https://www.interactivebrokers.com
   if you don't have one. Paper trading is free once your account is approved.
2. **Your paper account number.** Format `DUxxxxxxx` (the "DU" prefix indicates
   demo / paper). Find it under Account > Account Management > Settings.
3. **Trader Workstation (TWS) installed.** Download from
   https://www.interactivebrokers.com/en/trading/tws.php
   - Pick the **Stable** build (not Latest) — the API is more reliable.
   - Windows build is fine for this guide.
4. **Python 3.11+ in your backend venv** (you have 3.14 available as `python3`).

---

## Step 1: Install the `ib-async` dependency

The backend now lists `ib-async` in `backend/requirements.txt`. Install it into
the backend venv:

```bash
# Recreate the venv (the committed one has Windows paths that do not work in WSL)
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
```

Verify:

```bash
python -c "import ib_async; print(ib_async.__version__)"
```

You should see a version like `1.0.x`.

---

## Step 2: Launch TWS in Paper Trading mode

1. Launch **Trader Workstation**.
2. On the login screen, toggle **"Paper Trading"** (top-right area).
3. Log in with your **paper** credentials. Your paper account number begins with `DU`.
4. Wait for the trading window to open.

---

## Step 3: Enable the API socket

In TWS:

1. **File > Global Configuration** (or `Edit > Global Configuration` on Mac).
2. Navigate to **API > Settings**:

   | Setting | Value |
   |---|---|
   | Enable ActiveX and Socket Clients | **CHECKED** |
   | Read-Only API | **UNCHECKED** (only when you're ready to place orders) |
   | Socket port | **7497** (paper). Live mode would be 7496. |
   | Master API client ID | (leave blank) |
   | Allow connections from localhost only | **CHECKED** (security) |
   | Bypass Order Precautions for API Orders | UNCHECKED (keep IBKR's safety checks) |
   | Send instrument-specific attributes | CHECKED (default) |

3. Click **OK**. TWS may prompt to restart — restart it.

4. Navigate to **API > Precautions** and review:
   - "Bypass Bond warning for API Orders" — leave default.
   - "Bypass negative yield to worst confirmation" — leave default.
   - It's fine to leave the rest at defaults.

5. Navigate to **API > Trusted IPs** and confirm `127.0.0.1` is listed (it usually
   is by default).

---

## Step 4: Configure the platform's `.env`

In the project root, edit (or create) `.env` based on `.env.example`. The IBKR
section should look like this:

```
IBKR_ENABLED=true
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_CLIENT_ID=42
IBKR_ACCOUNT_ID=DU1234567        # YOUR paper account number
IBKR_READONLY=true                # KEEP TRUE until you have placed at least one test connection
IBKR_RECONNECT_DELAY_SECONDS=5
IBKR_MAX_RECONNECT_ATTEMPTS=10
IBKR_ORDER_DAILY_LIMIT=50         # safety brake
IBKR_ORDER_NOTIONAL_LIMIT_USD=100000
```

**Notes:**
- `IBKR_CLIENT_ID` can be any integer 1–32 — but each concurrent client needs a
  unique ID. If you ever connect from multiple places at once (e.g., a notebook
  and the backend), give them different IDs.
- `IBKR_READONLY=true` will allow the backend to **read** account / positions /
  market data but will **reject all order placements** with a 403. Recommended
  for your first few sessions to confirm everything works.

---

## Step 5: Apply database migration

The integration adds an `ibkr_orders` table. Run alembic upgrade:

```bash
source venv/bin/activate
cd backend
alembic upgrade head
```

You should see `b2c3d4e5f6a7_add_ibkr_orders` applied.

---

## Step 6: Start the backend

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open another shell for the frontend:

```bash
cd frontend
npm install        # if you haven't already
npm run dev
```

---

## Step 7: Verify the connection in the UI

1. Open http://localhost:3030/ (or whatever `FRONTEND_PORT` is set to).
2. Log in.
3. Navigate to **IBKR Trading** in the left nav.
4. Click **Connect**.

You should see:
- State = `connected`
- TWS server version (e.g., `TWS v179`)
- Account Summary populated with your paper-account balances
- Positions table (empty unless you've already placed orders in TWS)

If you see `last_error` saying "could not connect", check:
- TWS is running and you're logged into the paper account.
- Port 7497 is actually shown in TWS API > Settings.
- Windows Firewall isn't blocking TWS.
- `IBKR_CLIENT_ID` isn't already used by another process.

---

## Step 8: Place your first test order (read-only off)

Once `state=connected` and you've reviewed everything:

1. Stop the backend.
2. Edit `.env` and set `IBKR_READONLY=false`.
3. Restart the backend.
4. In the UI, the read-only banner should disappear and "New Order" form appears.
5. Place a **small** market order:
   - Symbol: `AAPL`
   - Action: BUY
   - Type: market
   - Quantity: `1`
6. The order appears in the Orders table. Within seconds, IBKR should fill it
   and the status flips to `filled` with an `avg_fill_price`.
7. The Positions table now shows 1 share of AAPL.
8. The Account Summary's Net Liquidation should be unchanged (cash → position
   conversion).

---

## Step 9: Monitor the safety brake

Every order increments per-user counters:
- Daily order count (max = `IBKR_ORDER_DAILY_LIMIT`)
- Daily notional USD (max = `IBKR_ORDER_NOTIONAL_LIMIT_USD`)

Hitting either cap returns HTTP 429 from `POST /api/v1/ibkr/orders` and the
reason is displayed as a toast in the UI. Counters reset at 00:00 UTC.

To change a cap, edit `.env` and restart the backend.

---

## Operational gotchas

- **TWS auto-logs out daily.** By default TWS auto-logs out around 22:30 ET. Set
  Configure > Lock and Exit > "Auto restart" to keep it running 24/7. Note that
  paper trading is only meaningful during US market hours unless your strategies
  trade other exchanges.
- **Market data subscriptions.** Paper trading uses delayed quotes by default
  (15-min delay for US equities). For live quotes you need to subscribe to
  market data in IBKR Account Management — and pay per-exchange fees.
- **Restarting the backend.** The backend reconnects lazily — the first IBKR-
  touching request after a restart will trigger a fresh connect. If you want
  eager reconnection, hit `POST /api/v1/ibkr/connect` from the UI.
- **Multiple backend instances.** If you scale to >1 backend replica, each
  replica needs a unique `IBKR_CLIENT_ID`. TWS rejects duplicate IDs.

---

## Going live (NOT recommended yet)

When (and only when) you want to move from paper to live:
1. Open a live account separately and fund it.
2. In TWS, log into the **Live** account (NOT paper).
3. Set `IBKR_PORT=7496` (live).
4. Set `IBKR_ACCOUNT_ID` to your live account (no `DU` prefix).
5. **Set `IBKR_ORDER_NOTIONAL_LIMIT_USD` to something appropriate to live capital.**
6. Set `IBKR_READONLY=true` initially. Verify status, positions, and account
   summary all read correctly.
7. Flip `IBKR_READONLY=false`. Place a tiny test trade first.

Live trading involves real money. Audit every step. See the `LICENSE` file
clause on "no investment advice" — this platform is a tool, not a strategy.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `Could not connect to TWS / IB Gateway at 127.0.0.1:7497` | TWS is not running, or port is wrong, or "Enable ActiveX and Socket Clients" is off. |
| Connect succeeds but Account Summary is empty | Your account is still onboarding, or you're connected to a different account. Verify `IBKR_ACCOUNT_ID`. |
| `IBKR could not resolve contract AAPL` | Symbol unknown or ambiguous. For unusual tickers, supply explicit `exchange` / `currency`. |
| Order stays in `pending_submit` forever | Check the TWS message window for an Order Precautions popup. Some order types prompt for confirmation in TWS. |
| `Daily order limit reached` | Safety gate fired. Edit `.env` to raise or reset at next UTC midnight. |
| 502 errors after backend restart | Backend lost connection; click **Connect** in the IBKR page, or hit `POST /api/v1/ibkr/connect`. |
