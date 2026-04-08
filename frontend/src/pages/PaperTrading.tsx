/**
 * Paper Trading Simulator Page Component
 */
import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Plus,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  Trophy,
  RefreshCw,
  X,
} from 'lucide-react';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';

interface Position {
  symbol: string;
  side: string;
  quantity: number;
  avg_entry_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  cost_basis: number;
}

interface Trade {
  id: string;
  symbol: string;
  side: string;
  order_type: string;
  quantity: number;
  fill_price: number;
  total_value: number;
  commission: number;
  timestamp: string;
  status: string;
}

interface PaperPortfolio {
  id: string;
  user_id: string;
  name: string;
  initial_capital: number;
  cash_balance: number;
  positions: Position[];
  total_value: number;
  total_pnl: number;
  total_pnl_percent: number;
  total_trades: number;
  win_rate: number;
  created_at: string;
}

interface LeaderboardEntry {
  user_name: string;
  total_pnl_percent: number;
  total_value: number;
  win_rate: number;
}

// Order form state
interface OrderForm {
  symbol: string;
  side: string;
  order_type: string;
  quantity: string;
  price: string;
}

export function PaperTrading() {
  const [portfolio, setPortfolio] = useState<PaperPortfolio | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showOrderForm, setShowOrderForm] = useState(false);
  const [orderForm, setOrderForm] = useState<OrderForm>({
    symbol: '',
    side: 'buy',
    order_type: 'market',
    quantity: '',
    price: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadPortfolio();
  }, []);

  const loadPortfolio = async () => {
    try {
      setIsLoading(true);
      const [portfolioRes, tradesRes, leaderboardRes] = await Promise.allSettled([
        apiService.request({ method: 'GET', url: '/api/v1/paper-trading/portfolio' }),
        apiService.request({ method: 'GET', url: '/api/v1/paper-trading/trades' }),
        apiService.request({ method: 'GET', url: '/api/v1/paper-trading/leaderboard' }),
      ]);

      if (portfolioRes.status === 'fulfilled' && portfolioRes.value.data) {
        setPortfolio(portfolioRes.value.data);
      }
      if (tradesRes.status === 'fulfilled' && tradesRes.value.data) {
        setTrades(tradesRes.value.data || []);
      }
      if (leaderboardRes.status === 'fulfilled' && leaderboardRes.value.data) {
        setLeaderboard(leaderboardRes.value.data || []);
      }
    } catch (error) {
      console.error('Failed to load paper trading data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createPortfolio = async () => {
    try {
      const response = await apiService.request({
        method: 'POST',
        url: '/api/v1/paper-trading/portfolios',
        data: { name: 'My Paper Portfolio', initial_capital: 100000 },
      });
      if (response.data) {
        setPortfolio(response.data);
        toast.success('Paper trading portfolio created with $100,000');
      }
    } catch (error) {
      toast.error('Failed to create portfolio');
    }
  };

  const submitOrder = async () => {
    try {
      setIsSubmitting(true);
      const response = await apiService.request({
        method: 'POST',
        url: '/api/v1/paper-trading/orders',
        data: {
          symbol: orderForm.symbol.toUpperCase(),
          side: orderForm.side,
          order_type: orderForm.order_type,
          quantity: parseFloat(orderForm.quantity),
          price: orderForm.price ? parseFloat(orderForm.price) : undefined,
        },
      });
      if (response.data) {
        toast.success(
          `Order filled: ${orderForm.side.toUpperCase()} ${orderForm.quantity} ${orderForm.symbol.toUpperCase()} @ $${response.data.fill_price?.toFixed(2) || 'market'}`
        );
        setShowOrderForm(false);
        setOrderForm({ symbol: '', side: 'buy', order_type: 'market', quantity: '', price: '' });
        loadPortfolio();
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Order failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const closePosition = async (symbol: string) => {
    try {
      await apiService.request({
        method: 'POST',
        url: `/api/v1/paper-trading/positions/${symbol}/close`,
      });
      toast.success(`Closed position: ${symbol}`);
      loadPortfolio();
    } catch (error) {
      toast.error('Failed to close position');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="text-center py-12">
        <LineChart className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Start Paper Trading</h3>
        <p className="text-gray-600 mb-6">
          Practice trading with $100,000 in virtual money. No risk, real market experience.
        </p>
        <button
          onClick={createPortfolio}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4 mr-2" />
          Create Paper Portfolio
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Paper Trading</h1>
          <p className="mt-1 text-sm text-gray-600">
            Practice trading strategies with virtual money
          </p>
        </div>
        <div className="mt-4 sm:mt-0 flex items-center space-x-3">
          <button
            onClick={loadPortfolio}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 bg-white hover:bg-gray-50"
          >
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </button>
          <button
            onClick={() => setShowOrderForm(!showOrderForm)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Place Order
          </button>
        </div>
      </div>

      {/* Portfolio Summary Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <DollarSign className="h-6 w-6 text-gray-400" />
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Value</dt>
                  <dd className="text-lg font-medium text-gray-900">
                    ${portfolio.total_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <DollarSign className="h-6 w-6 text-gray-400" />
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Cash Balance</dt>
                  <dd className="text-lg font-medium text-gray-900">
                    ${portfolio.cash_balance.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              {portfolio.total_pnl >= 0 ? (
                <TrendingUp className="h-6 w-6 text-green-500" />
              ) : (
                <TrendingDown className="h-6 w-6 text-red-500" />
              )}
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total P&L</dt>
                  <dd className={`text-lg font-medium ${portfolio.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {portfolio.total_pnl >= 0 ? '+' : ''}${portfolio.total_pnl.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    <span className="text-sm ml-1">
                      ({portfolio.total_pnl_percent >= 0 ? '+' : ''}{portfolio.total_pnl_percent.toFixed(2)}%)
                    </span>
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <Target className="h-6 w-6 text-gray-400" />
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Win Rate</dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {(portfolio.win_rate * 100).toFixed(1)}%
                  </dd>
                  <dd className="text-sm text-gray-500">
                    {portfolio.total_trades} total trades
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Order Form */}
      {showOrderForm && (
        <div className="bg-white shadow rounded-lg p-6 border border-indigo-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">Place Order</h3>
            <button onClick={() => setShowOrderForm(false)}>
              <X className="h-5 w-5 text-gray-400" />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Symbol</label>
              <input
                type="text"
                value={orderForm.symbol}
                onChange={(e) => setOrderForm({ ...orderForm, symbol: e.target.value.toUpperCase() })}
                placeholder="AAPL"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Side</label>
              <select
                value={orderForm.side}
                onChange={(e) => setOrderForm({ ...orderForm, side: e.target.value })}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              >
                <option value="buy">Buy</option>
                <option value="sell">Sell</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select
                value={orderForm.order_type}
                onChange={(e) => setOrderForm({ ...orderForm, order_type: e.target.value })}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              >
                <option value="market">Market</option>
                <option value="limit">Limit</option>
                <option value="stop">Stop</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Quantity</label>
              <input
                type="number"
                value={orderForm.quantity}
                onChange={(e) => setOrderForm({ ...orderForm, quantity: e.target.value })}
                placeholder="100"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Price {orderForm.order_type === 'market' ? '(optional)' : '(required)'}
              </label>
              <input
                type="number"
                value={orderForm.price}
                onChange={(e) => setOrderForm({ ...orderForm, price: e.target.value })}
                placeholder="150.00"
                disabled={orderForm.order_type === 'market'}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm disabled:bg-gray-100"
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <button
              onClick={submitOrder}
              disabled={isSubmitting || !orderForm.symbol || !orderForm.quantity}
              className={`px-4 py-2 rounded-md text-sm font-medium text-white disabled:opacity-50 ${
                orderForm.side === 'buy' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'
              }`}
            >
              {isSubmitting ? 'Submitting...' : `${orderForm.side === 'buy' ? 'Buy' : 'Sell'} ${orderForm.symbol || '...'}`}
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Positions Table */}
        <div className="lg:col-span-2 bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Open Positions</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Side</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Qty</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Entry</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Current</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">P&L</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Action</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {portfolio.positions && portfolio.positions.length > 0 ? (
                  portfolio.positions.map((pos) => (
                    <tr key={pos.symbol} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">{pos.symbol}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          pos.side === 'long' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {pos.side.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 text-right">{pos.quantity}</td>
                      <td className="px-6 py-4 text-sm text-gray-900 text-right">${pos.avg_entry_price.toFixed(2)}</td>
                      <td className="px-6 py-4 text-sm text-gray-900 text-right">${pos.current_price.toFixed(2)}</td>
                      <td className={`px-6 py-4 text-sm text-right font-medium ${
                        pos.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {pos.unrealized_pnl >= 0 ? '+' : ''}${pos.unrealized_pnl.toFixed(2)}
                        <span className="text-xs ml-1">({pos.unrealized_pnl_percent.toFixed(2)}%)</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => closePosition(pos.symbol)}
                          className="text-red-600 hover:text-red-800 text-xs font-medium"
                        >
                          Close
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-sm text-gray-500">
                      No open positions. Place an order to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Leaderboard */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6 border-b border-gray-200">
            <div className="flex items-center space-x-2">
              <Trophy className="h-5 w-5 text-yellow-500" />
              <h3 className="text-lg font-medium text-gray-900">Leaderboard</h3>
            </div>
          </div>
          <div className="divide-y divide-gray-200">
            {leaderboard.length > 0 ? (
              leaderboard.map((entry, index) => (
                <div key={index} className="px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className={`text-sm font-bold ${
                      index === 0 ? 'text-yellow-500' : index === 1 ? 'text-gray-400' : index === 2 ? 'text-orange-400' : 'text-gray-400'
                    }`}>
                      #{index + 1}
                    </span>
                    <span className="text-sm font-medium text-gray-900">{entry.user_name}</span>
                  </div>
                  <span className={`text-sm font-medium ${entry.total_pnl_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {entry.total_pnl_percent >= 0 ? '+' : ''}{entry.total_pnl_percent.toFixed(2)}%
                  </span>
                </div>
              ))
            ) : (
              <div className="px-4 py-8 text-center text-sm text-gray-500">
                No leaderboard data yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Trade History */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Trade History</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Side</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Qty</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Price</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {trades.length > 0 ? (
                trades.map((trade) => (
                  <tr key={trade.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {new Date(trade.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{trade.symbol}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        trade.side === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {trade.side.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 capitalize">{trade.order_type}</td>
                    <td className="px-6 py-4 text-sm text-gray-900 text-right">{trade.quantity}</td>
                    <td className="px-6 py-4 text-sm text-gray-900 text-right">${trade.fill_price.toFixed(2)}</td>
                    <td className="px-6 py-4 text-sm text-gray-900 text-right">
                      ${trade.total_value.toFixed(2)}
                      <span className="text-xs text-gray-400 ml-1">(fee: ${trade.commission.toFixed(2)})</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                        {trade.status}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="px-6 py-8 text-center text-sm text-gray-500">
                    No trades yet. Place your first order above.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
