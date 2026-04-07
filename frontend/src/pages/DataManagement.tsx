/**
 * Data Management Interface
 */
import React, { useState, useEffect } from 'react';
import {
  Database,
  Settings,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap,
  Shield,
  Activity,
  Download,
  Upload,
  Server,
  Key,
  BarChart3,
  TrendingUp,
  Calendar,
  Filter,
} from 'lucide-react';
import { DataSourceConfig } from '@/types/watchlist';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';

interface DataSource {
  id: string;
  name: string;
  provider: string;
  status: 'active' | 'inactive' | 'error' | 'syncing';
  last_sync: string;
  next_sync: string;
  api_calls_today: number;
  rate_limit: number;
  success_rate: number;
  error_count: number;
  data_points: number;
  latency_ms: number;
  cost_per_call: number;
  monthly_cost: number;
}

interface DataPipeline {
  id: string;
  name: string;
  source_id: string;
  status: 'running' | 'stopped' | 'error' | 'scheduled';
  schedule: string;
  last_run: string;
  next_run: string;
  processed_records: number;
  error_records: number;
  success_rate: number;
  avg_processing_time: number;
}

interface DataQualityMetric {
  metric: string;
  value: number;
  threshold: number;
  status: 'good' | 'warning' | 'critical';
  description: string;
}

