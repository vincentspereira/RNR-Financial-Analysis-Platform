/**
 * Reporting System Component
 */
import React, { useState, useEffect } from 'react';
import {
  FileText,
  Download,
  Calendar,
  Settings,
  Send,
  Eye,
  Clock,
  CheckCircle,
  AlertCircle,
  BarChart3,
  PieChart,
  TrendingUp,
  Mail,
  Filter,
  Plus,
  Edit,
  Trash2,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { apiService } from '@/services/api';

interface Report {
  id: string;
  name: string;
  type: ReportType;
  template: string;
  status: ReportStatus;
  created_at: string;
  generated_at?: string;
  file_size?: number;
  download_url?: string;
  parameters: ReportParameters;
  schedule?: ReportSchedule;
}

type ReportType = 
  | 'portfolio_performance'
  | 'risk_analysis'
  | 'market_analysis'
  | 'watchlist_summary'
  | 'trading_activity'
  | 'compliance_report'
  | 'custom_dashboard';

type ReportStatus = 
  | 'draft'
  | 'generating'
  | 'completed'
  | 'failed'
  | 'scheduled';

interface ReportParameters {
  date_range: { start: string; end: string };
  symbols?: string[];
  portfolios?: string[];
  include_charts: boolean;
  include_analysis: boolean;
  format: 'pdf' | 'excel' | 'csv' | 'json';
  template_options: Record<string, any>;
}

interface ReportSchedule {
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  time: string;
  timezone: string;
  recipients: string[];
  is_active: boolean;
  next_run: string;
}

interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  type: ReportType;
  sections: ReportSection[];
  is_system_template: boolean;
  preview_url?: string;
}

interface ReportSection {
  id: string;
  name: string;
  type: 'chart' | 'table' | 'text' | 'metrics' | 'analysis';
  config: Record<string, any>;
  order: number;
}

