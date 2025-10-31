/**
 * Analytics Dashboard with ML predictions and insights
 */
import React, { useState, useEffect } from 'react';
import { cn } from '@/utils/cn';

// Mock data interfaces (in a real app, these would come from API)
interface StockPrediction {
  symbol: string;
  predicted_price: number;
  confidence_score: number;
  current_price: number;
  prediction_date: string;
  model_used: string;
  days_ahead: number;
}

interface PortfolioRisk {
  var_95: number;
  var_99: number;
  expected_return: number;
  volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
  predicted_risk_score: number;
}

interface TradingSignal {
  symbol: string;
  current_signal: 'BUY' | 'SELL' | 'HOLD';
  signal_strength: number;
  confidence: number;
  technical_indicators: Record<string, number>;
}

interface PortfolioOptimization {
  optimized_weights: Record<string, number>;
  expected_annual_return: number;
  expected_annual_risk: number;
  sharpe_ratio: number;
  recommendation: string;
}

// Analytics Card Component
interface AnalyticsCardProps {
  title: string;
  children: React.ReactNode;
  className?: string;
  loading?: boolean;
}

const AnalyticsCard: React.FC<AnalyticsCardProps> = ({ 
  title, 
  children, 
  className = '', 
  loading = false 
}) => (
  <div className={cn('bg-white rounded-lg shadow-sm border border-gray-200 p-6', className)}>
    <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
    {loading ? (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    ) : (
      children
    )}
  </div>
);

// Stock Prediction Component
const StockPredictionCard: React.FC = () => {
  const [predictions, setPredictions] = useState<StockPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');

  useEffect(() => {
    // Mock data - in real app, fetch from API
    setTimeout(() => {
      setPredictions([
        {
          symbol: 'AAPL',
          predicted_price: 185.50,
          confidence_score: 0.78,
          current_price: 178.25,
          prediction_date: new Date().toISOString(),
          model_used: 'Random Forest',
          days_ahead: 30
        },
        {
          symbol: 'GOOGL',
          predicted_price: 142.80,
          confidence_score: 0.72,
          current_price: 138.90,
          prediction_date: new Date().toISOString(),
          model_used: 'Gradient Boosting',
          days_ahead: 30
        },
        {
          symbol: 'MSFT',
          predicted_price: 378.20,
          confidence_score: 0.81,
          current_price: 372.15,
          prediction_date: new Date().toISOString(),
          model_used: 'Random Forest',
          days_ahead: 30
        }
      ]);
      setLoading(false);
    }, 1000);
  }, []);

  const selectedPrediction = predictions.find(p => p.symbol === selectedSymbol);
  const priceChange = selectedPrediction 
    ? ((selectedPrediction.predicted_price - selectedPrediction.current_price) / selectedPrediction.current_price) * 100
    : 0;

  return (
    <AnalyticsCard title="Stock Price Predictions" loading={loading}>
      <div className="space-y-4">
        {/* Symbol Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Stock
          </label>
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            {predictions.map(pred => (
              <option key={pred.symbol} value={pred.symbol}>
                {pred.symbol}
              </option>
            ))}
          </select>
        </div>

        {selectedPrediction && (
          <div className="space-y-3">
            {/* Current vs Predicted Price */}
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-600">Current Price</div>
                <div className="text-xl font-semibold text-gray-900">
                  ${selectedPrediction.current_price.toFixed(2)}
                </div>
              </div>
              <div className="text-center p-3 bg-blue-50 rounded-lg">
                <div className="text-sm text-gray-600">Predicted Price (30d)</div>
                <div className="text-xl font-semibold text-blue-600">
                  ${selectedPrediction.predicted_price.toFixed(2)}
                </div>
              </div>
            </div>

            {/* Price Change */}
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600">Expected Change</div>
              <div className={cn(
                'text-lg font-semibold',
                priceChange >= 0 ? 'text-green-600' : 'text-red-600'
              )}>
                {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}%
              </div>
            </div>

            {/* Confidence Score */}
            <div>
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>Confidence Score</span>
                <span>{(selectedPrediction.confidence_score * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full"
                  style={{ width: `${selectedPrediction.confidence_score * 100}%` }}
                />
              </div>
            </div>

            {/* Model Info */}
            <div className="text-xs text-gray-500 text-center">
              Model: {selectedPrediction.model_used} | 
              Prediction for {selectedPrediction.days_ahead} days ahead
            </div>
          </div>
        )}
      </div>
    </AnalyticsCard>
  );
};

