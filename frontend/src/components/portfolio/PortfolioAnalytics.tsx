/**
 * Portfolio Analytics Dashboard Component
 */
import React, { useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Target,
  Shield,
  AlertTriangle,
  BarChart3,
  PieChart,
  Activity,
  Calendar,
} from 'lucide-react';
import { Portfolio, TimeSeriesData, ComparisonChartData } from '@/types/financial';
import { FinancialChart } from '@/components/charts/FinancialChart';

interface PortfolioAnalyticsProps {
  portfolio: Portfolio;
}

interface RiskMetrics {
  beta: number;
  sharpe_ratio: number;
  volatility: number;
  max_drawdown: number;
  var_95: number; // Value at Risk 95%
  correlation_sp500: number;
}

interface PerformanceMetrics {
  ytd_return: number;
  one_year_return: number;
  three_year_return: number;
  five_year_return: number;
  inception_return: number;
  best_month: number;
  worst_month: number;
  win_rate: number;
}

export function PortfolioAnalytics({ portfolio }: PortfolioAnalyticsProps) {
  const [activeTab, setActiveTab] = useState<'performance' | 'risk' | 'allocation' | 'attribution'>('performance');

  // Mock data for demonstration
  const mockRiskMetrics: RiskMetrics = {
    beta: 1.15,
    sharpe_ratio: 1.42,
    volatility: 0.18,
    max_drawdown: -0.12,
    var_95: -0.08,
    correlation_sp500: 0.85,
  };

  const mockPerformanceMetrics: PerformanceMetrics = {
    ytd_return: 0.087,
    one_year_return: 0.156,
    three_year_return: 0.124,
    five_year_return: 0.098,
    inception_return: 0.112,
    best_month: 0.089,
    worst_month: -0.067,
    win_rate: 0.64,
  };

  const mockPerformanceData: TimeSeriesData[] = [
    { date: '2023-01', value: 100000 },
    { date: '2023-02', value: 102500 },
    { date: '2023-03', value: 98750 },
    { date: '2023-04', value: 105200 },
    { date: '2023-05', value: 108900 },
    { date: '2023-06', value: 106300 },
    { date: '2023-07', value: 112100 },
    { date: '2023-08', value: 115600 },
    { date: '2023-09', value: 111800 },
    { date: '2023-10', value: 118400 },
    { date: '2023-11', value: 122700 },
    { date: '2023-12', value: 125000 },
  ];

  const mockBenchmarkComparison: ComparisonChartData[] = [
    { category: 'YTD', company_value: 8.7, peer_average: 6.2, industry_average: 5.8 },
    { category: '1Y', company_value: 15.6, peer_average: 12.3, industry_average: 11.1 },
    { category: '3Y', company_value: 12.4, peer_average: 9.8, industry_average: 8.9 },
    { category: '5Y', company_value: 9.8, peer_average: 8.1, industry_average: 7.6 },
  ];

  const sectorAllocation = portfolio.positions.reduce((acc, position) => {
    const sector = position.company.sector;
    if (!acc[sector]) {
      acc[sector] = 0;
    }
    acc[sector] += position.weight;
    return acc;
  }, {} as Record<string, number>);

  const sectorChartData = Object.entries(sectorAllocation).map(([sector, weight]) => ({
    x: sector,
    y: weight,
    label: sector,
  }));

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const getRiskLevel = (value: number, thresholds: { low: number; medium: number }) => {
    if (value <= thresholds.low) return { level: 'Low', color: 'text-green-600', bg: 'bg-green-100' };
    if (value <= thresholds.medium) return { level: 'Medium', color: 'text-yellow-600', bg: 'bg-yellow-100' };
    return { level: 'High', color: 'text-red-600', bg: 'bg-red-100' };
  };

  return (
    <div className="space-y-6">
      {/* Analytics Header */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Portfolio Analytics</h2>
        
        {/* Tab Navigation */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'performance', name: 'Performance', icon: TrendingUp },
              { id: 'risk', name: 'Risk Analysis', icon: Shield },
              { id: 'allocation', name: 'Allocation', icon: PieChart },
              { id: 'attribution', name: 'Attribution', icon: BarChart3 },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`${
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
              >
                <tab.icon className="h-4 w-4" />
                <span>{tab.name}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Performance Tab */}
      {activeTab === 'performance' && (
        <div className="space-y-6">
          {/* Performance Metrics */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Summary</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {formatPercentage(mockPerformanceMetrics.ytd_return)}
                </div>
                <div className="text-sm text-gray-600">YTD Return</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {formatPercentage(mockPerformanceMetrics.one_year_return)}
                </div>
                <div className="text-sm text-gray-600">1 Year</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {formatPercentage(mockPerformanceMetrics.three_year_return)}
                </div>
                <div className="text-sm text-gray-600">3 Year (Ann.)</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {formatPercentage(mockPerformanceMetrics.inception_return)}
                </div>
                <div className="text-sm text-gray-600">Since Inception</div>
              </div>
            </div>
          </div>

          {/* Performance Chart */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <FinancialChart
              type="line"
              title="Portfolio Value Over Time"
              data={mockPerformanceData}
              currency
              height={300}
            />
            <FinancialChart
              type="bar"
              title="Performance vs Benchmarks"
              data={mockBenchmarkComparison}
              percentage
              height={300}
            />
          </div>

          {/* Additional Performance Metrics */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Additional Metrics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-xl font-bold text-green-600 mb-1">
                  {formatPercentage(mockPerformanceMetrics.best_month)}
                </div>
                <div className="text-sm text-gray-600">Best Month</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-red-600 mb-1">
                  {formatPercentage(mockPerformanceMetrics.worst_month)}
                </div>
                <div className="text-sm text-gray-600">Worst Month</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-gray-900 mb-1">
                  {formatPercentage(mockPerformanceMetrics.win_rate)}
                </div>
                <div className="text-sm text-gray-600">Win Rate</div>
              </div>
              <div className="text-center">
                <div className="text-xl font-bold text-gray-900 mb-1">
                  {mockRiskMetrics.sharpe_ratio.toFixed(2)}
                </div>
                <div className="text-sm text-gray-600">Sharpe Ratio</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Risk Analysis Tab */}
      {activeTab === 'risk' && (
        <div className="space-y-6">
          {/* Risk Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Beta */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Beta</h3>
                <Activity className="h-5 w-5 text-gray-400" />
              </div>
              <div className="text-3xl font-bold text-gray-900 mb-2">
                {mockRiskMetrics.beta.toFixed(2)}
              </div>
              <div className="text-sm text-gray-600">
                {mockRiskMetrics.beta > 1 ? 'More volatile than market' : 'Less volatile than market'}
              </div>
            </div>

            {/* Volatility */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Volatility</h3>
                <AlertTriangle className="h-5 w-5 text-gray-400" />
              </div>
              <div className="text-3xl font-bold text-gray-900 mb-2">
                {formatPercentage(mockRiskMetrics.volatility)}
              </div>
              <div className={`text-sm ${getRiskLevel(mockRiskMetrics.volatility, { low: 0.15, medium: 0.25 }).color}`}>
                {getRiskLevel(mockRiskMetrics.volatility, { low: 0.15, medium: 0.25 }).level} Risk
              </div>
            </div>

            {/* Max Drawdown */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Max Drawdown</h3>
                <TrendingDown className="h-5 w-5 text-gray-400" />
              </div>
              <div className="text-3xl font-bold text-red-600 mb-2">
                {formatPercentage(mockRiskMetrics.max_drawdown)}
              </div>
              <div className="text-sm text-gray-600">
                Largest peak-to-trough decline
              </div>
            </div>

            {/* Value at Risk */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">VaR (95%)</h3>
                <Shield className="h-5 w-5 text-gray-400" />
              </div>
              <div className="text-3xl font-bold text-orange-600 mb-2">
                {formatPercentage(mockRiskMetrics.var_95)}
              </div>
              <div className="text-sm text-gray-600">
                Maximum expected loss (95% confidence)
              </div>
            </div>

            {/* Sharpe Ratio */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Sharpe Ratio</h3>
                <Target className="h-5 w-5 text-gray-400" />
              </div>
              <div className="text-3xl font-bold text-green-600 mb-2">
                {mockRiskMetrics.sharpe_ratio.toFixed(2)}
              </div>
              <div className="text-sm text-gray-600">
                Risk-adjusted return measure
              </div>
            </div>

            {/* Correlation */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">S&P 500 Correlation</h3>
                <BarChart3 className="h-5 w-5 text-gray-400" />
              </div>
              <div className="text-3xl font-bold text-gray-900 mb-2">
                {mockRiskMetrics.correlation_sp500.toFixed(2)}
              </div>
              <div className="text-sm text-gray-600">
                Correlation with market index
              </div>
            </div>
          </div>

          {/* Risk Assessment */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Risk Assessment</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-yellow-50 rounded-lg">
                <div className="flex items-center">
                  <AlertTriangle className="h-5 w-5 text-yellow-600 mr-3" />
                  <div>
                    <div className="font-medium text-gray-900">Moderate Risk Portfolio</div>
                    <div className="text-sm text-gray-600">
                      Higher volatility than market average but good risk-adjusted returns
                    </div>
                  </div>
                </div>
                <div className="text-yellow-600 font-medium">Medium</div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-green-50 rounded-lg">
                  <div className="font-medium text-green-900 mb-2">Strengths</div>
                  <ul className="text-sm text-green-700 space-y-1">
                    <li>• Strong Sharpe ratio indicates good risk-adjusted returns</li>
                    <li>• Reasonable maximum drawdown</li>
                    <li>• Diversified sector allocation</li>
                  </ul>
                </div>
                
                <div className="p-4 bg-red-50 rounded-lg">
                  <div className="font-medium text-red-900 mb-2">Areas for Improvement</div>
                  <ul className="text-sm text-red-700 space-y-1">
                    <li>• Higher volatility than market</li>
                    <li>• High correlation with S&P 500</li>
                    <li>• Consider adding defensive assets</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Allocation Tab */}
      {activeTab === 'allocation' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Sector Allocation */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Sector Allocation</h3>
              <FinancialChart
                type="doughnut"
                title=""
                data={sectorChartData}
                height={300}
                showLegend={true}
              />
            </div>

            {/* Allocation Details */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Allocation Breakdown</h3>
              <div className="space-y-4">
                {Object.entries(sectorAllocation)
                  .sort(([,a], [,b]) => b - a)
                  .map(([sector, weight]) => (
                    <div key={sector} className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div className="w-4 h-4 bg-indigo-500 rounded mr-3"></div>
                        <span className="text-sm font-medium text-gray-900">{sector}</span>
                      </div>
                      <div className="text-sm text-gray-600">
                        {weight.toFixed(1)}%
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Attribution Tab */}
      {activeTab === 'attribution' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Attribution</h3>
            <div className="text-center py-12">
              <Calendar className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-gray-900 mb-2">
                Performance Attribution Analysis
              </h4>
              <p className="text-gray-600">
                Detailed attribution analysis coming soon. This will show how different sectors and positions contributed to overall performance.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PortfolioAnalytics;