export function DataManagement() {
  const [activeTab, setActiveTab] = useState<'sources' | 'pipelines' | 'quality' | 'monitoring'>('sources');
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [pipelines, setPipelines] = useState<DataPipeline[]>([]);
  const [qualityMetrics, setQualityMetrics] = useState<DataQualityMetric[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddSource, setShowAddSource] = useState(false);

  // Mock data for demonstration
  const mockDataSources: DataSource[] = [
    {
      id: '1',
      name: 'Alpha Vantage',
      provider: 'alpha_vantage',
      status: 'active',
      last_sync: '2023-12-01T10:30:00Z',
      next_sync: '2023-12-01T11:00:00Z',
      api_calls_today: 450,
      rate_limit: 500,
      success_rate: 99.2,
      error_count: 3,
      data_points: 125000,
      latency_ms: 250,
      cost_per_call: 0.002,
      monthly_cost: 89.50,
    },
    {
      id: '2',
      name: 'Yahoo Finance',
      provider: 'yahoo_finance',
      status: 'active',
      last_sync: '2023-12-01T10:25:00Z',
      next_sync: '2023-12-01T10:55:00Z',
      api_calls_today: 1200,
      rate_limit: 2000,
      success_rate: 97.8,
      error_count: 12,
      data_points: 89000,
      latency_ms: 180,
      cost_per_call: 0.0,
      monthly_cost: 0.0,
    },
    {
      id: '3',
      name: 'IEX Cloud',
      provider: 'iex_cloud',
      status: 'error',
      last_sync: '2023-12-01T09:15:00Z',
      next_sync: '2023-12-01T10:45:00Z',
      api_calls_today: 0,
      rate_limit: 1000,
      success_rate: 0,
      error_count: 15,
      data_points: 0,
      latency_ms: 0,
      cost_per_call: 0.001,
      monthly_cost: 45.20,
    },
  ];

  const mockPipelines: DataPipeline[] = [
    {
      id: '1',
      name: 'Real-time Price Updates',
      source_id: '1',
      status: 'running',
      schedule: 'Every 30 seconds',
      last_run: '2023-12-01T10:30:00Z',
      next_run: '2023-12-01T10:30:30Z',
      processed_records: 15420,
      error_records: 23,
      success_rate: 99.85,
      avg_processing_time: 1.2,
    },
    {
      id: '2',
      name: 'Daily Financial Statements',
      source_id: '1',
      status: 'scheduled',
      schedule: 'Daily at 6:00 AM',
      last_run: '2023-12-01T06:00:00Z',
      next_run: '2023-12-02T06:00:00Z',
      processed_records: 2340,
      error_records: 5,
      success_rate: 99.78,
      avg_processing_time: 45.6,
    },
    {
      id: '3',
      name: 'News Sentiment Analysis',
      source_id: '2',
      status: 'error',
      schedule: 'Every 15 minutes',
      last_run: '2023-12-01T09:45:00Z',
      next_run: '2023-12-01T10:45:00Z',
      processed_records: 0,
      error_records: 156,
      success_rate: 0,
      avg_processing_time: 0,
    },
  ];

  const mockQualityMetrics: DataQualityMetric[] = [
    {
      metric: 'Data Completeness',
      value: 98.5,
      threshold: 95,
      status: 'good',
      description: 'Percentage of expected data points received',
    },
    {
      metric: 'Data Accuracy',
      value: 99.2,
      threshold: 98,
      status: 'good',
      description: 'Accuracy of price data vs market sources',
    },
    {
      metric: 'Data Freshness',
      value: 87.3,
      threshold: 90,
      status: 'warning',
      description: 'Percentage of data updated within SLA',
    },
    {
      metric: 'Schema Compliance',
      value: 94.1,
      threshold: 98,
      status: 'critical',
      description: 'Data conforming to expected schema',
    },
  ];

  useEffect(() => {
    loadDataManagement();
  }, []);

  const loadDataManagement = async () => {
    try {
      setIsLoading(true);

      // Fetch real data sources from API
      const sourcesResponse = await apiService.getDataSourcesStatus();
      if (sourcesResponse) {
        setDataSources(sourcesResponse);
      }

    } catch (error) {
      console.error('Failed to load data management:', error);
      toast.error('Failed to load data management');
      setIsLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
      case 'running':
      case 'good':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'inactive':
      case 'stopped':
      case 'scheduled':
        return <Clock className="h-5 w-5 text-gray-500" />;
      case 'error':
      case 'critical':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'syncing':
        return <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
      case 'running':
      case 'good':
        return 'text-green-600 bg-green-100';
      case 'inactive':
      case 'stopped':
      case 'scheduled':
        return 'text-gray-600 bg-gray-100';
      case 'error':
      case 'critical':
        return 'text-red-600 bg-red-100';
      case 'syncing':
        return 'text-blue-600 bg-blue-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const handleSyncDataSource = (sourceId: string) => {
    toast.success('Data source sync initiated');
    // TODO: Implement sync
  };

  const handleToggleDataSource = (sourceId: string) => {
    toast.success('Data source status updated');
    // TODO: Implement toggle
  };

  const handleRunPipeline = (pipelineId: string) => {
    toast.success('Pipeline execution started');
    // TODO: Implement pipeline run
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Management</h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage data sources, pipelines, and monitor data quality
          </p>
        </div>
        
        <div className="mt-4 sm:mt-0 flex space-x-3">
          <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
            <Download className="h-4 w-4 mr-2" />
            Export Logs
          </button>
          <button
            onClick={() => setShowAddSource(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
          >
            <Database className="h-4 w-4 mr-2" />
            Add Data Source
          </button>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Database className="h-8 w-8 text-indigo-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Active Sources
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {dataSources.filter(s => s.status === 'active').length}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Activity className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Running Pipelines
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {pipelines.filter(p => p.status === 'running').length}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <BarChart3 className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Data Points Today
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {dataSources.reduce((sum, s) => sum + s.data_points, 0).toLocaleString()}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <TrendingUp className="h-8 w-8 text-purple-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Avg Success Rate
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {formatPercentage(dataSources.reduce((sum, s) => sum + s.success_rate, 0) / dataSources.length)}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {[
              { id: 'sources', name: 'Data Sources', icon: Database },
              { id: 'pipelines', name: 'Pipelines', icon: Zap },
              { id: 'quality', name: 'Data Quality', icon: Shield },
              { id: 'monitoring', name: 'Monitoring', icon: Activity },
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
          {/* Data Sources Tab */}
          {activeTab === 'sources' && (
            <div className="space-y-6">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Data Source
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        API Usage
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Performance
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Cost
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {dataSources.map((source) => (
                      <tr key={source.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <Server className="h-8 w-8 text-gray-400 mr-3" />
                            <div>
                              <div className="text-sm font-medium text-gray-900">
                                {source.name}
                              </div>
                              <div className="text-sm text-gray-500">
                                {source.provider}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            {getStatusIcon(source.status)}
                            <span className={`ml-2 inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(source.status)}`}>
                              {source.status}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          <div>
                            {source.api_calls_today} / {source.rate_limit}
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                            <div
                              className="bg-indigo-600 h-2 rounded-full"
                              style={{ width: `${(source.api_calls_today / source.rate_limit) * 100}%` }}
                            />
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          <div>Success: {formatPercentage(source.success_rate)}</div>
                          <div>Latency: {source.latency_ms}ms</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          <div>{formatCurrency(source.monthly_cost)}/mo</div>
                          <div className="text-xs text-gray-500">
                            {formatCurrency(source.cost_per_call)}/call
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleSyncDataSource(source.id)}
                              className="text-indigo-600 hover:text-indigo-900"
                            >
                              <RefreshCw className="h-4 w-4" />
                            </button>
                            <button className="text-gray-600 hover:text-gray-900">
                              <Settings className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Pipelines Tab */}
          {activeTab === 'pipelines' && (
            <div className="space-y-6">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Pipeline
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Schedule
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Performance
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {pipelines.map((pipeline) => (
                      <tr key={pipeline.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <Zap className="h-8 w-8 text-gray-400 mr-3" />
                            <div>
                              <div className="text-sm font-medium text-gray-900">
                                {pipeline.name}
                              </div>
                              <div className="text-sm text-gray-500">
                                Source: {dataSources.find(s => s.id === pipeline.source_id)?.name}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            {getStatusIcon(pipeline.status)}
                            <span className={`ml-2 inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(pipeline.status)}`}>
                              {pipeline.status}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          <div>{pipeline.schedule}</div>
                          <div className="text-xs text-gray-500">
                            Next: {new Date(pipeline.next_run).toLocaleString()}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          <div>Success: {formatPercentage(pipeline.success_rate)}</div>
                          <div>Avg Time: {pipeline.avg_processing_time}s</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleRunPipeline(pipeline.id)}
                              className="text-indigo-600 hover:text-indigo-900"
                            >
                              <Zap className="h-4 w-4" />
                            </button>
                            <button className="text-gray-600 hover:text-gray-900">
                              <Settings className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Data Quality Tab */}
          {activeTab === 'quality' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {qualityMetrics.map((metric, index) => (
                  <div key={index} className="bg-gray-50 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-medium text-gray-900">{metric.metric}</h3>
                      {getStatusIcon(metric.status)}
                    </div>
                    
                    <div className="mb-4">
                      <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>Current</span>
                        <span>Threshold: {metric.threshold}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className={`h-3 rounded-full ${
                            metric.status === 'good' ? 'bg-green-500' :
                            metric.status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${Math.min(100, metric.value)}%` }}
                        />
                      </div>
                      <div className="text-right text-sm font-medium text-gray-900 mt-1">
                        {formatPercentage(metric.value)}
                      </div>
                    </div>
                    
                    <p className="text-sm text-gray-600">{metric.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Monitoring Tab */}
          {activeTab === 'monitoring' && (
            <div className="space-y-6">
              <div className="text-center py-12">
                <Activity className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Real-time Monitoring Dashboard
                </h3>
                <p className="text-gray-600">
                  Advanced monitoring features including real-time metrics, alerting, and performance analytics coming soon.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}