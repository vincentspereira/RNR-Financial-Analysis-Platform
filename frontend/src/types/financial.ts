/**
 * Financial Analysis Types and Interfaces
 */

export interface Company {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  industry: string;
  market_cap: number;
  employees?: number;
  founded?: string;
  headquarters?: string;
  website?: string;
  description?: string;
}

export interface FinancialStatement {
  period_type: 'annual' | 'quarterly';
  fiscal_year: number;
  fiscal_quarter?: number;
  currency: string;
  
  // Income Statement
  revenue: number;
  gross_profit: number;
  operating_income: number;
  ebitda: number;
  net_income: number;
  eps: number;
  
  // Balance Sheet
  total_assets: number;
  current_assets: number;
  cash_and_equivalents: number;
  inventory: number;
  total_liabilities: number;
  current_liabilities: number;
  long_term_debt: number;
  shareholders_equity: number;
  
  // Cash Flow
  operating_cash_flow: number;
  investing_cash_flow: number;
  financing_cash_flow: number;
  free_cash_flow: number;
  
  // Per Share Data
  shares_outstanding: number;
  book_value_per_share: number;
  
  // Market Data
  stock_price?: number;
  market_cap?: number;
}

export interface FinancialRatios {
  // Liquidity Ratios
  current_ratio: number;
  quick_ratio: number;
  cash_ratio: number;
  operating_cash_flow_ratio: number;
  
  // Profitability Ratios
  gross_profit_margin: number;
  operating_profit_margin: number;
  net_profit_margin: number;
  return_on_assets: number;
  return_on_equity: number;
  return_on_invested_capital: number;
  
  // Leverage Ratios
  debt_to_equity: number;
  debt_to_assets: number;
  equity_multiplier: number;
  interest_coverage_ratio: number;
  
  // Efficiency Ratios
  asset_turnover: number;
  inventory_turnover: number;
  receivables_turnover: number;
  working_capital_turnover: number;
  
  // Valuation Ratios
  price_to_earnings: number;
  price_to_book: number;
  price_to_sales: number;
  enterprise_value_to_ebitda: number;
  peg_ratio: number;
  
  // Growth Ratios
  revenue_growth: number;
  earnings_growth: number;
  book_value_growth: number;
  
  // Quality Scores
  piotroski_score?: number;
  altman_z_score?: number;
  beneish_m_score?: number;
}

export interface ValuationModel {
  model_type: 'dcf' | 'ddm' | 'graham_number' | 'peg' | 'ev_multiples';
  fair_value: number;
  current_price: number;
  upside_downside: number;
  confidence_level: 'high' | 'medium' | 'low';
  assumptions: Record<string, any>;
}

export interface CompanyAnalysis {
  company: Company;
  financial_statement: FinancialStatement;
  ratios: FinancialRatios;
  valuation_models: ValuationModel[];
  peer_comparison?: PeerComparison;
  analyst_recommendations?: AnalystRecommendation[];
  price_history?: PriceHistory[];
  news_sentiment?: NewsSentiment;
}

export interface PeerComparison {
  peers: Company[];
  metrics: {
    [key: string]: {
      company_value: number;
      peer_average: number;
      peer_median: number;
      percentile: number;
      rank: number;
    };
  };
}

export interface AnalystRecommendation {
  analyst_firm: string;
  recommendation: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell';
  target_price: number;
  date: string;
  reasoning?: string;
}

export interface PriceHistory {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjusted_close?: number;
}

export interface NewsSentiment {
  overall_sentiment: 'positive' | 'neutral' | 'negative';
  sentiment_score: number; // -1 to 1
  news_count: number;
  recent_headlines: string[];
}

export interface Portfolio {
  id: string;
  name: string;
  description?: string;
  total_value: number;
  total_return: number;
  total_return_percentage: number;
  positions: PortfolioPosition[];
  created_at: string;
  updated_at: string;
}

export interface PortfolioPosition {
  id: string;
  company: Company;
  shares: number;
  average_cost: number;
  current_price: number;
  market_value: number;
  unrealized_gain_loss: number;
  unrealized_gain_loss_percentage: number;
  weight: number; // Percentage of portfolio
  purchase_date: string;
}

export interface Watchlist {
  id: string;
  name: string;
  companies: Company[];
  created_at: string;
  updated_at: string;
}

export interface Alert {
  id: string;
  company: Company;
  alert_type: 'price' | 'ratio' | 'news' | 'earnings';
  condition: 'above' | 'below' | 'equals';
  threshold: number;
  current_value: number;
  is_triggered: boolean;
  created_at: string;
  triggered_at?: string;
}

export interface DataSource {
  name: string;
  status: 'active' | 'inactive' | 'error';
  last_update: string;
  api_calls_today: number;
  rate_limit: number;
  error_message?: string;
}

// Chart Data Types
export interface ChartDataPoint {
  x: string | number;
  y: number;
  label?: string;
}

export interface TimeSeriesData {
  date: string;
  value: number;
}

export interface ComparisonChartData {
  category: string;
  company_value: number;
  peer_average: number;
  industry_average?: number;
}

// API Request/Response Types
export interface FinancialAnalysisRequest {
  company_id: string;
  period_type: 'annual' | 'quarterly';
  fiscal_year: number;
  fiscal_quarter?: number;
}

export interface ValuationRequest {
  company_id: string;
  assumptions: {
    free_cash_flows?: number[];
    terminal_growth_rate?: number;
    discount_rate?: number;
    dividend_growth_rate?: number;
    required_return?: number;
  };
}

export interface PeerComparisonRequest {
  company_id: string;
  peer_ids?: string[];
  metrics: string[];
}

// Filter and Search Types
export interface CompanyFilter {
  sectors?: string[];
  market_cap_min?: number;
  market_cap_max?: number;
  pe_ratio_min?: number;
  pe_ratio_max?: number;
  debt_to_equity_max?: number;
  roe_min?: number;
  revenue_growth_min?: number;
}

export interface SearchResult {
  companies: Company[];
  total_count: number;
  page: number;
  page_size: number;
}