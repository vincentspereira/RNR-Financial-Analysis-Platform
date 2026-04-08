/**
 * Stock Screener Page Component
 */
import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  X,
  RefreshCw,
} from 'lucide-react';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';

interface ScreenerResult {
  symbol: string;
  company_name: string;
  sector: string;
  exchange: string;
  market_cap: number;
  price: number;
  pe_ratio: number | null;
  dividend_yield: number | null;
  price_change_1d: number | null;
  price_change_1y: number | null;
  volume: number | null;
  score: number;
}

interface ScreenerFilter {
  market_cap_min?: number;
  market_cap_max?: number;
  sector?: string[];
  pe_ratio_min?: number;
  pe_ratio_max?: number;
  dividend_yield_min?: number;
  revenue_growth_min?: number;
  price_change_1y_min?: number;
  rsi_14_min?: number;
  rsi_14_max?: number;
  sort_by?: string;
  sort_order?: string;
  limit?: number;
}

const PRESET_SCREENERS: Record<string, { label: string; description: string; filters: ScreenerFilter }> = {
  value: {
    label: 'Value Stocks',
    description: 'Low P/E, high dividend yield',
    filters: { pe_ratio_max: 15, dividend_yield_min: 2, sort_by: 'pe_ratio', sort_order: 'asc' },
  },
  growth: {
    label: 'Growth Stocks',
    description: 'High revenue growth',
    filters: { revenue_growth_min: 20, sort_by: 'market_cap', sort_order: 'desc' },
  },
  dividend: {
    label: 'High Dividend',
    description: 'Dividend yield > 3%',
    filters: { dividend_yield_min: 3, sort_by: 'dividend_yield', sort_order: 'desc' },
  },
  momentum: {
    label: 'Momentum',
    description: 'Strong 1Y performance',
    filters: { price_change_1y_min: 20, sort_by: 'price_change_1y', sort_order: 'desc' },
  },
  undervalued: {
    label: 'Undervalued',
    description: 'Low P/E + high quality',
    filters: { pe_ratio_max: 12, sort_by: 'score', sort_order: 'desc' },
  },
  large_cap: {
    label: 'Large Cap',
    description: 'Market cap > $10B',
    filters: { market_cap_min: 10000000000, sort_by: 'market_cap', sort_order: 'desc' },
  },
};

const SECTORS = [
  'Technology', 'Healthcare', 'Financials', 'Consumer Discretionary',
  'Consumer Staples', 'Energy', 'Industrials', 'Materials',
  'Real Estate', 'Utilities', 'Communication Services',
];

function formatMarketCap(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  return `$${value.toLocaleString()}`;
}

