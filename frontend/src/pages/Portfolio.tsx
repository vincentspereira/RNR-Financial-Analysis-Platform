/**
 * Portfolio Management Page
 */
import React, { useState, useEffect } from 'react';
import {
  Plus,
  Download,
  Settings,
  RefreshCw,
  BarChart3,
  TrendingUp,
  PieChart,
  Target,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Portfolio, PortfolioPosition, Company } from '@/types/financial';
import { PortfolioOverview } from '@/components/portfolio/PortfolioOverview';
import { PositionsTable } from '@/components/portfolio/PositionsTable';
import { PortfolioAnalytics } from '@/components/portfolio/PortfolioAnalytics';
import toast from 'react-hot-toast';

export function PortfolioPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'overview' | 'positions' | 'analytics'>('overview');
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Mock portfolio data for demonstration
  const mockCompanies: Company[] = [
    {
      id: '1',
      symbol: 'AAPL',
      name: 'Apple Inc.',
      sector: 'Technology',
      industry: 'Consumer Electronics',
      market_cap: 3000000000000,
    },
    {
      id: '2',
      symbol: 'MSFT',
      name: 'Microsoft Corporation',
      sector: 'Technology',
      industry: 'Software',
      market_cap: 2800000000000,
    },
    {
      id: '3',
      symbol: 'GOOGL',
      name: 'Alphabet Inc.',
      sector: 'Technology',
      industry: 'Internet Services',
      market_cap: 1700000000000,
    },
    {
      id: '4',
      symbol: 'AMZN',
      name: 'Amazon.com Inc.',
      sector: 'Consumer Discretionary',
      industry: 'E-commerce',
      market_cap: 1500000000000,
    },
    {
      id: '5',
      symbol: 'TSLA',
      name: 'Tesla Inc.',
      sector: 'Consumer Discretionary',
      industry: 'Electric Vehicles',
      market_cap: 800000000000,
    },
    {
      id: '6',
      symbol: 'JPM',
      name: 'JPMorgan Chase & Co.',
      sector: 'Financial Services',
      industry: 'Banking',
      market_cap: 450000000000,
    },
    {
      id: '7',
      symbol: 'JNJ',
      name: 'Johnson & Johnson',
      sector: 'Healthcare',
      industry: 'Pharmaceuticals',
      market_cap: 420000000000,
    },
  ];

  const mockPositions: PortfolioPosition[] = [
    {
      id: '1',
      company: mockCompanies[0], // AAPL
      shares: 100,
      average_cost: 150.00,
      current_price: 197.80,
      market_value: 19780,
      unrealized_gain_loss: 4780,
      unrealized_gain_loss_percentage: 31.87,
      weight: 22.5,
      purchase_date: '2023-01-15',
    },
    {
      id: '2',
      company: mockCompanies[1], // MSFT
      shares: 50,
      average_cost: 280.00,
      current_price: 378.85,
      market_value: 18942.50,
      unrealized_gain_loss: 4942.50,
      unrealized_gain_loss_percentage: 35.30,
      weight: 21.6,
      purchase_date: '2023-02-10',
    },
    {
      id: '3',
      company: mockCompanies[2], // GOOGL
      shares: 75,
      average_cost: 120.00,
      current_price: 140.93,
      market_value: 10569.75,
      unrealized_gain_loss: 1569.75,
      unrealized_gain_loss_percentage: 17.44,
      weight: 12.0,
      purchase_date: '2023-03-05',
    },
    {
      id: '4',
      company: mockCompanies[3], // AMZN
      shares: 80,
      average_cost: 145.00,
      current_price: 151.94,
      market_value: 12155.20,
      unrealized_gain_loss: 555.20,
      unrealized_gain_loss_percentage: 4.78,
      weight: 13.8,
      purchase_date: '2023-04-12',
    },
    {
      id: '5',
      company: mockCompanies[4], // TSLA
      shares: 30,
      average_cost: 220.00,
      current_price: 248.50,
      market_value: 7455.00,
      unrealized_gain_loss: 855.00,
      unrealized_gain_loss_percentage: 12.95,
      weight: 8.5,
      purchase_date: '2023-05-20',
    },
    {
      id: '6',
      company: mockCompanies[5], // JPM
      shares: 40,
      average_cost: 155.00,
      current_price: 168.85,
      market_value: 6754.00,
      unrealized_gain_loss: 554.00,
      unrealized_gain_loss_percentage: 8.93,
      weight: 7.7,
      purchase_date: '2023-06-08',
    },
    {
      id: '7',
      company: mockCompanies[6], // JNJ
      shares: 60,
      average_cost: 165.00,
      current_price: 159.23,
      market_value: 9553.80,
      unrealized_gain_loss: -346.20,
      unrealized_gain_loss_percentage: -3.50,
      weight: 10.9,
      purchase_date: '2023-07-15',
    },
  ];

  const mockPortfolio: Portfolio = {
    id: '1',
    name: 'Growth Portfolio',
    description: 'Diversified growth-focused investment portfolio',
    total_value: 87210.25,
    total_return: 12910.25,
    total_return_percentage: 17.38,
    positions: mockPositions,
    created_at: '2023-01-01T00:00:00Z',
    updated_at: new Date().toISOString(),
  };

  useEffect(() => {
    loadPortfolio();
  }, []);

  const loadPortfolio = async () => {
    try {
      setIsLoading(true);
      
      // In a real app, this would fetch from the API
      // const response = await apiService.getPortfolio(user?.id);
      
      // For now, use mock data
      setTimeout(() => {
        setPortfolio(mockPortfolio);
        setIsLoading(false);
      }, 1000);
      
    } catch (error) {
      console.error('Failed to load portfolio:', error);
      toast.error('Failed to load portfolio data');
      setIsLoading(false);
    }
  };

  const handleEditPosition = (position: PortfolioPosition) => {
    toast.info(`Edit position: ${position.company.symbol}`);
    // TODO: Implement edit position modal
  };

  const handleDeletePosition = (positionId: string) => {
    if (confirm('Are you sure you want to remove this position?')) {
      toast.success('Position removed successfully');
      // TODO: Implement position removal
    }
  };

  const handleAnalyzeCompany = (companyId: string) => {
    const company = mockCompanies.find(c => c.id === companyId);
    if (company) {
      toast.info(`Analyzing ${company.symbol}...`);
      // TODO: Navigate to analysis page with company pre-selected
    }
  };

  const handleAddPosition = () => {
    toast.info('Add new position');
    // TODO: Implement add position modal
  };

  const handleExportPortfolio = () => {
    toast.success('Portfolio exported successfully');
    // TODO: Implement portfolio export
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="text-center py-12">
        <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Portfolio Found</h3>
        <p className="text-gray-600 mb-6">Create your first portfolio to start tracking your investments.</p>
        <button
          onClick={handleAddPosition}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4 mr-2" />
          Create Portfolio
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Portfolio Management</h1>
          <p className="mt-1 text-sm text-gray-600">
            Track and analyze your investment portfolio performance
          </p>
        </div>
        
        <div className="mt-4 sm:mt-0 flex space-x-3">
          <button
            onClick={handleExportPortfolio}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </button>
          <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </button>
          <button
            onClick={handleAddPosition}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Position
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {[
              { id: 'overview', name: 'Overview', icon: BarChart3 },
              { id: 'positions', name: 'Positions', icon: Target },
              { id: 'analytics', name: 'Analytics', icon: TrendingUp },
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
            <PortfolioOverview portfolio={portfolio} showDetailed={true} />
          )}

          {/* Positions Tab */}
          {activeTab === 'positions' && (
            <PositionsTable
              positions={portfolio.positions}
              onEditPosition={handleEditPosition}
              onDeletePosition={handleDeletePosition}
              onAnalyzeCompany={handleAnalyzeCompany}
            />
          )}

          {/* Analytics Tab */}
          {activeTab === 'analytics' && (
            <PortfolioAnalytics portfolio={portfolio} />
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={handleAddPosition}
            className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-indigo-500 hover:bg-indigo-50 transition-colors"
          >
            <Plus className="h-8 w-8 text-gray-400 mx-auto mb-2" />
            <div className="text-sm font-medium text-gray-900">Add Position</div>
            <div className="text-xs text-gray-500">Buy a new stock or ETF</div>
          </button>
          
          <button className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-indigo-500 hover:bg-indigo-50 transition-colors">
            <PieChart className="h-8 w-8 text-gray-400 mx-auto mb-2" />
            <div className="text-sm font-medium text-gray-900">Rebalance</div>
            <div className="text-xs text-gray-500">Optimize allocation</div>
          </button>
          
          <button className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-indigo-500 hover:bg-indigo-50 transition-colors">
            <TrendingUp className="h-8 w-8 text-gray-400 mx-auto mb-2" />
            <div className="text-sm font-medium text-gray-900">Performance Report</div>
            <div className="text-xs text-gray-500">Generate detailed report</div>
          </button>
        </div>
      </div>
    </div>
  );
}