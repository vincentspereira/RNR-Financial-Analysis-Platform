/**
 * Watchlist Management Types and Interfaces
 */

export interface WatchlistItem {
  id: string;
  company_id: string;
  symbol: string;
  company_name: string;
  sector: string;
  current_price: number;
  price_change: number;
  price_change_percentage: number;
  volume: number;
  market_cap: number;
  added_date: string;
  last_updated: string;
  alerts: Alert[];
  notes?: string;
  tags: string[];
}

export interface Watchlist {
  id: string;
  name: string;
  description?: string;
  category: WatchlistCategory;
  items: WatchlistItem[];
  created_at: string;
  updated_at: string;
  is_public: boolean;
  user_id: string;
  color?: string;
  sort_order: number;
}

export interface WatchlistCategory {
  id: string;
  name: string;
  description?: string;
  color: string;
  icon?: string;
  created_at: string;
}

export interface Alert {
  id: string;
  watchlist_item_id: string;
  alert_type: AlertType;
  condition: AlertCondition;
  threshold_value: number;
  current_value: number;
  is_active: boolean;
  is_triggered: boolean;
  created_at: string;
  triggered_at?: string;
  notification_methods: NotificationMethod[];
  message?: string;
}

export type AlertType = 
  | 'price_above'
  | 'price_below'
  | 'price_change_percentage'
  | 'volume_spike'
  | 'market_cap_change'
  | 'news_sentiment'
  | 'analyst_rating'
  | 'earnings_date'
  | 'dividend_date'
  | 'technical_indicator';

export type AlertCondition = 
  | 'greater_than'
  | 'less_than'
  | 'equals'
  | 'percentage_change'
  | 'crosses_above'
  | 'crosses_below';

export type NotificationMethod = 
  | 'email'
  | 'push'
  | 'sms'
  | 'in_app'
  | 'webhook';

export interface AlertTemplate {
  id: string;
  name: string;
  description: string;
  alert_type: AlertType;
  default_condition: AlertCondition;
  default_threshold?: number;
  is_system_template: boolean;
}

export interface WatchlistFilter {
  categories?: string[];
  sectors?: string[];
  price_range?: { min?: number; max?: number };
  market_cap_range?: { min?: number; max?: number };
  change_percentage_range?: { min?: number; max?: number };
  has_alerts?: boolean;
  tags?: string[];
  search_query?: string;
}

export interface WatchlistSort {
  field: 'symbol' | 'company_name' | 'current_price' | 'price_change_percentage' | 'volume' | 'market_cap' | 'added_date';
  direction: 'asc' | 'desc';
}

export interface WatchlistStats {
  total_items: number;
  total_value: number;
  average_change: number;
  gainers: number;
  losers: number;
  active_alerts: number;
  triggered_alerts: number;
}

export interface MarketData {
  symbol: string;
  price: number;
  change: number;
  change_percentage: number;
  volume: number;
  high_52_week: number;
  low_52_week: number;
  market_cap: number;
  pe_ratio?: number;
  dividend_yield?: number;
  last_updated: string;
}

export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  url: string;
  source: string;
  published_at: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  sentiment_score: number;
  symbols: string[];
  categories: string[];
}

export interface TechnicalIndicator {
  symbol: string;
  indicator_type: 'sma' | 'ema' | 'rsi' | 'macd' | 'bollinger_bands' | 'stochastic';
  value: number;
  signal: 'buy' | 'sell' | 'hold';
  strength: number;
  calculated_at: string;
}

// API Request/Response Types
export interface CreateWatchlistRequest {
  name: string;
  description?: string;
  category_id: string;
  is_public?: boolean;
  color?: string;
}

export interface AddToWatchlistRequest {
  watchlist_id: string;
  symbol: string;
  notes?: string;
  tags?: string[];
}

export interface CreateAlertRequest {
  watchlist_item_id: string;
  alert_type: AlertType;
  condition: AlertCondition;
  threshold_value: number;
  notification_methods: NotificationMethod[];
  message?: string;
}

export interface WatchlistResponse {
  watchlists: Watchlist[];
  categories: WatchlistCategory[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface AlertNotification {
  id: string;
  alert_id: string;
  symbol: string;
  company_name: string;
  alert_type: AlertType;
  message: string;
  current_value: number;
  threshold_value: number;
  triggered_at: string;
  is_read: boolean;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

// Real-time Data Types
export interface RealtimeUpdate {
  symbol: string;
  price: number;
  change: number;
  change_percentage: number;
  volume: number;
  timestamp: string;
  market_status: 'open' | 'closed' | 'pre_market' | 'after_hours';
}

export interface WebSocketMessage {
  type: 'price_update' | 'alert_triggered' | 'news_update' | 'market_status';
  data: RealtimeUpdate | AlertNotification | NewsItem | any;
  timestamp: string;
}

// Configuration Types
export interface WatchlistSettings {
  auto_refresh_interval: number; // seconds
  default_notification_methods: NotificationMethod[];
  price_precision: number;
  show_after_hours: boolean;
  show_pre_market: boolean;
  default_sort: WatchlistSort;
  items_per_page: number;
  enable_sound_alerts: boolean;
  alert_cooldown_period: number; // minutes
}

export interface DataSourceConfig {
  provider: 'alpha_vantage' | 'yahoo_finance' | 'iex_cloud' | 'polygon' | 'finnhub';
  api_key: string;
  rate_limit: number;
  is_active: boolean;
  priority: number;
  supported_features: string[];
  last_sync: string;
  error_count: number;
}