// Portfolio Risk Analysis Component
const PortfolioRiskCard: React.FC = () => {
  const [riskData, setRiskData] = useState<PortfolioRisk | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock data - in real app, fetch from API
    setTimeout(() => {
      setRiskData({
        var_95: -0.045,
        var_99: -0.078,
        expected_return: 0.085,
        volatility: 0.152,
        sharpe_ratio: 0.559,
        max_drawdown: -0.123,
        predicted_risk_score: 0.62
      });
      setLoading(false);
    }, 1200);
  }, []);

  const getRiskLevel = (score: number) => {
    if (score < 0.3) return { level: 'Low', color: 'text-green-600', bg: 'bg-green-50' };
    if (score < 0.7) return { level: 'Medium', color: 'text-yellow-600', bg: 'bg-yellow-50' };
    return { level: 'High', color: 'text-red-600', bg: 'bg-red-50' };
  };

  return (
    <AnalyticsCard title="Portfolio Risk Analysis" loading={loading}>
      {riskData && (
        <div className="space-y-4">
          {/* Risk Score */}
          <div className="text-center">
            <div className="text-sm text-gray-600 mb-2">Overall Risk Score</div>
            <div className={cn(
              'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium',
              getRiskLevel(riskData.predicted_risk_score).bg,
              getRiskLevel(riskData.predicted_risk_score).color
            )}>
              {getRiskLevel(riskData.predicted_risk_score).level} Risk
            </div>
          </div>

          {/* Risk Metrics Grid */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-gray-600">VaR (95%)</div>
              <div className="font-semibold text-red-600">
                {(riskData.var_95 * 100).toFixed(2)}%
              </div>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-gray-600">VaR (99%)</div>
              <div className="font-semibold text-red-600">
                {(riskData.var_99 * 100).toFixed(2)}%
              </div>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-gray-600">Expected Return</div>
              <div className="font-semibold text-green-600">
                {(riskData.expected_return * 100).toFixed(2)}%
              </div>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-gray-600">Volatility</div>
              <div className="font-semibold text-gray-900">
                {(riskData.volatility * 100).toFixed(2)}%
              </div>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-gray-600">Sharpe Ratio</div>
              <div className="font-semibold text-blue-600">
                {riskData.sharpe_ratio.toFixed(3)}
              </div>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-gray-600">Max Drawdown</div>
              <div className="font-semibold text-red-600">
                {(riskData.max_drawdown * 100).toFixed(2)}%
              </div>
            </div>
          </div>
        </div>
      )}
    </AnalyticsCard>
  );
};

