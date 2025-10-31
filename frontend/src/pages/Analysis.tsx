/**
 * Financial Analysis Page
 */
import React, { useState, useEffect } from 'react';
import { 
  Search, 
  TrendingUp, 
  BarChart3, 
  Calculator,
  Download,
  RefreshCw,
  AlertCircle,
  Building2,
  DollarSign
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { apiService } from '@/services/api';
import { FinancialChart } from '@/components/charts/FinancialChart';
import { RatiosDisplay } from '@/components/financial/RatiosDisplay';
import { 
  Company, 
  CompanyAnalysis, 
  FinancialRatios, 
  TimeSeriesData,
  ComparisonChartData,
  ValuationModel 
} from '@/types/financial';
import toast from 'react-hot-toast';

export function Analysis() {
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [analysis, setAnalysis] = useState<CompanyAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'ratios' | 'valuation' | 'charts'>('overview');

  // Mock data for demonstration
  const mockCompanies: Company[] = [
    {
      id: '1',
      symbol: 'AAPL',
      name: 'Apple Inc.',
      sector: 'Technology',
      industry: 'Consumer Electronics',
      market_cap: 3000000000000,
      employees: 164000,
      founded: '1976',
      headquarters: 'Cupertino, CA',
      website: 'https://www.apple.com',
      description: 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.'
    },
    {
      id: '2',
      symbol: 'MSFT',
      name: 'Microsoft Corporation',
      sector: 'Technology',
      industry: 'Software',
      market_cap: 2800000000000,
      employees: 221000,
      founded: '1975',
      headquarters: 'Redmond, WA',
      website: 'https://www.microsoft.com',
      description: 'Microsoft Corporation develops, licenses, and supports software, services, devices, and solutions worldwide.'
    },
    {
      id: '3',
      symbol: 'GOOGL',
      name: 'Alphabet Inc.',
      sector: 'Technology',
      industry: 'Internet Services',
      market_cap: 1700000000000,
      employees: 190000,
      founded: '1998',
      headquarters: 'Mountain View, CA',
      website: 'https://www.alphabet.com',
      description: 'Alphabet Inc. provides various products and platforms in the United States, Europe, the Middle East, Africa, the Asia-Pacific, Canada, and Latin America.'
    }
  ];

  const mockRatios: FinancialRatios = {
    // Liquidity Ratios
    current_ratio: 1.73,
    quick_ratio: 1.38,
    cash_ratio: 0.34,
    operating_cash_flow_ratio: 0.28,
    
    // Profitability Ratios
    gross_profit_margin: 0.43,
    operating_profit_margin: 0.30,
    net_profit_margin: 0.25,
    return_on_assets: 0.20,
    return_on_equity: 0.87,
    return_on_invested_capital: 0.31,
    
    // Leverage Ratios
    debt_to_equity: 1.73,
    debt_to_assets: 0.32,
    equity_multiplier: 4.26,
    interest_coverage_ratio: 28.6,
    
    // Efficiency Ratios
    asset_turnover: 0.82,
    inventory_turnover: 10.4,
    receivables_turnover: 15.8,
    working_capital_turnover: 12.1,
    
    // Valuation Ratios
    price_to_earnings: 28.7,
    price_to_book: 39.4,
    price_to_sales: 7.8,
    enterprise_value_to_ebitda: 22.1,
    peg_ratio: 2.1,
    
    // Growth Ratios
    revenue_growth: 0.08,
    earnings_growth: 0.11,
    book_value_growth: 0.15,
    
    // Quality Scores
    piotroski_score: 8,
    altman_z_score: 3.2,
    beneish_m_score: -2.8,
  };

  const mockTimeSeriesData: TimeSeriesData[] = [
    { date: '2023-01', value: 150.2 },
    { date: '2023-02', value: 155.8 },
    { date: '2023-03', value: 148.9 },
    { date: '2023-04', value: 162.1 },
    { date: '2023-05', value: 171.3 },
    { date: '2023-06', value: 168.7 },
    { date: '2023-07', value: 175.4 },
    { date: '2023-08', value: 182.9 },
    { date: '2023-09', value: 178.2 },
    { date: '2023-10', value: 185.6 },
    { date: '2023-11', value: 191.3 },
    { date: '2023-12', value: 197.8 },
  ];

  const mockComparisonData: ComparisonChartData[] = [
    { category: 'P/E Ratio', company_value: 28.7, peer_average: 24.3, industry_average: 22.1 },
    { category: 'ROE', company_value: 0.87, peer_average: 0.21, industry_average: 0.18 },
    { category: 'Debt/Equity', company_value: 1.73, peer_average: 0.85, industry_average: 1.12 },
    { category: 'Current Ratio', company_value: 1.73, peer_average: 1.45, industry_average: 1.38 },
    { category: 'Gross Margin', company_value: 0.43, peer_average: 0.38, industry_average: 0.35 },
  ];

  const mockValuationModels: ValuationModel[] = [
    {
      model_type: 'dcf',
      fair_value: 185.50,
      current_price: 197.80,
      upside_downside: -6.2,
      confidence_level: 'high',
      assumptions: {
        terminal_growth_rate: 0.03,
        discount_rate: 0.10,
        projection_years: 5
      }
    },
    {
      model_type: 'graham_number',
      fair_value: 172.30,
      current_price: 197.80,
      upside_downside: -12.9,
      confidence_level: 'medium',
      assumptions: {
        eps: 6.89,
        book_value_per_share: 4.40
      }
    },
    {
      model_type: 'peg',
      fair_value: 205.40,
      current_price: 197.80,
      upside_downside: 3.8,
      confidence_level: 'medium',
      assumptions: {
        pe_ratio: 28.7,
        growth_rate: 0.11
      }
    }
  ];

  const filteredCompanies = mockCompanies.filter(company =>
    company.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
    company.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCompanySelect = async (company: Company) => {
    setSelectedCompany(company);
    setIsLoading(true);
    
    try {
      // In a real app, this would fetch actual data from the API
      // const ratiosResponse = await apiService.calculateFinancialRatios({
      //   company_id: company.id,
      //   period_type: 'annual',
      //   fiscal_year: 2023
      // });
      
      // For now, use mock data
      setTimeout(() => {
        setAnalysis({
          company,
          financial_statement: {} as any, // Would be populated with real data
          ratios: mockRatios,
          valuation_models: mockValuationModels,
        });
        setIsLoading(false);
        toast.success(`Analysis loaded for ${company.name}`);
      }, 1000);
      
    } catch (error) {
      console.error('Failed to load analysis:', error);
      toast.error('Failed to load company analysis');
      setIsLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatMarketCap = (value: number) => {
    if (value >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
    return formatCurrency(value);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Financial Analysis</h1>
          <p className="mt-1 text-sm text-gray-600">
            Analyze companies with comprehensive financial metrics and valuation models
          </p>
        </div>
        
        <div className="mt-4 sm:mt-0 flex space-x-3">
          <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
            <Download className="h-4 w-4 mr-2" />
            Export
          </button>
          <button className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700">
            <Calculator className="h-4 w-4 mr-2" />
            New Analysis
          </button>
        </div>
      </div>

      {/* Company Search */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center space-x-4">
          <div className="flex-1 relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Search companies by symbol or name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Search Results */}
        {searchQuery && (
          <div className="mt-4 border-t pt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredCompanies.map((company) => (
                <div
                  key={company.id}
                  className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => handleCompanySelect(company)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-gray-900">{company.symbol}</span>
                    <span className="text-sm text-gray-500">{company.sector}</span>
                  </div>
                  <div className="text-sm text-gray-700 mb-2">{company.name}</div>
                  <div className="text-xs text-gray-500">
                    Market Cap: {formatMarketCap(company.market_cap)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Analysis Results */}
      {selectedCompany && (
        <div className="space-y-6">
          {/* Company Header */}
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-4">
                <div className="h-16 w-16 bg-indigo-100 rounded-lg flex items-center justify-center">
                  <Building2 className="h-8 w-8 text-indigo-600" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-gray-900">
                    {selectedCompany.name} ({selectedCompany.symbol})
                  </h2>
                  <p className="text-gray-600">{selectedCompany.sector} • {selectedCompany.industry}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Market Cap: {formatMarketCap(selectedCompany.market_cap)}
                  </p>
                </div>
              </div>
              
              {isLoading && (
                <RefreshCw className="h-5 w-5 text-gray-400 animate-spin" />
              )}
            </div>
            
            {selectedCompany.description && (
              <p className="mt-4 text-gray-700">{selectedCompany.description}</p>
            )}
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="bg-white rounded-lg shadow-sm border p-12 text-center">
              <RefreshCw className="h-8 w-8 text-indigo-600 animate-spin mx-auto mb-4" />
              <p className="text-gray-600">Loading financial analysis...</p>
            </div>
          )}

          {/* Analysis Content */}
          {analysis && !isLoading && (
            <>
              {/* Tabs */}
              <div className="bg-white rounded-lg shadow-sm border">
                <div className="border-b border-gray-200">
                  <nav className="-mb-px flex space-x-8 px-6">
                    {[
                      { id: 'overview', name: 'Overview', icon: BarChart3 },
                      { id: 'ratios', name: 'Financial Ratios', icon: Calculator },
                      { id: 'valuation', name: 'Valuation', icon: DollarSign },
                      { id: 'charts', name: 'Charts', icon: TrendingUp },
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
                  {/* Overview Tab */}
                  {activeTab === 'overview' && (
                    <div className="space-y-6">
                      {/* Key Metrics */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <div className="text-sm font-medium text-gray-600">P/E Ratio</div>
                          <div className="text-2xl font-bold text-gray-900">
                            {analysis.ratios.price_to_earnings.toFixed(1)}
                          </div>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <div className="text-sm font-medium text-gray-600">ROE</div>
                          <div className="text-2xl font-bold text-gray-900">
                            {(analysis.ratios.return_on_equity * 100).toFixed(1)}%
                          </div>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <div className="text-sm font-medium text-gray-600">Debt/Equity</div>
                          <div className="text-2xl font-bold text-gray-900">
                            {analysis.ratios.debt_to_equity.toFixed(2)}
                          </div>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <div className="text-sm font-medium text-gray-600">Current Ratio</div>
                          <div className="text-2xl font-bold text-gray-900">
                            {analysis.ratios.current_ratio.toFixed(2)}
                          </div>
                        </div>
                      </div>

                      {/* Compact Ratios Display */}
                      <RatiosDisplay ratios={analysis.ratios} compact />
                    </div>
                  )}

                  {/* Ratios Tab */}
                  {activeTab === 'ratios' && (
                    <RatiosDisplay 
                      ratios={analysis.ratios} 
                      showComparison={false}
                    />
                  )}

                  {/* Valuation Tab */}
                  {activeTab === 'valuation' && (
                    <div className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {analysis.valuation_models.map((model, index) => (
                          <div key={index} className="bg-gray-50 p-6 rounded-lg">
                            <div className="text-sm font-medium text-gray-600 mb-2">
                              {model.model_type.toUpperCase()} Model
                            </div>
                            <div className="text-2xl font-bold text-gray-900 mb-2">
                              {formatCurrency(model.fair_value)}
                            </div>
                            <div className={`text-sm font-medium ${
                              model.upside_downside >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {model.upside_downside >= 0 ? '+' : ''}{model.upside_downside.toFixed(1)}%
                            </div>
                            <div className="text-xs text-gray-500 mt-2">
                              vs Current: {formatCurrency(model.current_price)}
                            </div>
                            <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mt-2 ${
                              model.confidence_level === 'high' ? 'bg-green-100 text-green-800' :
                              model.confidence_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {model.confidence_level} confidence
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Charts Tab */}
                  {activeTab === 'charts' && (
                    <div className="space-y-6">
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <FinancialChart
                          type="line"
                          title="Stock Price Trend"
                          data={mockTimeSeriesData}
                          currency
                        />
                        <FinancialChart
                          type="bar"
                          title="Peer Comparison"
                          data={mockComparisonData}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Empty State */}
      {!selectedCompany && (
        <div className="bg-white rounded-lg shadow-sm border p-12 text-center">
          <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Start Your Financial Analysis
          </h3>
          <p className="text-gray-600 mb-6">
            Search for a company above to begin comprehensive financial analysis with ratios, valuation models, and peer comparisons.
          </p>
          <div className="flex justify-center space-x-4">
            <button
              onClick={() => setSearchQuery('AAPL')}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              Try Apple (AAPL)
            </button>
            <button
              onClick={() => setSearchQuery('MSFT')}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              Try Microsoft (MSFT)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}