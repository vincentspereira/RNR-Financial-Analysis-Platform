/**
 * Analytics Page
 */
import React, { useState } from 'react';
import { Brain, TrendingUp, FileText, BarChart3 } from 'lucide-react';
import { MLModelsDashboard } from '@/components/analytics/MLModelsDashboard';
import { PredictiveAnalytics } from '@/components/analytics/PredictiveAnalytics';
import { ReportingSystem } from '@/components/reports/ReportingSystem';

export function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState<'models' | 'predictions' | 'reports'>('models');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Advanced Analytics</h1>
          <p className="mt-1 text-sm text-gray-600">
            Machine learning models, predictive analytics, and comprehensive reporting
          </p>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {[
              { id: 'models', name: 'ML Models', icon: Brain },
              { id: 'predictions', name: 'Predictive Analytics', icon: TrendingUp },
              { id: 'reports', name: 'Reports', icon: FileText },
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
          {/* ML Models Tab */}
          {activeTab === 'models' && <MLModelsDashboard />}

          {/* Predictive Analytics Tab */}
          {activeTab === 'predictions' && <PredictiveAnalytics />}

          {/* Reports Tab */}
          {activeTab === 'reports' && <ReportingSystem />}
        </div>
      </div>
    </div>
  );
}