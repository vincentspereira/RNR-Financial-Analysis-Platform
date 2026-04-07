/**
 * Watchlist Manager Component
 */
import React, { useState, useEffect } from 'react';
import {
  Plus,
  Search,
  Filter,
  Bell,
  TrendingUp,
  TrendingDown,
  Eye,
  Settings,
  Star,
  AlertTriangle,
  CheckCircle,
  Clock,
  MoreHorizontal,
  Edit,
  Trash2,
  BarChart3,
} from 'lucide-react';
import { 
  Watchlist, 
  WatchlistItem, 
  WatchlistCategory, 
  Alert,
  WatchlistFilter,
  WatchlistSort,
  MarketData 
} from '@/types/watchlist';
import toast from 'react-hot-toast';
import { apiService } from '@/services/api';

interface WatchlistManagerProps {
  onAnalyzeCompany?: (symbol: string) => void;
}

export function WatchlistManager({ onAnalyzeCompany }: WatchlistManagerProps) {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [categories, setCategories] = useState<WatchlistCategory[]>([]);
  const [selectedWatchlist, setSelectedWatchlist] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<WatchlistFilter>({});
  const [sort, setSort] = useState<WatchlistSort>({ field: 'symbol', direction: 'asc' });
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState<WatchlistItem | null>(null);

  // Mock data for demonstration
  const mockCategories: WatchlistCategory[] = [
    {
      id: '1',
      name: 'Growth Stocks',
      description: 'High-growth potential companies',
      color: '#10B981',
      icon: 'trending-up',
      created_at: '2023-01-01T00:00:00Z',
    },
    {
      id: '2',
      name: 'Dividend Stocks',
      description: 'Dividend-paying companies',
      color: '#3B82F6',
      icon: 'dollar-sign',
      created_at: '2023-01-01T00:00:00Z',
    },
    {
      id: '3',
      name: 'Tech Watch',
      description: 'Technology sector monitoring',
      color: '#8B5CF6',
      icon: 'cpu',
      created_at: '2023-01-01T00:00:00Z',
    },
  ];

  const mockWatchlistItems: WatchlistItem[] = [
    {
      id: '1',
      company_id: '1',
      symbol: 'AAPL',
      company_name: 'Apple Inc.',
      sector: 'Technology',
      current_price: 197.80,
      price_change: 2.45,
      price_change_percentage: 1.25,
      volume: 45678900,
      market_cap: 3000000000000,
      added_date: '2023-01-15T00:00:00Z',
      last_updated: new Date().toISOString(),
      alerts: [],
      tags: ['large-cap', 'consumer-electronics'],
    },
    {
      id: '2',
      company_id: '2',
      symbol: 'MSFT',
      company_name: 'Microsoft Corporation',
      sector: 'Technology',
      current_price: 378.85,
      price_change: -1.23,
      price_change_percentage: -0.32,
      volume: 23456789,
      market_cap: 2800000000000,
      added_date: '2023-02-10T00:00:00Z',
      last_updated: new Date().toISOString(),
      alerts: [
        {
          id: 'a1',
          watchlist_item_id: '2',
          alert_type: 'price_above',
          condition: 'greater_than',
          threshold_value: 380,
          current_value: 378.85,
          is_active: true,
          is_triggered: false,
          created_at: '2023-02-10T00:00:00Z',
          notification_methods: ['email', 'push'],
        }
      ],
      tags: ['large-cap', 'cloud-computing'],
    },
    {
      id: '3',
      company_id: '3',
      symbol: 'TSLA',
      company_name: 'Tesla Inc.',
      sector: 'Consumer Discretionary',
      current_price: 248.50,
      price_change: 8.75,
      price_change_percentage: 3.65,
      volume: 67890123,
      market_cap: 800000000000,
      added_date: '2023-03-05T00:00:00Z',
      last_updated: new Date().toISOString(),
      alerts: [],
      tags: ['electric-vehicles', 'growth'],
    },
  ];

  const mockWatchlists: Watchlist[] = [
    {
      id: '1',
      name: 'Tech Giants',
      description: 'Large technology companies',
      category: mockCategories[2],
      items: mockWatchlistItems,
      created_at: '2023-01-01T00:00:00Z',
      updated_at: new Date().toISOString(),
      is_public: false,
      user_id: 'user1',
      color: '#8B5CF6',
      sort_order: 1,
    },
  ];

  useEffect(() => {
    loadWatchlists();
  }, []);

  const loadWatchlists = async () => {
    try {
      setIsLoading(true);

      // Fetch real watchlist data from API
      const response = await apiService.request({
        method: 'GET',
        url: '/api/v1/watchlist/',
      });

      if (response.data) {
        const fetched = response.data.watchlists || response.data;
        if (Array.isArray(fetched) && fetched.length > 0) {
          setWatchlists(fetched);
          setSelectedWatchlist(fetched[0]?.id || null);
        }
      }

    } catch (error) {
      console.error('Failed to load watchlists:', error);
      toast.error('Failed to load watchlists');
      setIsLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatVolume = (value: number) => {
    if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
    if (value >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
    return value.toString();
  };

  const getSelectedWatchlist = () => {
    return watchlists.find(w => w.id === selectedWatchlist);
  };

  const handleCreateWatchlist = () => {
    setShowCreateModal(true);
  };

  const handleAddToWatchlist = () => {
    toast.info('Add company to watchlist');
    // TODO: Implement add company modal
  };

  const handleCreateAlert = (item: WatchlistItem) => {
    setSelectedItem(item);
    setShowAlertModal(true);
  };

  const handleRemoveFromWatchlist = (itemId: string) => {
    if (confirm('Remove this company from watchlist?')) {
      toast.success('Company removed from watchlist');
      // TODO: Implement removal
    }
  };

  const currentWatchlist = getSelectedWatchlist();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Watchlist Manager</h1>
          <p className="mt-1 text-sm text-gray-600">
            Monitor and track your favorite companies with customizable alerts
          </p>
        </div>
        
        <div className="mt-4 sm:mt-0 flex space-x-3">
          <button
            onClick={handleCreateWatchlist}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Watchlist
          </button>
          <button
            onClick={handleAddToWatchlist}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Company
          </button>
        </div>
      </div>

      {/* Watchlist Tabs */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {watchlists.map((watchlist) => (
              <button
                key={watchlist.id}
                onClick={() => setSelectedWatchlist(watchlist.id)}
                className={`${
                  selectedWatchlist === watchlist.id
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
              >
                <div 
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: watchlist.color }}
                />
                <span>{watchlist.name}</span>
                <span className="bg-gray-100 text-gray-600 py-1 px-2 rounded-full text-xs">
                  {watchlist.items.length}
                </span>
              </button>
            ))}
          </nav>
        </div>

        {/* Search and Filters */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex flex-col sm:flex-row sm:items-center space-y-4 sm:space-y-0 sm:space-x-4">
            <div className="flex-1 relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="Search companies..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
              <Filter className="h-4 w-4 mr-2" />
              Filters
            </button>
            <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
              <Settings className="h-4 w-4 mr-2" />
              Settings
            </button>
          </div>
        </div>

        {/* Watchlist Content */}
        {currentWatchlist && (
          <div className="p-6">
            {/* Watchlist Info */}
            <div className="mb-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                    <div 
                      className="w-4 h-4 rounded-full mr-3"
                      style={{ backgroundColor: currentWatchlist.color }}
                    />
                    {currentWatchlist.name}
                  </h2>
                  {currentWatchlist.description && (
                    <p className="text-sm text-gray-600 mt-1">{currentWatchlist.description}</p>
                  )}
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-500">Last Updated</div>
                  <div className="text-sm font-medium text-gray-900">
                    {new Date(currentWatchlist.updated_at).toLocaleString()}
                  </div>
                </div>
              </div>
            </div>

            {/* Watchlist Table */}
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Company
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Price
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Change
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Volume
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Alerts
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {currentWatchlist.items.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10">
                            <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                              <span className="text-sm font-medium text-gray-700">
                                {item.symbol.charAt(0)}
                              </span>
                            </div>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">
                              {item.symbol}
                            </div>
                            <div className="text-sm text-gray-500">
                              {item.company_name}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {formatCurrency(item.current_price)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className="flex items-center">
                          {item.price_change_percentage >= 0 ? (
                            <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
                          ) : (
                            <TrendingDown className="h-4 w-4 text-red-500 mr-1" />
                          )}
                          <div className={`${
                            item.price_change_percentage >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                            <div className="font-medium">
                              {formatPercentage(item.price_change_percentage)}
                            </div>
                            <div className="text-xs">
                              {formatCurrency(item.price_change)}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatVolume(item.volume)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          {item.alerts.length > 0 ? (
                            <div className="flex items-center">
                              <Bell className="h-4 w-4 text-indigo-500 mr-1" />
                              <span className="text-sm text-gray-900">{item.alerts.length}</span>
                            </div>
                          ) : (
                            <button
                              onClick={() => handleCreateAlert(item)}
                              className="text-gray-400 hover:text-indigo-500"
                            >
                              <Bell className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div className="flex items-center space-x-2">
                          {onAnalyzeCompany && (
                            <button
                              onClick={() => onAnalyzeCompany(item.symbol)}
                              className="text-gray-400 hover:text-indigo-500"
                              title="Analyze Company"
                            >
                              <BarChart3 className="h-4 w-4" />
                            </button>
                          )}
                          <button
                            onClick={() => handleCreateAlert(item)}
                            className="text-gray-400 hover:text-yellow-500"
                            title="Create Alert"
                          >
                            <Bell className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleRemoveFromWatchlist(item.id)}
                            className="text-gray-400 hover:text-red-500"
                            title="Remove from Watchlist"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {currentWatchlist.items.length === 0 && (
              <div className="text-center py-12">
                <Eye className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No companies in this watchlist
                </h3>
                <p className="text-gray-600 mb-6">
                  Add companies to start monitoring their performance and set up alerts.
                </p>
                <button
                  onClick={handleAddToWatchlist}
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add First Company
                </button>
              </div>
            )}
          </div>
        )}

        {watchlists.length === 0 && (
          <div className="text-center py-12">
            <Star className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No watchlists yet
            </h3>
            <p className="text-gray-600 mb-6">
              Create your first watchlist to start monitoring companies.
            </p>
            <button
              onClick={handleCreateWatchlist}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
            >
              <Plus className="h-4 w-4 mr-2" />
              Create Watchlist
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default WatchlistManager;