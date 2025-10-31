/**
 * Financial Ratios Display Component
 */
import React from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Info,
  AlertTriangle,
  CheckCircle,
  XCircle
} from 'lucide-react';
import { FinancialRatios } from '@/types/financial';

interface RatiosDisplayProps {
  ratios: FinancialRatios;
  peerAverages?: Partial<FinancialRatios>;
  showComparison?: boolean;
  compact?: boolean;
}

interface RatioItem {
  key: keyof FinancialRatios;
  label: string;
  category: string;
  format: 'ratio' | 'percentage' | 'times' | 'score';
  description: string;
  goodRange?: { min?: number; max?: number };
  warningRange?: { min?: number; max?: number };
}

const ratioDefinitions: RatioItem[] = [
  // Liquidity Ratios
  {
    key: 'current_ratio',
    label: 'Current Ratio',
    category: 'Liquidity',
    format: 'ratio',
    description: 'Ability to pay short-term obligations',
    goodRange: { min: 1.5, max: 3.0 },
    warningRange: { min: 1.0, max: 4.0 },
  },
  {
    key: 'quick_ratio',
    label: 'Quick Ratio',
    category: 'Liquidity',
    format: 'ratio',
    description: 'Ability to pay short-term debts with liquid assets',
    goodRange: { min: 1.0, max: 2.0 },
    warningRange: { min: 0.5, max: 3.0 },
  },
  {
    key: 'cash_ratio',
    label: 'Cash Ratio',
    category: 'Liquidity',
    format: 'ratio',
    description: 'Most conservative liquidity measure',
    goodRange: { min: 0.2, max: 0.5 },
  },
  
  // Profitability Ratios
  {
    key: 'gross_profit_margin',
    label: 'Gross Margin',
    category: 'Profitability',
    format: 'percentage',
    description: 'Percentage of revenue after cost of goods sold',
    goodRange: { min: 0.3 },
  },
  {
    key: 'operating_profit_margin',
    label: 'Operating Margin',
    category: 'Profitability',
    format: 'percentage',
    description: 'Operating efficiency measure',
    goodRange: { min: 0.15 },
  },
  {
    key: 'net_profit_margin',
    label: 'Net Margin',
    category: 'Profitability',
    format: 'percentage',
    description: 'Bottom-line profitability',
    goodRange: { min: 0.1 },
  },
  {
    key: 'return_on_assets',
    label: 'ROA',
    category: 'Profitability',
    format: 'percentage',
    description: 'How efficiently assets generate profit',
    goodRange: { min: 0.05 },
  },
  {
    key: 'return_on_equity',
    label: 'ROE',
    category: 'Profitability',
    format: 'percentage',
    description: 'Return generated on shareholders equity',
    goodRange: { min: 0.15 },
  },
  
  // Leverage Ratios
  {
    key: 'debt_to_equity',
    label: 'Debt-to-Equity',
    category: 'Leverage',
    format: 'ratio',
    description: 'Financial leverage measure',
    goodRange: { max: 1.0 },
    warningRange: { max: 2.0 },
  },
  {
    key: 'debt_to_assets',
    label: 'Debt-to-Assets',
    category: 'Leverage',
    format: 'percentage',
    description: 'Percentage of assets financed by debt',
    goodRange: { max: 0.4 },
    warningRange: { max: 0.6 },
  },
  
  // Efficiency Ratios
  {
    key: 'asset_turnover',
    label: 'Asset Turnover',
    category: 'Efficiency',
    format: 'times',
    description: 'How efficiently assets generate revenue',
    goodRange: { min: 1.0 },
  },
  {
    key: 'inventory_turnover',
    label: 'Inventory Turnover',
    category: 'Efficiency',
    format: 'times',
    description: 'How quickly inventory is sold',
    goodRange: { min: 4.0 },
  },
  
  // Valuation Ratios
  {
    key: 'price_to_earnings',
    label: 'P/E Ratio',
    category: 'Valuation',
    format: 'ratio',
    description: 'Price relative to earnings',
    goodRange: { min: 10, max: 25 },
    warningRange: { min: 5, max: 40 },
  },
  {
    key: 'price_to_book',
    label: 'P/B Ratio',
    category: 'Valuation',
    format: 'ratio',
    description: 'Price relative to book value',
    goodRange: { min: 1.0, max: 3.0 },
  },
  {
    key: 'peg_ratio',
    label: 'PEG Ratio',
    category: 'Valuation',
    format: 'ratio',
    description: 'P/E ratio adjusted for growth',
    goodRange: { min: 0.5, max: 1.5 },
  },
];