// Trading Signals Component
const TradingSignalsCard: React.FC = () => {
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock data - in real app, fetch from API
    setTimeout(() => {
      setSignals([
        {
          symbol: 'AAPL',
          current_signal: 'BUY',
          signal_strength: 0.78,
          confidence: 0.82,
          technical_indicators: { rsi: 45.2, macd: 1.23, sma_20: 175.50 }
        },
        {
          symbol: 'GOOGL',
          current_signal: 'HOLD',
          signal_strength: 0.45,
          confidence: 0.67,
          technical_indicators: { rsi: 52.8, macd: -0.45, sma_20: 140.25 }
        },
        {
          symbol: 'MSFT',
          current_signal: 'SELL',
          signal_strength: 0.65,
          confidence: 0.74,
          technical_indicators: { rsi: 68.9, macd: -2.15, sma_20: 375.80 }
        }
      ]);
      setLoading(false);
    }, 800);
  }, []);

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'BUY': return 'text-green-600 bg-green-50';
      case 'SELL': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <AnalyticsCard title="Trading Signals" loading={loading}>
      <div className="space-y-3">
        {signals.map((signal) => (
          <div key={signal.symbol} className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="font-semibold text-gray-900">{signal.symbol}</div>
              <div className={cn(
                'px-2 py-1 rounded text-sm font-medium',
                getSignalColor(signal.current_signal)
              )}>
                {signal.current_signal}
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-600">Strength:</span>
                <span className="ml-1 font-medium">
                  {(signal.signal_strength * 100).toFixed(0)}%
                </span>
              </div>
              <div>
                <span className="text-gray-600">Confidence:</span>
                <span className="ml-1 font-medium">
                  {(signal.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div>
                <span className="text-gray-600">RSI:</span>
                <span className="ml-1 font-medium">
                  {signal.technical_indicators.rsi.toFixed(1)}
                </span>
              </div>
              <div>
                <span className="text-gray-600">MACD:</span>
                <span className="ml-1 font-medium">
                  {signal.technical_indicators.macd.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </AnalyticsCard>
  );
};

// Portfolio Optimization Component
const PortfolioOptimizationCard: React.FC = () => {
  const [optimization, setOptimization] = useState<PortfolioOptimization | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock data - in real app, fetch from API
    setTimeout(() => {
      setOptimization({
        optimized_weights: {
          'AAPL': 0.25,
          'GOOGL': 0.20,
          'MSFT': 0.22,
          'TSLA': 0.15,
          'AMZN': 0.18
        },
        expected_annual_return: 0.095,
        expected_annual_risk: 0.168,
        sharpe_ratio: 0.565,
        recommendation: 'Balanced allocation with tech focus for moderate risk tolerance'
      });
      setLoading(false);
    }, 1500);
  }, []);

  return (
    <AnalyticsCard title="Portfolio Optimization" loading={loading}>
      {optimization && (
        <div className="space-y-4">
          {/* Optimized Weights */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Recommended Allocation</h4>
            <div className="space-y-2">
              {Object.entries(optimization.optimized_weights).map(([symbol, weight]) => (
                <div key={symbol} className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900">{symbol}</span>
                  <div className="flex items-center space-x-2">
                    <div className="w-20 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${weight * 100}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-600 w-12 text-right">
                      {(weight * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Expected Metrics */}
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div className="text-center p-3 bg-green-50 rounded-lg">
              <div className="text-gray-600">Expected Return</div>
              <div className="font-semibold text-green-600">
                {(optimization.expected_annual_return * 100).toFixed(1)}%
              </div>
            </div>
            <div className="text-center p-3 bg-yellow-50 rounded-lg">
              <div className="text-gray-600">Expected Risk</div>
              <div className="font-semibold text-yellow-600">
                {(optimization.expected_annual_risk * 100).toFixed(1)}%
              </div>
            </div>
            <div className="text-center p-3 bg-blue-50 rounded-lg">
              <div className="text-gray-600">Sharpe Ratio</div>
              <div className="font-semibold text-blue-600">
                {optimization.sharpe_ratio.toFixed(3)}
              </div>
            </div>
          </div>

          {/* Recommendation */}
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-600 mb-1">AI Recommendation</div>
            <div className="text-sm text-gray-900">{optimization.recommendation}</div>
          </div>
        </div>
      )}
    </AnalyticsCard>
  );
};

// Main Analytics Dashboard Component
export const AnalyticsDashboard: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Advanced Analytics</h1>
          <p className="text-gray-600">AI-powered insights and predictions for your portfolio</p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1 text-sm text-green-600">
            <div className="w-2 h-2 bg-green-600 rounded-full"></div>
            <span>ML Models Active</span>
          </div>
        </div>
      </div>

      {/* Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StockPredictionCard />
        <PortfolioRiskCard />
        <TradingSignalsCard />
        <PortfolioOptimizationCard />
      </div>

      {/* Additional Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-medium text-blue-800">About ML Predictions</h3>
            <p className="text-sm text-blue-700 mt-1">
              Our machine learning models analyze historical data, technical indicators, and market patterns 
              to provide predictions and insights. All predictions include confidence scores and should be 
              used as part of a comprehensive investment strategy.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;