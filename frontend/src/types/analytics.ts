/**
 * Machine Learning and Predictive Analytics Types
 */

export interface MLModel {
  id: string;
  name: string;
  type: ModelType;
  version: string;
  description: string;
  status: ModelStatus;
  accuracy: number;
  last_trained: string;
  training_data_size: number;
  features: string[];
  target_variable: string;
  performance_metrics: ModelMetrics;
  created_at: string;
  updated_at: string;
}

export type ModelType = 
  | 'price_prediction'
  | 'trend_analysis'
  | 'volatility_forecast'
  | 'sentiment_analysis'
  | 'risk_assessment'
  | 'anomaly_detection'
  | 'portfolio_optimization'
  | 'earnings_prediction'
  | 'bankruptcy_prediction'
  | 'market_regime_detection';

export type ModelStatus = 
  | 'training'
  | 'active'
  | 'inactive'
  | 'error'
  | 'deprecated'
  | 'testing';

export interface ModelMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  mse?: number;
  mae?: number;
  r_squared?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  win_rate?: number;
}

export interface Prediction {
  id: string;
  model_id: string;
  symbol: string;
  prediction_type: PredictionType;
  predicted_value: number;
  confidence: number;
  probability_distribution?: number[];
  features_used: Record<string, number>;
  prediction_date: string;
  target_date: string;
  actual_value?: number;
  accuracy?: number;
  explanation?: string;
}

export type PredictionType = 
  | 'price_target'
  | 'trend_direction'
  | 'volatility_level'
  | 'risk_score'
  | 'sentiment_score'
  | 'anomaly_score'
  | 'earnings_surprise'
  | 'bankruptcy_probability';

export interface MarketTrend {
  id: string;
  symbol: string;
  timeframe: TimeFrame;
  trend_direction: TrendDirection;
  strength: number;
  confidence: number;
  support_levels: number[];
  resistance_levels: number[];
  key_indicators: TechnicalIndicator[];
  predicted_duration: number;
  risk_factors: string[];
  created_at: string;
}

export type TimeFrame = '1d' | '1w' | '1m' | '3m' | '6m' | '1y';
export type TrendDirection = 'bullish' | 'bearish' | 'sideways' | 'volatile';

export interface TechnicalIndicator {
  name: string;
  value: number;
  signal: 'buy' | 'sell' | 'hold';
  strength: number;
  description: string;
}

export interface SentimentAnalysis {
  id: string;
  symbol: string;
  overall_sentiment: SentimentScore;
  news_sentiment: SentimentScore;
  social_sentiment: SentimentScore;
  analyst_sentiment: SentimentScore;
  sentiment_trend: SentimentTrend;
  key_themes: string[];
  sentiment_drivers: SentimentDriver[];
  confidence: number;
  analysis_date: string;
}

export interface SentimentScore {
  score: number; // -1 to 1
  label: 'very_negative' | 'negative' | 'neutral' | 'positive' | 'very_positive';
  confidence: number;
}

export interface SentimentTrend {
  direction: 'improving' | 'declining' | 'stable';
  momentum: number;
  volatility: number;
}

export interface SentimentDriver {
  theme: string;
  impact: number;
  sentiment: number;
  mentions: number;
  sources: string[];
}

export interface RiskAssessment {
  id: string;
  symbol: string;
  overall_risk: RiskLevel;
  risk_factors: RiskFactor[];
  risk_score: number;
  var_95: number;
  expected_shortfall: number;
  beta: number;
  volatility: number;
  correlation_matrix: Record<string, number>;
  stress_test_results: StressTestResult[];
  recommendations: string[];
  assessment_date: string;
}

export type RiskLevel = 'very_low' | 'low' | 'medium' | 'high' | 'very_high';

export interface RiskFactor {
  factor: string;
  impact: number;
  probability: number;
  description: string;
  mitigation: string;
}

export interface StressTestResult {
  scenario: string;
  impact: number;
  probability: number;
  description: string;
}

export interface AnomalyDetection {
  id: string;
  symbol: string;
  anomaly_type: AnomalyType;
  severity: 'low' | 'medium' | 'high' | 'critical';
  anomaly_score: number;
  description: string;
  detected_at: string;
  features_affected: string[];
  potential_causes: string[];
  recommended_actions: string[];
  false_positive_probability: number;
}