export function ReportingSystem() {
  const [activeTab, setActiveTab] = useState<'reports' | 'templates' | 'scheduled'>('reports');
  const [reports, setReports] = useState<Report[]>([]);
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Mock data for demonstration
  const mockReports: Report[] = [
    {
      id: '1',
      name: 'Monthly Portfolio Performance',
      type: 'portfolio_performance',
      template: 'portfolio_standard',
      status: 'completed',
      created_at: '2023-12-01T10:00:00Z',
      generated_at: '2023-12-01T10:05:00Z',
      file_size: 2.4,
      download_url: '/reports/portfolio_nov_2023.pdf',
      parameters: {
        date_range: { start: '2023-11-01', end: '2023-11-30' },
        portfolios: ['portfolio_1'],
        include_charts: true,
        include_analysis: true,
        format: 'pdf',
        template_options: { show_benchmarks: true, include_risk_metrics: true },
      },
      schedule: {
        frequency: 'monthly',
        time: '09:00',
        timezone: 'UTC',
        recipients: ['investor@example.com'],
        is_active: true,
        next_run: '2023-12-31T09:00:00Z',
      },
    },
    {
      id: '2',
      name: 'Weekly Risk Analysis',
      type: 'risk_analysis',
      template: 'risk_comprehensive',
      status: 'generating',
      created_at: '2023-12-01T08:30:00Z',
      parameters: {
        date_range: { start: '2023-11-24', end: '2023-12-01' },
        symbols: ['AAPL', 'MSFT', 'GOOGL'],
        include_charts: true,
        include_analysis: true,
        format: 'pdf',
        template_options: { stress_test_scenarios: true, var_analysis: true },
      },
    },
    {
      id: '3',
      name: 'Market Analysis Dashboard',
      type: 'market_analysis',
      template: 'market_overview',
      status: 'failed',
      created_at: '2023-11-30T16:45:00Z',
      parameters: {
        date_range: { start: '2023-11-01', end: '2023-11-30' },
        include_charts: true,
        include_analysis: true,
        format: 'pdf',
        template_options: { sector_analysis: true, technical_indicators: true },
      },
    },
  ];

  const mockTemplates: ReportTemplate[] = [
    {
      id: '1',
      name: 'Standard Portfolio Report',
      description: 'Comprehensive portfolio performance analysis with charts and metrics',
      type: 'portfolio_performance',
      sections: [
        { id: '1', name: 'Executive Summary', type: 'text', config: {}, order: 1 },
        { id: '2', name: 'Performance Overview', type: 'metrics', config: {}, order: 2 },
        { id: '3', name: 'Asset Allocation', type: 'chart', config: { chart_type: 'pie' }, order: 3 },
        { id: '4', name: 'Performance Chart', type: 'chart', config: { chart_type: 'line' }, order: 4 },
        { id: '5', name: 'Holdings Table', type: 'table', config: {}, order: 5 },
      ],
      is_system_template: true,
      preview_url: '/templates/portfolio_standard_preview.png',
    },
    {
      id: '2',
      name: 'Risk Analysis Report',
      description: 'Detailed risk assessment with VaR, stress testing, and correlation analysis',
      type: 'risk_analysis',
      sections: [
        { id: '1', name: 'Risk Summary', type: 'metrics', config: {}, order: 1 },
        { id: '2', name: 'VaR Analysis', type: 'chart', config: { chart_type: 'histogram' }, order: 2 },
        { id: '3', name: 'Correlation Matrix', type: 'table', config: {}, order: 3 },
        { id: '4', name: 'Stress Test Results', type: 'analysis', config: {}, order: 4 },
      ],
      is_system_template: true,
      preview_url: '/templates/risk_analysis_preview.png',
    },
    {
      id: '3',
      name: 'Market Overview',
      description: 'Market trends, sector analysis, and economic indicators',
      type: 'market_analysis',
      sections: [
        { id: '1', name: 'Market Summary', type: 'text', config: {}, order: 1 },
        { id: '2', name: 'Index Performance', type: 'chart', config: { chart_type: 'line' }, order: 2 },
        { id: '3', name: 'Sector Performance', type: 'chart', config: { chart_type: 'bar' }, order: 3 },
        { id: '4', name: 'Economic Indicators', type: 'table', config: {}, order: 4 },
      ],
      is_system_template: true,
      preview_url: '/templates/market_overview_preview.png',
    },
  ];

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      setIsLoading(true);

      // Fetch real reports data from API
      const [reportsRes, templatesRes] = await Promise.all([
        apiService.request({ method: 'GET', url: '/api/v1/reports/history' }),
        apiService.request({ method: 'GET', url: '/api/v1/reports/templates' }),
      ]);

      if (reportsRes.data?.reports) {
        setReports(reportsRes.data.reports);
      }
      if (templatesRes.data?.templates) {
        setTemplates(templatesRes.data.templates);
      }

    } catch (error) {
      console.error('Failed to load reports:', error);
      toast.error('Failed to load reports');
      setIsLoading(false);
    }
  };

  const getReportTypeIcon = (type: ReportType) => {
    switch (type) {
      case 'portfolio_performance':
        return <TrendingUp className="h-5 w-5" />;
      case 'risk_analysis':
        return <BarChart3 className="h-5 w-5" />;
      case 'market_analysis':
        return <PieChart className="h-5 w-5" />;
      default:
        return <FileText className="h-5 w-5" />;
    }
  };

  const getStatusIcon = (status: ReportStatus) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'generating':
        return <Clock className="h-4 w-4 text-blue-500 animate-pulse" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'scheduled':
        return <Calendar className="h-4 w-4 text-purple-500" />;
      default:
        return <FileText className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: ReportStatus) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'generating':
        return 'text-blue-600 bg-blue-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      case 'scheduled':
        return 'text-purple-600 bg-purple-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const formatFileSize = (sizeInMB: number) => {
    return `${sizeInMB.toFixed(1)} MB`;
  };

  const handleGenerateReport = (templateId: string) => {
    toast.success('Report generation started');
    // TODO: Implement report generation
  };

  const handleDownloadReport = (report: Report) => {
    if (report.download_url) {
      toast.success('Downloading report...');
      // TODO: Implement download
    } else {
      toast.error('Report not available for download');
    }
  };

  const handleScheduleReport = (reportId: string) => {
    toast.info('Report scheduling configuration');
    // TODO: Implement scheduling modal
  };

  const handleDeleteReport = (reportId: string) => {
    if (confirm('Are you sure you want to delete this report?')) {
      setReports(reports.filter(r => r.id !== reportId));
      toast.success('Report deleted successfully');
    }
  };

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
          <h1 className="text-2xl font-bold text-gray-900">Reporting System</h1>
          <p className="mt-1 text-sm text-gray-600">
            Generate, schedule, and manage financial reports and analytics
          </p>
        </div>
        
        <div className="mt-4 sm:mt-0 flex space-x-3">
          <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Report
          </button>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <FileText className="h-8 w-8 text-indigo-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Total Reports
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {reports.length}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Completed
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {reports.filter(r => r.status === 'completed').length}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Calendar className="h-8 w-8 text-purple-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Scheduled
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {reports.filter(r => r.schedule?.is_active).length}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Download className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Downloads
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {reports.filter(r => r.download_url).length * 15} {/* Mock download count */}
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
              { id: 'reports', name: 'Reports', icon: FileText },
              { id: 'templates', name: 'Templates', icon: Settings },
              { id: 'scheduled', name: 'Scheduled', icon: Calendar },
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
          {/* Reports Tab */}
          {activeTab === 'reports' && (
            <div className="space-y-6">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Report
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Created
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Size
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {reports.map((report) => (
                      <tr key={report.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="text-indigo-600 mr-3">
                              {getReportTypeIcon(report.type)}
                            </div>
                            <div>
                              <div className="text-sm font-medium text-gray-900">
                                {report.name}
                              </div>
                              <div className="text-sm text-gray-500">
                                {report.type.replace('_', ' ')}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            {getStatusIcon(report.status)}
                            <span className={`ml-2 inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(report.status)}`}>
                              {report.status}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {new Date(report.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {report.file_size ? formatFileSize(report.file_size) : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex space-x-2">
                            {report.status === 'completed' && (
                              <button
                                onClick={() => handleDownloadReport(report)}
                                className="text-indigo-600 hover:text-indigo-900"
                                title="Download Report"
                              >
                                <Download className="h-4 w-4" />
                              </button>
                            )}
                            <button
                              onClick={() => setSelectedReport(report)}
                              className="text-gray-600 hover:text-gray-900"
                              title="View Details"
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleScheduleReport(report.id)}
                              className="text-purple-600 hover:text-purple-900"
                              title="Schedule Report"
                            >
                              <Calendar className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteReport(report.id)}
                              className="text-red-600 hover:text-red-900"
                              title="Delete Report"
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
            </div>
          )}

          {/* Templates Tab */}
          {activeTab === 'templates' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {templates.map((template) => (
                  <div key={template.id} className="bg-gray-50 rounded-lg p-6 hover:bg-gray-100 transition-colors">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center">
                        <div className="text-indigo-600 mr-3">
                          {getReportTypeIcon(template.type)}
                        </div>
                        <div>
                          <h3 className="text-lg font-medium text-gray-900">{template.name}</h3>
                          <p className="text-sm text-gray-600">{template.type.replace('_', ' ')}</p>
                        </div>
                      </div>
                      {template.is_system_template && (
                        <span className="inline-flex px-2 py-1 text-xs font-semibold text-blue-600 bg-blue-100 rounded-full">
                          System
                        </span>
                      )}
                    </div>

                    <p className="text-sm text-gray-600 mb-4">{template.description}</p>

                    <div className="space-y-2 mb-4">
                      <div className="text-sm font-medium text-gray-700">Sections ({template.sections.length})</div>
                      <div className="flex flex-wrap gap-1">
                        {template.sections.slice(0, 3).map((section) => (
                          <span key={section.id} className="inline-flex px-2 py-1 text-xs text-gray-600 bg-gray-200 rounded">
                            {section.name}
                          </span>
                        ))}
                        {template.sections.length > 3 && (
                          <span className="inline-flex px-2 py-1 text-xs text-gray-600 bg-gray-200 rounded">
                            +{template.sections.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleGenerateReport(template.id)}
                        className="flex-1 inline-flex items-center justify-center px-3 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                      >
                        <FileText className="h-4 w-4 mr-1" />
                        Generate
                      </button>
                      <button className="inline-flex items-center justify-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                        <Eye className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Scheduled Tab */}
          {activeTab === 'scheduled' && (
            <div className="space-y-6">
              <div className="text-center py-12">
                <Calendar className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Scheduled Reports Management
                </h3>
                <p className="text-gray-600">
                  Configure automated report generation and delivery schedules.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}