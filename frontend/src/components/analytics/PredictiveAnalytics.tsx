/**
 * Predictive Analytics Component
 */
import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Brain,
  Target,
  Shield,
  Eye,
  AlertTriangle,
  Activity,
  BarChart3,
  Zap,
  Calendar,
  Filter,
  RefreshCw,
} from 'lucide-react';
import {
  MarketTrend,
  SentimentAnalysis,
  RiskAssessment,
  AnomalyDetection,
  Prediction,
  TimeFrame,
} from '@/types/analytics';
import { FinancialChart } from '@/components/charts/FinancialChart';
import toast from 'react-hot-toast';
import { apiService } from '@/services/api';

interface PredictiveAnalyticsProps {
  symbol?: string;
  timeframe?: TimeFrame;
}

export function PredictiveAnalytics({ symbol = 'AAPL', timeframe = '1m' }: PredictiveAnalyticsProps) {
  const [activeTab, setActiveTab] = useState<'trends' | 'sentiment' | 'risk' | 'anomalies'>('trends');
  const [trends, setTrends] = useState<MarketTrend[]>([]);
  const [sentiment, setSentiment] = useState<SentimentAnalysis | null>(null);
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessment | null>(null);
  const [anomalies, setAnomalies] = useState<AnomalyDetection[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [selectedTimeframe, setSelectedTimeframe] = useState<TimeFrame>(timeframe);
  const [isLoading, setIsLoading] = useState(true);

  // Mock data for demonstration
  const mockTrends: MarketTrend[] = [
    {
      id: '1',
      symbol: symbol,
      timeframe: '1m',
      trend_direction: 'bullish',
      strength: 0.78,
      confidence: 0.85,
      support_levels: [190.50, 185.20, 180.00],
      resistance_levels: [205.00, 210.50, 215.80],
      key_indicators: [
        { name: 'RSI', value: 62.3, signal: 'buy', strength: 0.7, description: 'Momentum indicator showing bullish momentum' },
        { name: 'MACD', value: 1.23, signal: 'buy', strength: 0.8, description: 'Moving average convergence showing positive crossover' },
        { name: 'Bollinger Bands', value: 0.65, signal: 'hold', strength: 0.6, description: 'Price near upper band, potential resistance' },
      ],
      predicted_duration: 14,
      risk_factors: ['Market volatility', 'Earnings announcement', 'Fed policy changes'],
      created_at: '2023-12-01T10:00:00Z',
    },
    {
      id: '2',
      symbol: symbol,
      timeframe: '3m',
      trend_direction: 'bullish',
      strength: 0.65,
      confidence: 0.72,
      support_levels: [185.00, 175.50, 165.00],
      resistance_levels: [220.00, 235.00, 250.00],
      key_indicators: [
        { name: 'Moving Average', value: 195.50, signal: 'buy', strength: 0.75, description: '50-day MA trending upward' },
        { name: 'Volume Profile', value: 1.2, signal: 'buy', strength: 0.65, description: 'Above-average volume supporting trend' },
      ],
      predicted_duration: 45,
      risk_factors: ['Sector rotation', 'Economic indicators', 'Geopolitical events'],
      created_at: '2023-12-01T10:00:00Z',
    },
  ];

  const mockSentiment: SentimentAnalysis = {
    id: '1',
    symbol: symbol,
    overall_sentiment: { score: 0.65, label: 'positive', confidence: 0.82 },
    news_sentiment: { score: 0.72, label: 'positive', confidence: 0.88 },
    social_sentiment: { score: 0.58, label: 'positive', confidence: 0.75 },
    analyst_sentiment: { score: 0.68, label: 'positive', confidence: 0.91 },
    sentiment_trend: { direction: 'improving', momentum: 0.15, volatility: 0.23 },
    key_themes: ['Product Innovation', 'Market Expansion', 'Financial Performance', 'AI Integration'],
    sentiment_drivers: [
      { theme: 'Product Innovation', impact: 0.8, sentiment: 0.75, mentions: 156, sources: ['TechCrunch', 'Reuters', 'Bloomberg'] },
      { theme: 'Financial Performance', impact: 0.7, sentiment: 0.68, mentions: 89, sources: ['WSJ', 'Financial Times', 'CNBC'] },
      { theme: 'Market Expansion', impact: 0.6, sentiment: 0.62, mentions: 67, sources: ['Forbes', 'MarketWatch'] },
    ],
    confidence: 0.82,
    analysis_date: '2023-12-01T10:00:00Z',
  };

  const mockRiskAssessment: RiskAssessment = {
    id: '1',
    symbol: symbol,
    overall_risk: 'medium',
    risk_factors: [
      { factor: 'Market Volatility', impact: 0.7, probability: 0.6, description: 'Increased market volatility due to economic uncertainty', mitigation: 'Diversification and hedging strategies' },
      { factor: 'Sector Concentration', impact: 0.5, probability: 0.8, description: 'High exposure to technology sector', mitigation: 'Sector diversification' },
      { factor: 'Liquidity Risk', impact: 0.3, probability: 0.4, description: 'Potential liquidity constraints during market stress', mitigation: 'Maintain cash reserves' },
    ],
    risk_score: 0.62,
    var_95: -0.08,
    expected_shortfall: -0.12,
    beta: 1.15,
    volatility: 0.28,
    correlation_matrix: { 'SPY': 0.85, 'QQQ': 0.92, 'VTI': 0.88 },
    stress_test_results: [
      { scenario: 'Market Crash (-20%)', impact: -0.23, probability: 0.05, description: 'Severe market downturn scenario' },
      { scenario: 'Interest Rate Spike', impact: -0.15, probability: 0.15, description: 'Rapid interest rate increases' },
      { scenario: 'Recession', impact: -0.18, probability: 0.25, description: 'Economic recession scenario' },
    ],
    recommendations: [
      'Consider reducing position size during high volatility periods',
      'Implement stop-loss orders to limit downside risk',
      'Monitor correlation with market indices',
      'Review portfolio diversification regularly',
    ],
    assessment_date: '2023-12-01T10:00:00Z',
  };

  const mockAnomalies: AnomalyDetection[] = [
    {
      id: '1',
      symbol: symbol,
      anomaly_type: 'volume_anomaly',
      severity: 'medium',
      anomaly_score: 0.73,
      description: 'Unusual trading volume spike detected - 3x normal volume',
      detected_at: '2023-12-01T09:30:00Z',
      features_affected: ['volume', 'price_velocity'],
      potential_causes: ['News announcement', 'Institutional trading', 'Options expiry'],
      recommended_actions: ['Monitor for news catalysts', 'Check options activity', 'Review institutional flows'],
      false_positive_probability: 0.15,
    },
    {
      id: '2',
      symbol: symbol,
      anomaly_type: 'price_spike',
      severity: 'low',
      anomaly_score: 0.45,
      description: 'Minor price deviation from expected range',
      detected_at: '2023-12-01T11:15:00Z',
      features_affected: ['price', 'momentum'],
      potential_causes: ['Market microstructure', 'Algorithmic trading'],
      recommended_actions: ['Continue monitoring', 'Check for pattern confirmation'],
      false_positive_probability: 0.35,
    },
  ];

  useEffect(() => {
    loadPredictiveAnalytics();
  }, [symbol, selectedTimeframe]);

  const loadPredictiveAnalytics = async () => {
    try {
      setIsLoading(true);

      // Fetch real predictive analytics from API
      const response = await apiService.request({
        method: 'GET',
        url: '/api/v1/analytics/predictions/history',
        params: { symbol, timeframe: selectedTimeframe },
      });

      if (response.data) {
        setTrends(response.data.trends || []);
        setSentiment(response.data.sentiment || null);
        setRiskAssessment(response.data.risk_assessment || null);
        setAnomalies(response.data.anomalies || []);
      }

    } catch (error) {
      console.error('Failed to load predictive analytics:', error);
      toast.error('Failed to load predictive analytics');
      setIsLoading(false);
    }
  };

  const getTrendIcon = (direction: string) => {
    switch (direction) {
      case 'bullish':
        return <TrendingUp className="h-5 w-5 text-green-500" />;
      case 'bearish':
        return <TrendingDown className="h-5 w-5 text-red-500" />;
      default:
        return <Activity className="h-5 w-5 text-gray-500" />;
    }
  };

  const getSentimentColor = (score: number) => {
    if (score >= 0.6) return 'text-green-600 bg-green-100';
    if (score >= 0.2) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'very_low':
      case 'low':
        return 'text-green-600 bg-green-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'high':
      case 'very_high':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getAnomalySeverityColor = (severity: string) => {
    switch (severity) {
      case 'low':
        return 'text-blue-600 bg-blue-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'high':
        return 'text-orange-600 bg-orange-100';
      case 'critical':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Predictive Analytics</h2>
          <p className="mt-1 text-sm text-gray-600">
            AI-powered insights for {symbol} - Market trends, sentiment, and risk analysis
          </p>
        </div>
        
        <div className="mt-4 sm:mt-0 flex space-x-3">
          <select
            value={selectedTimeframe}
            onChange={(e) => setSelectedTimeframe(e.target.value as TimeFrame)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="1d">1 Day</option>
            <option value="1w">1 Week</option>
            <option value="1m">1 Month</option>
            <option value="3m">3 Months</option>
            <option value="6m">6 Months</option>
            <option value="1y">1 Year</option>
          </select>
          <button
            onClick={loadPredictiveAnalytics}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {[
              { id: 'trends', name: 'Market Trends', icon: TrendingUp },
              { id: 'sentiment', name: 'Sentiment Analysis', icon: Eye },
              { id: 'risk', name: 'Risk Assessment', icon: Shield },
              { id: 'anomalies', name: 'Anomaly Detection', icon: AlertTriangle },
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

        <div className="p-6">
          {/* Market Trends Tab */}
          {activeTab === 'trends' && (
            <div className="space-y-6">
              {trends.map((trend) => (
                <div key={trend.id} className="bg-gray-50 rounded-lg p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center">
                      {getTrendIcon(trend.trend_direction)}
                      <h3 className="ml-3 text-lg font-medium text-gray-900">
                        {trend.timeframe.toUpperCase()} Trend Analysis
                      </h3>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <div className="text-sm text-gray-500">Strength</div>
                        <div className="font-medium text-gray-900">{formatPercentage(trend.strength)}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-gray-500">Confidence</div>
                        <div className="font-medium text-gray-900">{formatPercentage(trend.confidence)}</div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                      <h4 className="font-medium text-gray-900 mb-3">Key Indicators</h4>
                      <div className="space-y-2">
                        {trend.key_indicators.map((indicator, index) => (
                          <div key={index} className="flex items-center justify-between p-2 bg-white rounded">
                            <span className="text-sm font-medium text-gray-700">{indicator.name}</span>
                            <div className="flex items-center">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                indicator.signal === 'buy' ? 'text-green-600 bg-green-100' :
                                indicator.signal === 'sell' ? 'text-red-600 bg-red-100' :
                                'text-gray-600 bg-gray-100'
                              }`}>
                                {indicator.signal}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h4 className="font-medium text-gray-900 mb-3">Support Levels</h4>
                      <div className="space-y-1">
                        {trend.support_levels.map((level, index) => (
                          <div key={index} className="text-sm text-gray-600">
                            ${level.toFixed(2)}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h4 className="font-medium text-gray-900 mb-3">Resistance Levels</h4>
                      <div className="space-y-1">
                        {trend.resistance_levels.map((level, index) => (
                          <div key={index} className="text-sm text-gray-600">
                            ${level.toFixed(2)}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                    <h4 className="font-medium text-blue-900 mb-2">Risk Factors</h4>
                    <div className="flex flex-wrap gap-2">
                      {trend.risk_factors.map((factor, index) => (
                        <span key={index} className="inline-flex px-2 py-1 text-xs font-medium text-blue-700 bg-blue-100 rounded-full">
                          {factor}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Sentiment Analysis Tab */}
          {activeTab === 'sentiment' && sentiment && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-gray-50 rounded-lg p-6 text-center">
                  <div className="text-2xl font-bold text-gray-900 mb-2">
                    {formatPercentage(sentiment.overall_sentiment.score)}
                  </div>
                  <div className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getSentimentColor(sentiment.overall_sentiment.score)}`}>
                    {sentiment.overall_sentiment.label}
                  </div>
                  <div className="text-sm text-gray-600 mt-2">Overall Sentiment</div>
                </div>

                <div className="bg-gray-50 rounded-lg p-6 text-center">
                  <div className="text-2xl font-bold text-gray-900 mb-2">
                    {formatPercentage(sentiment.news_sentiment.score)}
                  </div>
                  <div className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getSentimentColor(sentiment.news_sentiment.score)}`}>
                    {sentiment.news_sentiment.label}
                  </div>
                  <div className="text-sm text-gray-600 mt-2">News Sentiment</div>
                </div>

                <div className="bg-gray-50 rounded-lg p-6 text-center">
                  <div className="text-2xl font-bold text-gray-900 mb-2">
                    {formatPercentage(sentiment.social_sentiment.score)}
                  </div>
                  <div className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getSentimentColor(sentiment.social_sentiment.score)}`}>
                    {sentiment.social_sentiment.label}
                  </div>
                  <div className="text-sm text-gray-600 mt-2">Social Sentiment</div>
                </div>

                <div className="bg-gray-50 rounded-lg p-6 text-center">
                  <div className="text-2xl font-bold text-gray-900 mb-2">
                    {formatPercentage(sentiment.analyst_sentiment.score)}
                  </div>
                  <div className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getSentimentColor(sentiment.analyst_sentiment.score)}`}>
                    {sentiment.analyst_sentiment.label}
                  </div>
                  <div className="text-sm text-gray-600 mt-2">Analyst Sentiment</div>
                </div>
              </div>

              <div className="bg-white rounded-lg border p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Sentiment Drivers</h3>
                <div className="space-y-4">
                  {sentiment.sentiment_drivers.map((driver, index) => (
                    <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900">{driver.theme}</div>
                        <div className="text-sm text-gray-600">{driver.mentions} mentions</div>
                        <div className="flex flex-wrap gap-1 mt-2">
                          {driver.sources.map((source, idx) => (
                            <span key={idx} className="inline-flex px-2 py-1 text-xs text-gray-600 bg-gray-200 rounded">
                              {source}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="text-right ml-4">
                        <div className="text-sm text-gray-500">Impact</div>
                        <div className="font-medium text-gray-900">{formatPercentage(driver.impact)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Risk Assessment Tab */}
          {activeTab === 'risk' && riskAssessment && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-gray-50 rounded-lg p-6 text-center">
                  <div className="text-2xl font-bold text-gray-900 mb-2">
                    {(riskAssessment.risk_score * 100).toFixed(0)}
                  </div>
                  <div className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getRiskColor(riskAssessment.overall_risk)}`}>
                    {riskAssessment.overall_risk} risk
                  </div>
                  <div className="text-sm text-gray-600 mt-2">Risk Score</div>
                </div>

                <div className="bg-gray-50 rounded-lg p-6 text-center">
                  <div className="text-2xl font-bold text-gray-900 mb-2">
                    {formatPercentage(Math.abs(riskAssessment.var_95))}
                  </div>
                  <div className="text-sm text-gray-600">Value at Risk (95%)</div>
                </div>

                <div className="bg-gray-50 rounded-lg p-6 text-center">
                  <div className="text-2xl font-bold text-gray-900 mb-2">
                    {riskAssessment.beta.toFixed(2)}
                  </div>
                  <div className="text-sm text-gray-600">Beta</div>
                </div>
              </div>

              <div className="bg-white rounded-lg border p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Risk Factors</h3>
                <div className="space-y-4">
                  {riskAssessment.risk_factors.map((factor, index) => (
                    <div key={index} className="p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-gray-900">{factor.factor}</h4>
                        <div className="flex space-x-4 text-sm">
                          <span className="text-gray-600">Impact: {formatPercentage(factor.impact)}</span>
                          <span className="text-gray-600">Probability: {formatPercentage(factor.probability)}</span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{factor.description}</p>
                      <p className="text-sm text-blue-600">
                        <strong>Mitigation:</strong> {factor.mitigation}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-lg border p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Recommendations</h3>
                <ul className="space-y-2">
                  {riskAssessment.recommendations.map((recommendation, index) => (
                    <li key={index} className="flex items-start">
                      <Target className="h-4 w-4 text-indigo-500 mt-1 mr-2 flex-shrink-0" />
                      <span className="text-sm text-gray-700">{recommendation}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Anomaly Detection Tab */}
          {activeTab === 'anomalies' && (
            <div className="space-y-6">
              {anomalies.length > 0 ? (
                <div className="space-y-4">
                  {anomalies.map((anomaly) => (
                    <div key={anomaly.id} className="bg-white rounded-lg border p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center">
                          <AlertTriangle className="h-6 w-6 text-orange-500 mr-3" />
                          <div>
                            <h3 className="text-lg font-medium text-gray-900">
                              {anomaly.anomaly_type.replace('_', ' ').toUpperCase()}
                            </h3>
                            <p className="text-sm text-gray-600">{anomaly.description}</p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-4">
                          <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getAnomalySeverityColor(anomaly.severity)}`}>
                            {anomaly.severity}
                          </span>
                          <div className="text-right">
                            <div className="text-sm text-gray-500">Score</div>
                            <div className="font-medium text-gray-900">{(anomaly.anomaly_score * 100).toFixed(0)}</div>
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <h4 className="font-medium text-gray-900 mb-2">Potential Causes</h4>
                          <ul className="space-y-1">
                            {anomaly.potential_causes.map((cause, index) => (
                              <li key={index} className="text-sm text-gray-600">• {cause}</li>
                            ))}
                          </ul>
                        </div>

                        <div>
                          <h4 className="font-medium text-gray-900 mb-2">Recommended Actions</h4>
                          <ul className="space-y-1">
                            {anomaly.recommended_actions.map((action, index) => (
                              <li key={index} className="text-sm text-gray-600">• {action}</li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                        <div className="text-sm text-yellow-800">
                          <strong>False Positive Probability:</strong> {formatPercentage(anomaly.false_positive_probability)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <CheckCircle className="h-12 w-12 text-green-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No Anomalies Detected</h3>
                  <p className="text-gray-600">
                    All market indicators are within normal ranges for {symbol}.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}