export function RatiosDisplay({ 
  ratios, 
  peerAverages, 
  showComparison = false, 
  compact = false 
}: RatiosDisplayProps) {
  
  const formatValue = (value: number, format: string) => {
    if (value === null || value === undefined || isNaN(value)) {
      return 'N/A';
    }
    
    switch (format) {
      case 'percentage':
        return `${(value * 100).toFixed(2)}%`;
      case 'ratio':
        return value.toFixed(2);
      case 'times':
        return `${value.toFixed(2)}x`;
      case 'score':
        return value.toFixed(0);
      default:
        return value.toFixed(2);
    }
  };

  const getRatioStatus = (value: number, definition: RatioItem) => {
    if (value === null || value === undefined || isNaN(value)) {
      return 'unknown';
    }

    const { goodRange, warningRange } = definition;
    
    if (goodRange) {
      const withinGoodRange = 
        (goodRange.min === undefined || value >= goodRange.min) &&
        (goodRange.max === undefined || value <= goodRange.max);
      
      if (withinGoodRange) return 'good';
    }
    
    if (warningRange) {
      const withinWarningRange = 
        (warningRange.min === undefined || value >= warningRange.min) &&
        (warningRange.max === undefined || value <= warningRange.max);
      
      if (withinWarningRange) return 'warning';
    }
    
    return 'poor';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'good':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'poor':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Minus className="h-4 w-4 text-gray-400" />;
    }
  };

  const getComparisonIcon = (companyValue: number, peerValue: number) => {
    if (Math.abs(companyValue - peerValue) < 0.01) {
      return <Minus className="h-4 w-4 text-gray-400" />;
    }
    return companyValue > peerValue 
      ? <TrendingUp className="h-4 w-4 text-green-500" />
      : <TrendingDown className="h-4 w-4 text-red-500" />;
  };

  const groupedRatios = ratioDefinitions.reduce((acc, ratio) => {
    if (!acc[ratio.category]) {
      acc[ratio.category] = [];
    }
    acc[ratio.category].push(ratio);
    return acc;
  }, {} as Record<string, RatioItem[]>);

  if (compact) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {ratioDefinitions.slice(0, 8).map((definition) => {
          const value = ratios[definition.key] as number;
          const status = getRatioStatus(value, definition);
          
          return (
            <div key={definition.key} className="bg-white p-4 rounded-lg border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">
                  {definition.label}
                </span>
                {getStatusIcon(status)}
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {formatValue(value, definition.format)}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {Object.entries(groupedRatios).map(([category, categoryRatios]) => (
        <div key={category} className="bg-white rounded-lg shadow-sm border">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">{category} Ratios</h3>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {categoryRatios.map((definition) => {
                const value = ratios[definition.key] as number;
                const peerValue = peerAverages?.[definition.key] as number;
                const status = getRatioStatus(value, definition);
                
                return (
                  <div key={definition.key} className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-gray-900">
                          {definition.label}
                        </span>
                        <div className="group relative">
                          <Info className="h-4 w-4 text-gray-400 cursor-help" />
                          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                            {definition.description}
                          </div>
                        </div>
                      </div>
                      {getStatusIcon(status)}
                    </div>
                    
                    <div className="flex items-baseline justify-between">
                      <span className="text-2xl font-bold text-gray-900">
                        {formatValue(value, definition.format)}
                      </span>
                      
                      {showComparison && peerValue !== undefined && (
                        <div className="flex items-center space-x-1 text-sm text-gray-600">
                          {getComparisonIcon(value, peerValue)}
                          <span>vs {formatValue(peerValue, definition.format)}</span>
                        </div>
                      )}
                    </div>
                    
                    {showComparison && peerValue !== undefined && (
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            value > peerValue ? 'bg-green-500' : 'bg-red-500'
                          }`}
                          style={{
                            width: `${Math.min(100, Math.max(10, (value / (peerValue * 2)) * 100))}%`
                          }}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ))}
      
      {/* Quality Scores */}
      {(ratios.piotroski_score || ratios.altman_z_score) && (
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Quality Scores</h3>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {ratios.piotroski_score && (
                <div className="text-center">
                  <div className="text-3xl font-bold text-indigo-600 mb-2">
                    {ratios.piotroski_score}/9
                  </div>
                  <div className="text-sm font-medium text-gray-900 mb-1">
                    Piotroski F-Score
                  </div>
                  <div className="text-xs text-gray-600">
                    Financial Strength
                  </div>
                </div>
              )}
              
              {ratios.altman_z_score && (
                <div className="text-center">
                  <div className={`text-3xl font-bold mb-2 ${
                    ratios.altman_z_score > 2.99 ? 'text-green-600' :
                    ratios.altman_z_score > 1.8 ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {ratios.altman_z_score.toFixed(2)}
                  </div>
                  <div className="text-sm font-medium text-gray-900 mb-1">
                    Altman Z-Score
                  </div>
                  <div className="text-xs text-gray-600">
                    Bankruptcy Risk
                  </div>
                </div>
              )}
              
              {ratios.beneish_m_score && (
                <div className="text-center">
                  <div className={`text-3xl font-bold mb-2 ${
                    ratios.beneish_m_score < -2.22 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {ratios.beneish_m_score.toFixed(2)}
                  </div>
                  <div className="text-sm font-medium text-gray-900 mb-1">
                    Beneish M-Score
                  </div>
                  <div className="text-xs text-gray-600">
                    Earnings Manipulation
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RatiosDisplay;