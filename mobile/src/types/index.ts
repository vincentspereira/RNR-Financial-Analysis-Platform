export interface Company {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  industry: string;
  market_cap: number;
  description: string;
  exchange: string;
  website: string;
}

export interface MarketData {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  high: number;
  low: number;
  open: number;
  previous_close: number;
  timestamp: string;
}

export interface Portfolio {
  id: string;
  name: string;
  description: string;
  total_value: number;
  total_return: number;
  total_return_percent: number;
  positions: Position[];
  created_at: string;
}

export interface Position {
  symbol: string;
  company_name: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  weight: number;
}

export interface Prediction {
  symbol: string;
  predicted_price: number;
  current_price: number;
  confidence: number;
  days_ahead: number;
  direction: 'up' | 'down';
  change_percent: number;
  model_type: string;
}

export interface SentimentResult {
  overall_score: number;
  overall_label: 'positive' | 'negative' | 'neutral';
  article_count: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  sentiment_trend: 'improving' | 'declining' | 'stable';
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  subscription_tier: 'free' | 'pro' | 'enterprise';
}
