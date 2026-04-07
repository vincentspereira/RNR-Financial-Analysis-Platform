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
import { apiService } from '@/services/api';
import { Portfolio, PortfolioPosition } from '@/types/financial';
import { PortfolioOverview } from '@/components/portfolio/PortfolioOverview';
import { PositionsTable } from '@/components/portfolio/PositionsTable';
import { PortfolioAnalytics } from '@/components/portfolio/PortfolioAnalytics';
import toast from 'react-hot-toast';

export function PortfolioPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'overview' | 'positions' | 'analytics'>('overview');
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadPortfolio();
  }, []);

  const loadPortfolio = async () => {
    try {
      setIsLoading(true);
      const response = await apiService.request({
        method: 'GET',
        url: '/api/v1/portfolio/',
      });
      if (response.data) {
        const portfolios = response.data.portfolios || response.data;
        if (Array.isArray(portfolios) && portfolios.length > 0) {
          setPortfolio(portfolios[0]);
        }
      }
    } catch (error) {
      console.error('Failed to load portfolio:', error);
      toast.error('Failed to load portfolio data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditPosition = (position: PortfolioPosition) => {
    toast.info(`Edit position: ${position.company.symbol}`);
  };

  const handleDeletePosition = (positionId: string) => {
    if (confirm('Are you sure you want to remove this position?')) {
      toast.success('Position removed successfully');
    }
  };

  const handleAnalyzeCompany = (companyId: string) => {
    toast.info(`Analyzing company...`);
  };

  const handleAddPosition = () => {
    toast.info('Add new position');
  };

  const handleExportPortfolio = () => {
    toast.success('Portfolio exported successfully');
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
          {activeTab === 'overview' && (
            <PortfolioOverview portfolio={portfolio} showDetailed={true} />
          )}
          {activeTab === 'positions' && (
            <PositionsTable
              positions={portfolio.positions}
              onEditPosition={handleEditPosition}
              onDeletePosition={handleDeletePosition}
              onAnalyzeCompany={handleAnalyzeCompany}
            />
          )}
          {activeTab === 'analytics' && (
            <PortfolioAnalytics portfolio={portfolio} />
          )}
        </div>
      </div>

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
