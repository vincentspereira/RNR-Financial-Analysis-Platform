/**
 * Admin Dashboard Page Component
 */
import React, { useState, useEffect } from 'react';
import {
  Users,
  Activity,
  DollarSign,
  TrendingUp,
  Shield,
  BarChart3,
  AlertCircle,
  RefreshCw,
  Search,
  ChevronLeft,
  ChevronRight,
  Ban,
  CheckCircle,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';

interface UserSummary {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  subscription_tier: string;
  created_at: string;
  last_login: string | null;
  portfolio_count: number;
  total_trades: number;
}

interface SystemMetrics {
  total_users: number;
  active_users_24h: number;
  active_users_7d: number;
  active_users_30d: number;
  total_portfolios: number;
  total_trades: number;
  total_alerts_configured: number;
  api_calls_today: number;
  api_calls_7d: number;
  average_response_time_ms: number;
  uptime_percentage: number;
  storage_used_gb: number;
  error_rate_percentage: number;
}

interface RevenueMetrics {
  mrr: number;
  total_revenue: number;
  subscribers_by_tier: Record<string, number>;
  revenue_by_tier: Record<string, number>;
  churn_rate: number;
  new_subscribers_30d: number;
  cancelled_subscribers_30d: number;
}

interface ActivityLogEntry {
  timestamp: string;
  user_email: string;
  action: string;
  details: string | null;
  ip_address: string | null;
}

type TabType = 'users' | 'metrics' | 'activity';

export function Admin() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<TabType>('users');
  const [isLoading, setIsLoading] = useState(true);

  // Users state
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [userPage, setUserPage] = useState(1);
  const [userSearch, setUserSearch] = useState('');

  // Metrics state
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [revenueMetrics, setRevenueMetrics] = useState<RevenueMetrics | null>(null);

  // Activity log state
  const [activityLog, setActivityLog] = useState<ActivityLogEntry[]>([]);
  const [activityPage, setActivityPage] = useState(1);

  useEffect(() => {
    loadTabData();
  }, [activeTab, userPage, activityPage]);

  const loadTabData = async () => {
    try {
      setIsLoading(true);

      if (activeTab === 'users') {
        const response = await apiService.request({
          method: 'GET',
          url: '/api/v1/admin/users',
          params: { page: userPage, page_size: 20, search: userSearch || undefined },
        });
        if (response.data) {
          setUsers(response.data.users || []);
          setTotalUsers(response.data.total || 0);
        }
      } else if (activeTab === 'metrics') {
        const [metricsRes, revenueRes] = await Promise.allSettled([
          apiService.request({ method: 'GET', url: '/api/v1/admin/metrics' }),
          apiService.request({ method: 'GET', url: '/api/v1/admin/revenue' }),
        ]);
        if (metricsRes.status === 'fulfilled' && metricsRes.value.data) {
          setSystemMetrics(metricsRes.value.data);
        }
        if (revenueRes.status === 'fulfilled' && revenueRes.value.data) {
          setRevenueMetrics(revenueRes.value.data);
        }
      } else if (activeTab === 'activity') {
        const response = await apiService.request({
          method: 'GET',
          url: '/api/v1/admin/activity-log',
          params: { page: activityPage, page_size: 20 },
        });
        if (response.data) {
          setActivityLog(response.data.entries || []);
        }
      }
    } catch (error) {
      console.error('Failed to load admin data:', error);
      toast.error('Failed to load data');
    } finally {
      setIsLoading(false);
    }
  };

  const updateUser = async (userId: string, updates: Record<string, any>) => {
    try {
      await apiService.request({
        method: 'PATCH',
        url: `/api/v1/admin/users/${userId}`,
        data: updates,
      });
      setUsers(users.map(u => u.id === userId ? { ...u, ...updates } : u));
      toast.success('User updated');
    } catch (error) {
      toast.error('Failed to update user');
    }
  };

  // Admin-only guard
  if (user?.role !== 'admin') {
    return (
      <div className="text-center py-12">
        <Shield className="h-12 w-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Access Denied</h3>
        <p className="text-gray-600">You need administrator privileges to access this page.</p>
      </div>
    );
  }

  const tabs: { id: TabType; name: string; Icon: typeof Users }[] = [
    { id: 'users', name: 'User Management', Icon: Users },
    { id: 'metrics', name: 'System Metrics', Icon: Activity },
    { id: 'activity', name: 'Activity Log', Icon: BarChart3 },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="mt-1 text-sm text-gray-600">
          System management, user administration, and analytics
        </p>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`${
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
              >
                <tab.Icon className="h-4 w-4" />
                <span>{tab.name}</span>
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 text-indigo-600 animate-spin" />
            </div>
          ) : (
            <>
              {/* Users Tab */}
              {activeTab === 'users' && (
                <div>
                  {/* Search */}
                  <div className="mb-4 flex items-center space-x-3">
                    <div className="relative flex-1 max-w-md">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                      <input
                        type="text"
                        value={userSearch}
                        onChange={(e) => setUserSearch(e.target.value)}
                        placeholder="Search users by email or name..."
                        className="w-full pl-10 rounded-md border-gray-300 text-sm focus:border-indigo-500 focus:ring-indigo-500"
                      />
                    </div>
                    <button
                      onClick={loadTabData}
                      className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 bg-white hover:bg-gray-50"
                    >
                      Search
                    </button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tier</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Portfolios</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Login</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {users.map((u) => (
                          <tr key={u.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm text-gray-900">{u.email}</td>
                            <td className="px-4 py-3 text-sm text-gray-500">{u.full_name || '-'}</td>
                            <td className="px-4 py-3">
                              <select
                                value={u.role}
                                onChange={(e) => updateUser(u.id, { role: e.target.value })}
                                className="text-xs rounded border-gray-300"
                              >
                                <option value="user">User</option>
                                <option value="premium">Premium</option>
                                <option value="admin">Admin</option>
                              </select>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                u.subscription_tier === 'enterprise' ? 'bg-purple-100 text-purple-800' :
                                u.subscription_tier === 'pro' ? 'bg-blue-100 text-blue-800' :
                                'bg-gray-100 text-gray-800'
                              }`}>
                                {u.subscription_tier}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              {u.is_active ? (
                                <CheckCircle className="h-4 w-4 text-green-500" />
                              ) : (
                                <Ban className="h-4 w-4 text-red-500" />
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500">{u.portfolio_count}</td>
                            <td className="px-4 py-3 text-sm text-gray-500">
                              {u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <button
                                onClick={() => updateUser(u.id, { is_active: !u.is_active })}
                                className={`text-xs font-medium ${u.is_active ? 'text-red-600 hover:text-red-800' : 'text-green-600 hover:text-green-800'}`}
                              >
                                {u.is_active ? 'Deactivate' : 'Activate'}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  <div className="flex items-center justify-between mt-4">
                    <span className="text-sm text-gray-500">
                      Showing {(userPage - 1) * 20 + 1}-{Math.min(userPage * 20, totalUsers)} of {totalUsers}
                    </span>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => setUserPage(p => Math.max(1, p - 1))}
                        disabled={userPage === 1}
                        className="p-2 rounded border border-gray-300 disabled:opacity-50"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => setUserPage(p => p + 1)}
                        disabled={userPage * 20 >= totalUsers}
                        className="p-2 rounded border border-gray-300 disabled:opacity-50"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Metrics Tab */}
              {activeTab === 'metrics' && systemMetrics && (
                <div className="space-y-6">
                  <h3 className="text-lg font-medium text-gray-900">System Metrics</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[
                      { label: 'Total Users', value: String(systemMetrics.total_users), Icon: Users, color: 'text-blue-600' },
                      { label: 'Active Users (24h)', value: String(systemMetrics.active_users_24h), Icon: Activity, color: 'text-green-600' },
                      { label: 'Active Users (7d)', value: String(systemMetrics.active_users_7d), Icon: Activity, color: 'text-green-600' },
                      { label: 'API Calls Today', value: systemMetrics.api_calls_today.toLocaleString(), Icon: BarChart3, color: 'text-indigo-600' },
                      { label: 'Avg Response Time', value: `${systemMetrics.average_response_time_ms.toFixed(0)}ms`, Icon: Activity, color: 'text-yellow-600' },
                      { label: 'Error Rate', value: `${systemMetrics.error_rate_percentage.toFixed(2)}%`, Icon: AlertCircle, color: 'text-red-600' },
                      { label: 'Uptime', value: `${systemMetrics.uptime_percentage.toFixed(2)}%`, Icon: CheckCircle, color: 'text-green-600' },
                      { label: 'Storage Used', value: `${systemMetrics.storage_used_gb.toFixed(1)} GB`, Icon: BarChart3, color: 'text-purple-600' },
                    ].map((metric) => (
                      <div key={metric.label} className="bg-white border rounded-lg p-4">
                        <div className="flex items-center">
                          <metric.Icon className={`h-5 w-5 ${metric.color}`} />
                          <span className="ml-2 text-sm text-gray-500">{metric.label}</span>
                        </div>
                        <p className="mt-2 text-xl font-bold text-gray-900">{metric.value}</p>
                      </div>
                    ))}
                  </div>

                  {/* Revenue Section */}
                  {revenueMetrics && (
                    <>
                      <h3 className="text-lg font-medium text-gray-900 pt-4">Revenue</h3>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="bg-white border rounded-lg p-4">
                          <div className="flex items-center">
                            <DollarSign className="h-5 w-5 text-green-600" />
                            <span className="ml-2 text-sm text-gray-500">Monthly Recurring Revenue</span>
                          </div>
                          <p className="mt-2 text-xl font-bold text-gray-900">
                            ${revenueMetrics.mrr.toLocaleString()}
                          </p>
                        </div>
                        <div className="bg-white border rounded-lg p-4">
                          <div className="flex items-center">
                            <TrendingUp className="h-5 w-5 text-blue-600" />
                            <span className="ml-2 text-sm text-gray-500">Total Revenue</span>
                          </div>
                          <p className="mt-2 text-xl font-bold text-gray-900">
                            ${revenueMetrics.total_revenue.toLocaleString()}
                          </p>
                        </div>
                        <div className="bg-white border rounded-lg p-4">
                          <div className="flex items-center">
                            <AlertCircle className="h-5 w-5 text-red-600" />
                            <span className="ml-2 text-sm text-gray-500">Churn Rate</span>
                          </div>
                          <p className="mt-2 text-xl font-bold text-gray-900">
                            {revenueMetrics.churn_rate.toFixed(1)}%
                          </p>
                        </div>
                      </div>

                      {/* Subscribers by Tier */}
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {Object.entries(revenueMetrics.subscribers_by_tier).map(([tier, count]) => (
                          <div key={tier} className="bg-gray-50 rounded-lg p-4 text-center">
                            <p className="text-sm font-medium text-gray-500 capitalize">{tier}</p>
                            <p className="text-2xl font-bold text-gray-900">{count}</p>
                            <p className="text-xs text-gray-400">
                              ${(revenueMetrics.revenue_by_tier[tier] || 0).toLocaleString()}/mo
                            </p>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Activity Log Tab */}
              {activeTab === 'activity' && (
                <div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Details</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">IP</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {activityLog.map((entry, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm text-gray-500">
                              {new Date(entry.timestamp).toLocaleString()}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900">{entry.user_email}</td>
                            <td className="px-4 py-3">
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                {entry.action}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">
                              {entry.details || '-'}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-400 font-mono">
                              {entry.ip_address || '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="flex items-center justify-end mt-4 space-x-2">
                    <button
                      onClick={() => setActivityPage(p => Math.max(1, p - 1))}
                      disabled={activityPage === 1}
                      className="p-2 rounded border border-gray-300 disabled:opacity-50"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <span className="text-sm text-gray-500">Page {activityPage}</span>
                    <button
                      onClick={() => setActivityPage(p => p + 1)}
                      className="p-2 rounded border border-gray-300"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