export function StockScreener() {
  const [results, setResults] = useState<ScreenerResult[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(true);
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [sortField, setSortField] = useState<string>('market_cap');
  const [sortOrder, setSortOrder] = useState<string>('desc');

  // Filter state
  const [filters, setFilters] = useState<ScreenerFilter>({
    sort_by: 'market_cap',
    sort_order: 'desc',
    limit: 50,
  });
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);

  const runScreener = async (customFilters?: ScreenerFilter) => {
    try {
      setIsLoading(true);
      const filterData = customFilters || {
        ...filters,
        sector: selectedSectors.length > 0 ? selectedSectors : undefined,
        sort_by: sortField,
        sort_order: sortOrder,
      };

      const response = await apiService.request({
        method: 'POST',
        url: '/api/v1/screener/run',
        data: filterData,
      });

      if (response.data) {
        setResults(response.data.results || []);
        setTotalResults(response.data.total_results || 0);
      }
    } catch (error) {
      console.error('Screener failed:', error);
      toast.error('Failed to run screener');
    } finally {
      setIsLoading(false);
    }
  };

  const runPreset = async (presetKey: string) => {
    const preset = PRESET_SCREENERS[presetKey];
    if (!preset) return;
    setActivePreset(presetKey);
    setSelectedSectors([]);
    setFilters(preset.filters);
    await runScreener(preset.filters);
  };

  const updateFilter = (key: string, value: number | undefined) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setActivePreset(null);
  };

  const toggleSector = (sector: string) => {
    setSelectedSectors(prev =>
      prev.includes(sector)
        ? prev.filter(s => s !== sector)
        : [...prev, sector]
    );
    setActivePreset(null);
  };

  const handleSort = (field: string) => {
    const newOrder = sortField === field && sortOrder === 'desc' ? 'asc' : 'desc';
    setSortField(field);
    setSortOrder(newOrder);
  };

  const clearFilters = () => {
    setFilters({ sort_by: 'market_cap', sort_order: 'desc', limit: 50 });
    setSelectedSectors([]);
    setActivePreset(null);
  };

  const SortHeader = ({ field, label }: { field: string; label: string }) => (
    <th
      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-700"
      onClick={() => handleSort(field)}
    >
      <span className="flex items-center space-x-1">
        <span>{label}</span>
        {sortField === field && (
          sortOrder === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
        )}
      </span>
    </th>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Stock Screener</h1>
          <p className="mt-1 text-sm text-gray-600">
            Find stocks matching your investment criteria
          </p>
        </div>
        <div className="mt-4 sm:mt-0 flex items-center space-x-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 bg-white hover:bg-gray-50"
          >
            <SlidersHorizontal className="h-4 w-4 mr-1" />
            {showFilters ? 'Hide' : 'Show'} Filters
          </button>
          <button
            onClick={() => runScreener()}
            disabled={isLoading}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
          >
            {isLoading ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Search className="h-4 w-4 mr-2" />
            )}
            Run Screener
          </button>
        </div>
      </div>

      {/* Preset Screeners */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(PRESET_SCREENERS).map(([key, preset]) => (
          <button
            key={key}
            onClick={() => runPreset(key)}
            className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
              activePreset === key
                ? 'bg-indigo-100 border-indigo-300 text-indigo-800'
                : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-900">Custom Filters</h3>
            <button onClick={clearFilters} className="text-xs text-gray-500 hover:text-gray-700 flex items-center">
              <X className="h-3 w-3 mr-1" /> Clear all
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Market Cap Min</label>
              <input
                type="number"
                value={filters.market_cap_min || ''}
                onChange={(e) => updateFilter('market_cap_min', e.target.value ? Number(e.target.value) : undefined)}
                placeholder="e.g., 1000000000"
                className="w-full rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Market Cap Max</label>
              <input
                type="number"
                value={filters.market_cap_max || ''}
                onChange={(e) => updateFilter('market_cap_max', e.target.value ? Number(e.target.value) : undefined)}
                placeholder="e.g., 100000000000"
                className="w-full rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">P/E Ratio Min</label>
              <input
                type="number"
                value={filters.pe_ratio_min || ''}
                onChange={(e) => updateFilter('pe_ratio_min', e.target.value ? Number(e.target.value) : undefined)}
                placeholder="0"
                className="w-full rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">P/E Ratio Max</label>
              <input
                type="number"
                value={filters.pe_ratio_max || ''}
                onChange={(e) => updateFilter('pe_ratio_max', e.target.value ? Number(e.target.value) : undefined)}
                placeholder="50"
                className="w-full rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Dividend Yield Min %</label>
              <input
                type="number"
                step="0.1"
                value={filters.dividend_yield_min || ''}
                onChange={(e) => updateFilter('dividend_yield_min', e.target.value ? Number(e.target.value) : undefined)}
                placeholder="0"
                className="w-full rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Revenue Growth Min %</label>
              <input
                type="number"
                step="0.1"
                value={filters.revenue_growth_min || ''}
                onChange={(e) => updateFilter('revenue_growth_min', e.target.value ? Number(e.target.value) : undefined)}
                placeholder="0"
                className="w-full rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">RSI Min</label>
              <input
                type="number"
                value={filters.rsi_14_min || ''}
                onChange={(e) => updateFilter('rsi_14_min', e.target.value ? Number(e.target.value) : undefined)}
                placeholder="0"
                className="w-full rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">1Y Price Change Min %</label>
              <input
                type="number"
                step="0.1"
                value={filters.price_change_1y_min || ''}
                onChange={(e) => updateFilter('price_change_1y_min', e.target.value ? Number(e.target.value) : undefined)}
                placeholder="0"
                className="w-full rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Sector Filter */}
          <div className="mt-4">
            <label className="block text-xs font-medium text-gray-500 mb-2">Sectors</label>
            <div className="flex flex-wrap gap-2">
              {SECTORS.map((sector) => (
                <button
                  key={sector}
                  onClick={() => toggleSector(sector)}
                  className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                    selectedSectors.includes(sector)
                      ? 'bg-indigo-100 text-indigo-800 border border-indigo-300'
                      : 'bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200'
                  }`}
                >
                  {sector}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">
            Results
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({totalResults} stocks found)
            </span>
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <SortHeader field="symbol" label="Symbol" />
                <SortHeader field="company_name" label="Company" />
                <SortHeader field="sector" label="Sector" />
                <SortHeader field="market_cap" label="Market Cap" />
                <SortHeader field="price" label="Price" />
                <SortHeader field="pe_ratio" label="P/E" />
                <SortHeader field="dividend_yield" label="Div Yield" />
                <SortHeader field="price_change_1d" label="1D %" />
                <SortHeader field="price_change_1y" label="1Y %" />
                <SortHeader field="score" label="Score" />
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {results.length > 0 ? (
                results.map((stock) => (
                  <tr key={stock.symbol} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-indigo-600">{stock.symbol}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate">{stock.company_name}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{stock.sector}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{formatMarketCap(stock.market_cap)}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">${stock.price.toFixed(2)}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {stock.pe_ratio != null ? stock.pe_ratio.toFixed(1) : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {stock.dividend_yield != null ? `${stock.dividend_yield.toFixed(2)}%` : '-'}
                    </td>
                    <td className={`px-4 py-3 text-sm font-medium ${
                      stock.price_change_1d != null
                        ? stock.price_change_1d >= 0 ? 'text-green-600' : 'text-red-600'
                        : 'text-gray-400'
                    }`}>
                      {stock.price_change_1d != null ? `${stock.price_change_1d >= 0 ? '+' : ''}${stock.price_change_1d.toFixed(2)}%` : '-'}
                    </td>
                    <td className={`px-4 py-3 text-sm font-medium ${
                      stock.price_change_1y != null
                        ? stock.price_change_1y >= 0 ? 'text-green-600' : 'text-red-600'
                        : 'text-gray-400'
                    }`}>
                      {stock.price_change_1y != null ? `${stock.price_change_1y >= 0 ? '+' : ''}${stock.price_change_1y.toFixed(2)}%` : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        stock.score >= 80 ? 'bg-green-100 text-green-800' :
                        stock.score >= 60 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {stock.score.toFixed(0)}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={10} className="px-4 py-12 text-center text-sm text-gray-500">
                    <Filter className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                    No results. Adjust your filters or try a preset screener.
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
