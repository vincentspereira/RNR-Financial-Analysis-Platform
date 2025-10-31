/**
 * Dashboard Page Component
 */
import React, { useEffect, useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  Users,
  Activity,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { apiService } from '@/services/api';

interface DashboardStats {
  totalPortfolioValue: number;
  totalReturn: number;
  totalReturnPercentage: number;
  activePositions: number;
  watchlistCount: number;
  alertsCount: number;
}

interface HealthStatus {
  status: string;
  features: string[];
}

export function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats>({
    totalPortfolioValue: 125000,
    totalReturn: 8750,
    totalReturnPercentage: 7.5,
    activePositions: 12,
    watchlistCount: 25,
    alertsCount: 3,
  });
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      
      // Load health status
      const health = await apiService.healthCheck();
      setHealthStatus(health);
      
      // In a real app, you would load actual portfolio data here
      // For now, we'll use mock data
      
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const statCards = [
    {
      name: 'Portfolio Value',
      value: `$${stats.totalPortfolioValue.toLocaleString()}`,
      change: `+$${stats.totalReturn.toLocaleString()}`,
      changeType: stats.totalReturn >= 0 ? 'increase' : 'decrease',
      icon: DollarSign,
    },
    {
      name: 'Total Return',
      value: `${stats.totalReturnPercentage >= 0 ? '+' : ''}${stats.totalReturnPercentage}%`,
      change: 'vs last month',
      changeType: stats.totalReturnPercentage >= 0 ? 'increase' : 'decrease',
      icon: TrendingUp,
    },
    {
      name: 'Active Positions',
      value: stats.activePositions.toString(),
      change: '+2 this week',
      changeType: 'increase',
      icon: BarChart3,
    },
    {
      name: 'Watchlist',
      value: stats.watchlistCount.toString(),
      change: '+5 companies',
      changeType: 'increase',
      icon: Activity,
    },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="md:flex md:items-center md:justify-between">
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate">
            Welcome back, {user?.name}!
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Here's what's happening with your financial portfolio today.
          </p>
        </div>
        <div className="mt-4 flex md:mt-0 md:ml-4">
          <button
            type="button"
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Export Report
          </button>
          <button
            type="button"
            className="ml-3 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Add Position
          </button>
        </div>
      </div>

      {/* System Status */}
      {healthStatus && (
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                {healthStatus.status === 'healthy' ? (
                  <CheckCircle className="h-8 w-8 text-green-400" />
                ) : (
                  <AlertCircle className="h-8 w-8 text-red-400" />
                )}
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    System Status
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 capitalize">
                    {healthStatus.status}
                  </dd>
                </dl>
              </div>
            </div>
            <div className="mt-4">
              <div className="text-sm text-gray-500">Available Features:</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {healthStatus.features.map((feature, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => (
          <div key={card.name} className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <card.icon className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      {card.name}
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {card.value}
                    </dd>
                  </dl>
                </div>
              </div>
              <div className="mt-4">
                <div className="flex items-center text-sm">
                  {card.changeType === 'increase' ? (
                    <TrendingUp className="flex-shrink-0 h-4 w-4 text-green-500" />
                  ) : (
                    <TrendingDown className="flex-shrink-0 h-4 w-4 text-red-500" />
                  )}
                  <span
                    className={`ml-1 ${
                      card.changeType === 'increase' ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {card.change}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Quick Actions
          </h3>
          <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            <div className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 cursor-pointer transition-colors">
              <div className="flex items-center">
                <BarChart3 className="h-8 w-8 text-indigo-600" />
                <div className="ml-4">
                  <h4 className="text-sm font-medium text-gray-900">
                    Analyze Company
                  </h4>
                  <p className="text-sm text-gray-500">
                    Calculate financial ratios and valuation
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 cursor-pointer transition-colors">
              <div className="flex items-center">
                <TrendingUp className="h-8 w-8 text-green-600" />
                <div className="ml-4">
                  <h4 className="text-sm font-medium text-gray-900">
                    Portfolio Review
                  </h4>
                  <p className="text-sm text-gray-500">
                    Review performance and allocations
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 cursor-pointer transition-colors">
              <div className="flex items-center">
                <Users className="h-8 w-8 text-blue-600" />
                <div className="ml-4">
                  <h4 className="text-sm font-medium text-gray-900">
                    Peer Comparison
                  </h4>
                  <p className="text-sm text-gray-500">
                    Compare with industry peers
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Recent Activity
          </h3>
          <div className="mt-5">
            <div className="flow-root">
              <ul className="-mb-8">
                <li>
                  <div className="relative pb-8">
                    <div className="relative flex space-x-3">
                      <div>
                        <span className="h-8 w-8 rounded-full bg-green-500 flex items-center justify-center ring-8 ring-white">
                          <CheckCircle className="h-5 w-5 text-white" />
                        </span>
                      </div>
                      <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                        <div>
                          <p className="text-sm text-gray-500">
                            Financial analysis completed for{' '}
                            <span className="font-medium text-gray-900">AAPL</span>
                          </p>
                        </div>
                        <div className="text-right text-sm whitespace-nowrap text-gray-500">
                          2 hours ago
                        </div>
                      </div>
                    </div>
                  </div>
                </li>
                <li>
                  <div className="relative pb-8">
                    <div className="relative flex space-x-3">
                      <div>
                        <span className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center ring-8 ring-white">
                          <BarChart3 className="h-5 w-5 text-white" />
                        </span>
                      </div>
                      <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                        <div>
                          <p className="text-sm text-gray-500">
                            Portfolio rebalancing suggested
                          </p>
                        </div>
                        <div className="text-right text-sm whitespace-nowrap text-gray-500">
                          1 day ago
                        </div>
                      </div>
                    </div>
                  </div>
                </li>
                <li>
                  <div className="relative">
                    <div className="relative flex space-x-3">
                      <div>
                        <span className="h-8 w-8 rounded-full bg-indigo-500 flex items-center justify-center ring-8 ring-white">
                          <TrendingUp className="h-5 w-5 text-white" />
                        </span>
                      </div>
                      <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                        <div>
                          <p className="text-sm text-gray-500">
                            New market data ingested for 15 companies
                          </p>
                        </div>
                        <div className="text-right text-sm whitespace-nowrap text-gray-500">
                          2 days ago
                        </div>
                      </div>
                    </div>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}