export type AnomalyType = 
  | 'price_spike'
  | 'volume_anomaly'
  | 'pattern_break'
  | 'correlation_break'
  | 'fundamental_divergence'
  | 'news_impact'
  | 'insider_activity';

export interface PortfolioOptimization {
  id: string;
  portfolio_id: string;
  optimization_type: OptimizationType;
  objective: OptimizationObjective;
  constraints: OptimizationConstraint[];
  current_allocation: Record<string, number>;
  recommended_allocation: Record<string, number>;
  expected_return: number;
  expected_risk: number;
  sharpe_ratio: number;
  improvement_metrics: ImprovementMetric[];
  rebalancing_cost: number;
  confidence: number;
  created_at: string;
}

export type OptimizationType = 
  | 'mean_variance'
  | 'risk_parity'
  | 'black_litterman'
  | 'minimum_variance'
  | 'maximum_sharpe'
  | 'maximum_return';

export interface OptimizationObjective {
  type: 'maximize_return' | 'minimize_risk' | 'maximize_sharpe' | 'target_return' | 'target_risk';
  target_value?: number;
  weight: number;
}

export interface OptimizationConstraint {
  type: 'weight_limit' | 'sector_limit' | 'turnover_limit' | 'tracking_error';
  symbol?: string;
  sector?: string;
  min_value?: number;
  max_value?: number;
}

export interface ImprovementMetric {
  metric: string;
  current_value: number;
  optimized_value: number;
  improvement: number;
  improvement_percentage: number;
}

export interface ModelTraining {
  id: string;
  model_id: string;
  training_status: TrainingStatus;
  progress: number;
  start_time: string;
  end_time?: string;
  training_data: TrainingData;
  hyperparameters: Record<string, any>;
  validation_results: ModelMetrics;
  feature_importance: FeatureImportance[];
  training_logs: TrainingLog[];
  error_message?: string;
}

export type TrainingStatus = 
  | 'queued'
  | 'preprocessing'
  | 'training'
  | 'validating'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface TrainingData {
  source: string;
  size: number;
  features: number;
  start_date: string;
  end_date: string;
  preprocessing_steps: string[];
}

export interface FeatureImportance {
  feature: string;
  importance: number;
  rank: number;
  description: string;
}

export interface TrainingLog {
  timestamp: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  metrics?: Record<string, number>;
}

// API Request/Response Types
export interface PredictionRequest {
  model_id: string;
  symbol: string;
  features?: Record<string, number>;
  prediction_horizon?: number;
  confidence_interval?: number;
}

export interface TrendAnalysisRequest {
  symbol: string;
  timeframe: TimeFrame;
  include_technical_indicators?: boolean;
  include_sentiment?: boolean;
}

export interface RiskAssessmentRequest {
  symbols: string[];
  portfolio_weights?: Record<string, number>;
  time_horizon?: number;
  confidence_level?: number;
}

export interface OptimizationRequest {
  portfolio_id: string;
  optimization_type: OptimizationType;
  objective: OptimizationObjective;
  constraints?: OptimizationConstraint[];
  rebalancing_frequency?: 'daily' | 'weekly' | 'monthly' | 'quarterly';
}

// Real-time Analytics
export interface AnalyticsUpdate {
  type: 'prediction' | 'trend' | 'sentiment' | 'risk' | 'anomaly';
  symbol: string;
  data: Prediction | MarketTrend | SentimentAnalysis | RiskAssessment | AnomalyDetection;
  timestamp: string;
  confidence: number;
}

export interface ModelPerformance {
  model_id: string;
  symbol?: string;
  timeframe: TimeFrame;
  accuracy_trend: number[];
  prediction_count: number;
  correct_predictions: number;
  avg_confidence: number;
  performance_by_market_condition: Record<string, ModelMetrics>;
  recent_predictions: Prediction[];
}

// Configuration
export interface AnalyticsConfig {
  enabled_models: string[];
  prediction_frequency: number;
  confidence_threshold: number;
  alert_thresholds: Record<string, number>;
  feature_selection: string[];
  model_refresh_interval: number;
  performance_monitoring: boolean;
}