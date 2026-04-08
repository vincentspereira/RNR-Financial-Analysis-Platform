/**
 * Risk Dashboard Page Component
 */
import React, { useState } from 'react';
import {
  Shield,
  AlertTriangle,
  TrendingDown,
  Activity,
  Play,
  BarChart3,
  RefreshCw,
} from 'lucide-react';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';

interface VaRResult {
  method: string;
  confidence_level: number;
  time_horizon_days: number;
  var_amount: number;
  var_percentage: number;
  cvar_amount: number;
  cvar_percentage: number;
}

interface DrawdownResult {
  max_drawdown: number;
  max_drawdown_duration_days: number;
  current_drawdown: number;
  recovery_time_days: number | null;
}

interface RiskScore {
  overall_score: number;
  volatility_risk: number;
  concentration_risk: number;
  liquidity_risk: number;
  market_risk: number;
  rating: string;
}

interface StressTestResult {
  scenario: string;
  description: string;
  portfolio_impact_percentage: number;
  portfolio_impact_amount: number;
  worst_position: string;
  worst_position_impact: number;
}

interface RiskAnalysis {
  portfolio_id: string;
  timestamp: string;
  var_analysis: VaRResult;
  drawdown: DrawdownResult;
  risk_score: RiskScore;
  stress_tests: StressTestResult[];
  risk_factors: Record<string, number>;
}

const STRESS_SCENARIO_ICONS: Record<string, string> = {
  market_crash: '📉',
  interest_rate_hike: '📈',
  recession: '🔄',
  inflation_spike: '💸',
  black_swan: '🦢',
};

function getRiskColor(score: number): string {
  if (score <= 25) return 'text-green-600';
  if (score <= 50) return 'text-yellow-600';
  if (score <= 75) return 'text-orange-600';
  return 'text-red-600';
}

function getRiskBg(score: number): string {
  if (score <= 25) return 'bg-green-100';
  if (score <= 50) return 'bg-yellow-100';
  if (score <= 75) return 'bg-orange-100';
  return 'bg-red-100';
}

function getImpactColor(impact: number): string {
  if (impact >= -5) return 'text-green-600';
  if (impact >= -15) return 'text-yellow-600';
  if (impact >= -30) return 'text-orange-600';
  return 'text-red-600';
}

export function RiskDashboard() {
  const [analysis, setAnalysis] = useState<RiskAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [method, setMethod] = useState('historical');
  const [confidence, setConfidence] = useState(95);
  const [portfolioId, setPortfolioId] = useState('default');

  const runAnalysis = async () => {
    try {
      setIsLoading(true);
      const response = await apiService.request({
        method: 'POST',
        url: '/api/v1/risk/analyze',
        data: {
          portfolio_id: portfolioId,
          method,
          confidence_level: confidence / 100,
          time_horizon_days: 1,
          include_stress_tests: true,
        },
      });
      if (response.data) {
        setAnalysis(response.data);
        toast.success('Risk analysis completed');
      }
    } catch (error) {
      console.error('Risk analysis failed:', error);
      toast.error('Failed to run risk analysis');
    } finally {
      setIsLoading(false);
    }
  };

  const score = analysis?.risk_score;
  const varResult = analysis?.var_analysis;
  const drawdown = analysis?.drawdown;
  const stressTests = analysis?.stress_tests || [];
  const riskFactors = analysis?.risk_factors || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Risk Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">
            Portfolio risk analysis, stress testing, and VaR calculations
          </p>
        </div>
        <div className="mt-4 sm:mt-0 flex items-center space-x-3">
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
          >
            <option value="historical">Historical VaR</option>
            <option value="parametric">Parametric VaR</option>
            <option value="monte_carlo">Monte Carlo VaR</option>
          </select>
          <select
            value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))}
            className="rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
          >
            <option value={90}>90% Confidence</option>
            <option value={95}>95% Confidence</option>
            <option value={99}>99% Confidence</option>
          </select>
          <button
            onClick={runAnalysis}
            disabled={isLoading}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
          >
            {isLoading ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Run Analysis
          </button>
        </div>
      </div>

      {/* Risk Score & VaR Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {/* Overall Risk Score */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Shield className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Risk Score</dt>
                  <dd className={`text-2xl font-bold ${score ? getRiskColor(score.overall_score) : 'text-gray-400'}`}>
                    {score ? `${score.overall_score.toFixed(0)} (${score.rating})` : '--'}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* VaR Amount */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <AlertTriangle className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    VaR ({confidence}%)
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {varResult ? `$${varResult.var_amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '--'}
                  </dd>
                  <dd className="text-sm text-gray-500">
                    {varResult ? `${varResult.var_percentage.toFixed(2)}%` : ''}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* Max Drawdown */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <TrendingDown className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Max Drawdown</dt>
                  <dd className="text-lg font-medium text-red-600">
                    {drawdown ? `${drawdown.max_drawdown.toFixed(2)}%` : '--'}
                  </dd>
                  <dd className="text-sm text-gray-500">
                    {drawdown ? `${drawdown.max_drawdown_duration_days} days duration` : ''}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* CVaR / Expected Shortfall */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Activity className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">CVaR (Expected Shortfall)</dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {varResult ? `$${varResult.cvar_amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '--'}
                  </dd>
                  <dd className="text-sm text-gray-500">
                    {varResult ? `${varResult.cvar_percentage.toFixed(2)}%` : ''}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Factors Breakdown */}
      {score && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Risk Factor Breakdown</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: 'Volatility Risk', value: score.volatility_risk },
                { label: 'Concentration Risk', value: score.concentration_risk },
                { label: 'Liquidity Risk', value: score.liquidity_risk },
                { label: 'Market Risk', value: score.market_risk },
              ].map((factor) => (
                <div key={factor.label} className="relative">
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">{factor.label}</span>
                    <span className={`text-sm font-medium ${getRiskColor(factor.value)}`}>
                      {factor.value.toFixed(0)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        factor.value <= 25 ? 'bg-green-500' :
                        factor.value <= 50 ? 'bg-yellow-500' :
                        factor.value <= 75 ? 'bg-orange-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min(factor.value, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Stress Test Scenarios */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Stress Test Scenarios</h3>
          {stressTests.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {stressTests.map((test) => (
                <div
                  key={test.scenario}
                  className={`rounded-lg p-4 border ${
                    test.portfolio_impact_percentage >= -10
                      ? 'border-green-200 bg-green-50'
                      : test.portfolio_impact_percentage >= -25
                      ? 'border-yellow-200 bg-yellow-50'
                      : 'border-red-200 bg-red-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-900">
                      {STRESS_SCENARIO_ICONS[test.scenario] || '⚠️'}{' '}
                      {test.scenario.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mb-3">{test.description}</p>
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-500">Portfolio Impact</span>
                      <span className={`text-sm font-semibold ${getImpactColor(test.portfolio_impact_percentage)}`}>
                        {test.portfolio_impact_percentage.toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-500">Amount</span>
                      <span className="text-sm font-medium text-gray-700">
                        ${Math.abs(test.portfolio_impact_amount).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-500">Worst Position</span>
                      <span className="text-xs font-medium text-gray-700">
                        {test.worst_position} ({test.worst_position_impact.toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <BarChart3 className="h-10 w-10 mx-auto mb-2 text-gray-300" />
              <p>Run an analysis to see stress test results</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
