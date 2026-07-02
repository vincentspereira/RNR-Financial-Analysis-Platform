/**
 * IBKR Trading Page
 *
 * Real Interactive Brokers Paper Trading (via TWS / IB Gateway on port 7497).
 * Backend endpoints under /api/v1/ibkr/*. See IBKR_SETUP.md for TWS setup.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Wifi,
  WifiOff,
  RefreshCw,
  Plus,
  X,
  AlertTriangle,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';

// --------------------------------------------------------------------------
// Types (mirror backend/app/schemas/ibkr.py)
// --------------------------------------------------------------------------
interface IBKRStatus {
  state: 'disabled' | 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'failed';
  host: string;
  port: number;
  client_id: number;
  account_id: string | null;
  readonly: boolean;
  last_error: string | null;
  reconnect_attempts: number;
  server_version: number | null;
}

interface AccountSummary {
  account: string;
  net_liquidation: number | null;
  total_cash_value: number | null;
  buying_power: number | null;
  available_funds: number | null;
  excess_liquidity: number | null;
  gross_position_value: number | null;
  unrealized_pnl: number | null;
  realized_pnl: number | null;
  currency: string | null;
}

interface IBKRPosition {
  account: string;
  symbol: string;
  sec_type: string;
  exchange: string;
  currency: string;
  quantity: number;
  avg_cost: number;
}

interface IBKROrder {
  id: string;
  client_order_id: string;
  ib_order_id: number | null;
  symbol: string;
  action: string;
  order_type: string;
  quantity: string;
  limit_price: string | null;
  stop_price: string | null;
  status: string;
  filled_quantity: string;
  avg_fill_price: string | null;
  notional_usd_at_submit: string | null;
  last_error: string | null;
  submitted_at: string;
  updated_at: string;
}

interface OrderForm {
  symbol: string;
  action: 'BUY' | 'SELL';
  order_type: 'market' | 'limit' | 'stop' | 'stop_limit';
  quantity: string;
  limit_price: string;
  stop_price: string;
  time_in_force: 'DAY' | 'GTC';
}

// --------------------------------------------------------------------------
// Tiny formatter helpers
// --------------------------------------------------------------------------
const fmtUsd = (v: number | null | undefined): string =>
  v == null ? '—' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v);

const fmtNum = (v: string | number | null | undefined, digits = 4): string => {
  if (v == null) return '—';
  const n = typeof v === 'string' ? parseFloat(v) : v;
  return Number.isFinite(n) ? n.toFixed(digits) : '—';
};

const statusBadgeClass = (status: string): string => {
  switch (status) {
    case 'filled':
      return 'bg-green-100 text-green-800';
    case 'submitted':
    case 'partially_filled':
    case 'pending_submit':
      return 'bg-blue-100 text-blue-800';
    case 'pending_cancel':
      return 'bg-yellow-100 text-yellow-800';
    case 'cancelled':
      return 'bg-gray-100 text-gray-800';
    case 'rejected':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

// --------------------------------------------------------------------------
// Component
// --------------------------------------------------------------------------
export function IBKR() {
  const [status, setStatus] = useState<IBKRStatus | null>(null);
  const [account, setAccount] = useState<AccountSummary | null>(null);
  const [positions, setPositions] = useState<IBKRPosition[]>([]);
  const [orders, setOrders] = useState<IBKROrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [showOrderForm, setShowOrderForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [orderForm, setOrderForm] = useState<OrderForm>({
    symbol: '',
    action: 'BUY',
    order_type: 'market',
    quantity: '',
    limit_price: '',
    stop_price: '',
    time_in_force: 'DAY',
  });

  const refreshStatus = useCallback(async () => {
    try {
      const res = await apiService.request<IBKRStatus>({
        method: 'GET',
        url: '/api/v1/ibkr/status',
      });
      setStatus(res.data);
    } catch (e: any) {
      console.error('status', e);
    }
  }, []);

  const refreshAccount = useCallback(async () => {
    try {
      const res = await apiService.request<AccountSummary>({
        method: 'GET',
        url: '/api/v1/ibkr/account',
      });
      setAccount(res.data);
    } catch (e: any) {
      // Silently ignore — account is only available when connected
      setAccount(null);
    }
  }, []);

  const refreshPositions = useCallback(async () => {
    try {
      const res = await apiService.request<{ positions: IBKRPosition[] }>({
        method: 'GET',
        url: '/api/v1/ibkr/positions',
      });
      setPositions(res.data.positions);
    } catch (e: any) {
      setPositions([]);
    }
  }, []);

  const refreshOrders = useCallback(async () => {
    try {
      const res = await apiService.request<{ orders: IBKROrder[] }>({
        method: 'GET',
        url: '/api/v1/ibkr/orders?include_closed=true&limit=50',
      });
      setOrders(res.data.orders);
    } catch (e: any) {
      setOrders([]);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setLoading(true);
    try {
      await refreshStatus();
      await Promise.all([refreshAccount(), refreshPositions(), refreshOrders()]);
    } finally {
      setLoading(false);
    }
  }, [refreshStatus, refreshAccount, refreshPositions, refreshOrders]);

  useEffect(() => {
    refreshAll();
    const interval = setInterval(refreshAll, 15000); // poll every 15s
    return () => clearInterval(interval);
  }, [refreshAll]);

  const handleConnect = async () => {
    setLoading(true);
    try {
      await apiService.request({ method: 'POST', url: '/api/v1/ibkr/connect' });
      toast.success('Connected to TWS');
      await refreshAll();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Connect failed');
      await refreshStatus();
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await apiService.request({ method: 'POST', url: '/api/v1/ibkr/disconnect' });
      toast.success('Disconnected');
      await refreshStatus();
    } catch (e: any) {
      toast.error('Disconnect failed');
    }
  };

  const handleSyncOrders = async () => {
    try {
      const res = await apiService.request<{ updated: number }>({
        method: 'POST',
        url: '/api/v1/ibkr/orders/sync',
      });
      toast.success(`Synced ${res.data.updated} order(s)`);
      await refreshOrders();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Sync failed');
    }
  };

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orderForm.symbol || !orderForm.quantity) {
      toast.error('Symbol and quantity are required');
      return;
    }
    setSubmitting(true);
    try {
      const body: any = {
        symbol: orderForm.symbol.toUpperCase(),
        action: orderForm.action,
        order_type: orderForm.order_type,
        quantity: parseFloat(orderForm.quantity),
        time_in_force: orderForm.time_in_force,
      };
      if (orderForm.order_type === 'limit' || orderForm.order_type === 'stop_limit') {
        body.limit_price = parseFloat(orderForm.limit_price);
      }
      if (orderForm.order_type === 'stop' || orderForm.order_type === 'stop_limit') {
        body.stop_price = parseFloat(orderForm.stop_price);
      }
      await apiService.request({
        method: 'POST',
        url: '/api/v1/ibkr/orders',
        data: body,
      });
      toast.success(`Order submitted: ${body.action} ${body.quantity} ${body.symbol}`);
      setShowOrderForm(false);
      setOrderForm({
        symbol: '',
        action: 'BUY',
        order_type: 'market',
        quantity: '',
        limit_price: '',
        stop_price: '',
        time_in_force: 'DAY',
      });
      await Promise.all([refreshOrders(), refreshPositions(), refreshAccount()]);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Order rejected');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelOrder = async (orderId: string) => {
    if (!window.confirm('Cancel this order?')) return;
    try {
      await apiService.request({
        method: 'DELETE',
        url: `/api/v1/ibkr/orders/${orderId}`,
      });
      toast.success('Cancel sent');
      await refreshOrders();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Cancel failed');
    }
  };

  const isConnected = status?.state === 'connected';
  const isDisabled = status?.state === 'disabled';
  const canPlaceOrder = isConnected && !status?.readonly;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">IBKR Paper Trading</h1>
          <p className="text-sm text-gray-600 mt-1">
            Real orders against your Interactive Brokers Paper Trading account via TWS.
          </p>
        </div>
        <button
          onClick={refreshAll}
          disabled={loading}
          className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium hover:bg-gray-50 flex items-center gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Connection card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            {isConnected ? (
              <Wifi className="h-5 w-5 text-green-600" />
            ) : (
              <WifiOff className="h-5 w-5 text-gray-400" />
            )}
            <div>
              <div className="font-medium text-gray-900">
                {isDisabled
                  ? 'IBKR integration disabled'
                  : isConnected
                  ? `Connected to ${status?.host}:${status?.port}`
                  : `Disconnected`}
              </div>
              {status && (
                <div className="text-sm text-gray-500">
                  client_id={status.client_id} · account={status.account_id || 'default'} · readonly={String(status.readonly)} · state={status.state}
                  {status.server_version ? ` · TWS v${status.server_version}` : ''}
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!isConnected && !isDisabled && (
              <button
                onClick={handleConnect}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin inline" /> : 'Connect'}
              </button>
            )}
            {isConnected && (
              <button
                onClick={handleDisconnect}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-300"
              >
                Disconnect
              </button>
            )}
          </div>
        </div>
        {status?.last_error && (
          <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-md flex items-start gap-2">
            <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-red-800">{status.last_error}</div>
          </div>
        )}
        {isDisabled && (
          <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md text-sm text-yellow-800">
            Set <code>IBKR_ENABLED=true</code> in <code>.env</code> and restart the backend. See{' '}
            <code>IBKR_SETUP.md</code> for TWS configuration.
          </div>
        )}
        {isConnected && status?.readonly && (
          <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-md text-sm text-blue-800 flex items-start gap-2">
            <CheckCircle2 className="h-4 w-4 mt-0.5" />
            Read-only mode. Set <code>IBKR_READONLY=false</code> in <code>.env</code> to enable order placement.
          </div>
        )}
      </div>

      {/* Account summary */}
      {isConnected && account && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Account Summary{account.account ? ` — ${account.account}` : ''}</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Net Liquidation" value={fmtUsd(account.net_liquidation)} />
            <Stat label="Buying Power" value={fmtUsd(account.buying_power)} />
            <Stat label="Cash" value={fmtUsd(account.total_cash_value)} />
            <Stat label="Available Funds" value={fmtUsd(account.available_funds)} />
            <Stat label="Gross Position Value" value={fmtUsd(account.gross_position_value)} />
            <Stat label="Excess Liquidity" value={fmtUsd(account.excess_liquidity)} />
            <Stat label="Unrealized P&L" value={fmtUsd(account.unrealized_pnl)} />
            <Stat label="Realized P&L" value={fmtUsd(account.realized_pnl)} />
          </div>
        </div>
      )}

      {/* Positions */}
      {isConnected && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Positions ({positions.length})</h2>
          {positions.length === 0 ? (
            <p className="text-sm text-gray-500">No open positions.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <Th>Symbol</Th>
                    <Th>Type</Th>
                    <Th>Exchange</Th>
                    <Th>Currency</Th>
                    <Th className="text-right">Quantity</Th>
                    <Th className="text-right">Avg Cost</Th>
                    <Th className="text-right">Cost Basis</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {positions.map((p) => (
                    <tr key={`${p.account}-${p.symbol}-${p.sec_type}`}>
                      <Td className="font-medium">{p.symbol}</Td>
                      <Td>{p.sec_type}</Td>
                      <Td>{p.exchange}</Td>
                      <Td>{p.currency}</Td>
                      <Td className="text-right">{fmtNum(p.quantity, 2)}</Td>
                      <Td className="text-right">{fmtUsd(p.avg_cost)}</Td>
                      <Td className="text-right">{fmtUsd(p.quantity * p.avg_cost)}</Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Place order */}
      {canPlaceOrder && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Place Order</h2>
            <button
              onClick={() => setShowOrderForm(!showOrderForm)}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 flex items-center gap-1"
            >
              {showOrderForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
              {showOrderForm ? 'Cancel' : 'New Order'}
            </button>
          </div>
          {showOrderForm && (
            <form onSubmit={handlePlaceOrder} className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Field label="Symbol">
                <input
                  type="text"
                  value={orderForm.symbol}
                  onChange={(e) => setOrderForm({ ...orderForm, symbol: e.target.value })}
                  className="form-input w-full"
                  placeholder="AAPL"
                  required
                />
              </Field>
              <Field label="Action">
                <select
                  value={orderForm.action}
                  onChange={(e) => setOrderForm({ ...orderForm, action: e.target.value as any })}
                  className="form-select w-full"
                >
                  <option>BUY</option>
                  <option>SELL</option>
                </select>
              </Field>
              <Field label="Type">
                <select
                  value={orderForm.order_type}
                  onChange={(e) => setOrderForm({ ...orderForm, order_type: e.target.value as any })}
                  className="form-select w-full"
                >
                  <option value="market">Market</option>
                  <option value="limit">Limit</option>
                  <option value="stop">Stop</option>
                  <option value="stop_limit">Stop-Limit</option>
                </select>
              </Field>
              <Field label="Quantity">
                <input
                  type="number"
                  min="0"
                  step="any"
                  value={orderForm.quantity}
                  onChange={(e) => setOrderForm({ ...orderForm, quantity: e.target.value })}
                  className="form-input w-full"
                  required
                />
              </Field>
              {(orderForm.order_type === 'limit' || orderForm.order_type === 'stop_limit') && (
                <Field label="Limit Price">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={orderForm.limit_price}
                    onChange={(e) => setOrderForm({ ...orderForm, limit_price: e.target.value })}
                    className="form-input w-full"
                    required
                  />
                </Field>
              )}
              {(orderForm.order_type === 'stop' || orderForm.order_type === 'stop_limit') && (
                <Field label="Stop Price">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={orderForm.stop_price}
                    onChange={(e) => setOrderForm({ ...orderForm, stop_price: e.target.value })}
                    className="form-input w-full"
                    required
                  />
                </Field>
              )}
              <Field label="Time-in-Force">
                <select
                  value={orderForm.time_in_force}
                  onChange={(e) => setOrderForm({ ...orderForm, time_in_force: e.target.value as any })}
                  className="form-select w-full"
                >
                  <option value="DAY">DAY</option>
                  <option value="GTC">GTC</option>
                </select>
              </Field>
              <div className="col-span-2 md:col-span-4 flex justify-end">
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin inline" /> : 'Submit Order'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* Orders */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Orders ({orders.length})</h2>
          {isConnected && (
            <button
              onClick={handleSyncOrders}
              className="px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm font-medium hover:bg-gray-50"
            >
              Sync from IBKR
            </button>
          )}
        </div>
        {orders.length === 0 ? (
          <p className="text-sm text-gray-500">No orders yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <Th>Submitted</Th>
                  <Th>Symbol</Th>
                  <Th>Action</Th>
                  <Th>Type</Th>
                  <Th className="text-right">Qty</Th>
                  <Th className="text-right">Filled</Th>
                  <Th className="text-right">Avg Fill</Th>
                  <Th>Status</Th>
                  <Th></Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {orders.map((o) => {
                  const isOpen = ['pending_submit', 'submitted', 'partially_filled'].includes(o.status);
                  return (
                    <tr key={o.id}>
                      <Td className="text-xs text-gray-500 whitespace-nowrap">
                        {new Date(o.submitted_at).toLocaleString()}
                      </Td>
                      <Td className="font-medium">{o.symbol}</Td>
                      <Td className={o.action === 'BUY' ? 'text-green-700' : 'text-red-700'}>
                        {o.action}
                      </Td>
                      <Td>{o.order_type}</Td>
                      <Td className="text-right">{fmtNum(o.quantity, 2)}</Td>
                      <Td className="text-right">{fmtNum(o.filled_quantity, 2)}</Td>
                      <Td className="text-right">{o.avg_fill_price ? fmtUsd(parseFloat(o.avg_fill_price)) : '—'}</Td>
                      <Td>
                        <span className={`px-2 py-1 text-xs rounded ${statusBadgeClass(o.status)}`}>
                          {o.status}
                        </span>
                      </Td>
                      <Td>
                        {isOpen && canPlaceOrder && (
                          <button
                            onClick={() => handleCancelOrder(o.id)}
                            className="text-xs text-red-600 hover:text-red-800"
                          >
                            Cancel
                          </button>
                        )}
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
// Small helpers
// --------------------------------------------------------------------------
const Stat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="border border-gray-100 rounded-md p-3">
    <div className="text-xs uppercase text-gray-500">{label}</div>
    <div className="mt-1 text-lg font-semibold text-gray-900">{value}</div>
  </div>
);

const Th: React.FC<{ children?: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <th className={`px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${className}`}>
    {children}
  </th>
);

const Td: React.FC<{ children?: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <td className={`px-3 py-2 whitespace-nowrap ${className}`}>{children}</td>
);

const Field: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <label className="block">
    <span className="text-xs font-medium text-gray-700">{label}</span>
    <div className="mt-1">{children}</div>
  </label>
);

export default IBKR;
