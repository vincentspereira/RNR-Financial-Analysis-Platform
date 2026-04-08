/**
 * Notifications & Alerts Page Component
 */
import React, { useState, useEffect } from 'react';
import {
  Bell,
  BellOff,
  Plus,
  Trash2,
  Check,
  CheckCheck,
  AlertCircle,
  AlertTriangle,
  Info,
  X,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';

interface AlertCondition {
  type: string;
  symbol?: string;
  portfolio_id?: string;
  threshold: number;
  direction?: string;
}

interface Alert {
  id: string;
  user_id: string;
  name: string;
  condition: AlertCondition;
  notification_methods: string[];
  is_active: boolean;
  triggered_count: number;
  last_triggered: string | null;
  created_at: string;
}

interface Notification {
  id: string;
  user_id: string;
  alert_id?: string;
  title: string;
  message: string;
  severity: string;
  is_read: boolean;
  created_at: string;
  data?: Record<string, any>;
}

const SEVERITY_CONFIG: Record<string, { icon: typeof Info; color: string; bg: string }> = {
  info: { icon: Info, color: 'text-blue-600', bg: 'bg-blue-100' },
  warning: { icon: AlertTriangle, color: 'text-yellow-600', bg: 'bg-yellow-100' },
  critical: { icon: AlertCircle, color: 'text-red-600', bg: 'bg-red-100' },
};

export function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateAlert, setShowCreateAlert] = useState(false);

  // New alert form state
  const [alertName, setAlertName] = useState('');
  const [alertType, setAlertType] = useState('price_above');
  const [alertSymbol, setAlertSymbol] = useState('');
  const [alertThreshold, setAlertThreshold] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [notifRes, alertRes] = await Promise.allSettled([
        apiService.request({ method: 'GET', url: '/api/v1/notifications' }),
        apiService.request({ method: 'GET', url: '/api/v1/notifications/alerts' }),
      ]);

      if (notifRes.status === 'fulfilled' && notifRes.value.data) {
        setNotifications(notifRes.value.data.notifications || []);
        setUnreadCount(notifRes.value.data.unread_count || 0);
      }
      if (alertRes.status === 'fulfilled' && alertRes.value.data) {
        setAlerts(alertRes.value.data || []);
      }
    } catch (error) {
      console.error('Failed to load notifications:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createAlert = async () => {
    try {
      await apiService.request({
        method: 'POST',
        url: '/api/v1/notifications/alerts',
        data: {
          name: alertName,
          condition: {
            type: alertType,
            symbol: alertSymbol || undefined,
            threshold: parseFloat(alertThreshold),
          },
          notification_methods: ['in_app'],
        },
      });
      toast.success('Alert created successfully');
      setShowCreateAlert(false);
      setAlertName('');
      setAlertType('price_above');
      setAlertSymbol('');
      setAlertThreshold('');
      loadData();
    } catch (error) {
      toast.error('Failed to create alert');
    }
  };

  const toggleAlert = async (alertId: string, currentActive: boolean) => {
    try {
      await apiService.request({
        method: 'PATCH',
        url: `/api/v1/notifications/alerts/${alertId}`,
        data: { is_active: !currentActive },
      });
      setAlerts(alerts.map(a => a.id === alertId ? { ...a, is_active: !currentActive } : a));
      toast.success(currentActive ? 'Alert paused' : 'Alert activated');
    } catch (error) {
      toast.error('Failed to update alert');
    }
  };

  const deleteAlert = async (alertId: string) => {
    try {
      await apiService.request({
        method: 'DELETE',
        url: `/api/v1/notifications/alerts/${alertId}`,
      });
      setAlerts(alerts.filter(a => a.id !== alertId));
      toast.success('Alert deleted');
    } catch (error) {
      toast.error('Failed to delete alert');
    }
  };

  const markAsRead = async (notificationId: string) => {
    try {
      await apiService.request({
        method: 'PATCH',
        url: `/api/v1/notifications/${notificationId}/read`,
      });
      setNotifications(notifications.map(n => n.id === notificationId ? { ...n, is_read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  const markAllRead = async () => {
    try {
      await apiService.request({ method: 'POST', url: '/api/v1/notifications/mark-all-read' });
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
      toast.success('All notifications marked as read');
    } catch (error) {
      toast.error('Failed to mark all as read');
    }
  };

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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Notifications & Alerts</h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage price alerts, portfolio alerts, and notifications
          </p>
        </div>
        <div className="mt-4 sm:mt-0 flex items-center space-x-3">
          <button
            onClick={markAllRead}
            disabled={unreadCount === 0}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            <CheckCheck className="h-4 w-4 mr-1" />
            Mark All Read
          </button>
          <button
            onClick={() => setShowCreateAlert(!showCreateAlert)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Alert
          </button>
        </div>
      </div>

      {/* Create Alert Form */}
      {showCreateAlert && (
        <div className="bg-white shadow rounded-lg p-6 border border-indigo-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">Create New Alert</h3>
            <button onClick={() => setShowCreateAlert(false)}>
              <X className="h-5 w-5 text-gray-400" />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Alert Name</label>
              <input
                type="text"
                value={alertName}
                onChange={(e) => setAlertName(e.target.value)}
                placeholder="e.g., AAPL above $200"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Alert Type</label>
              <select
                value={alertType}
                onChange={(e) => setAlertType(e.target.value)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              >
                <option value="price_above">Price Above</option>
                <option value="price_below">Price Below</option>
                <option value="price_crosses">Price Crosses</option>
                <option value="volume_above">Volume Above</option>
                <option value="change_percent">Change %</option>
                <option value="drawdown_percent">Drawdown %</option>
                <option value="profit_target">Profit Target</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Symbol</label>
              <input
                type="text"
                value={alertSymbol}
                onChange={(e) => setAlertSymbol(e.target.value.toUpperCase())}
                placeholder="e.g., AAPL"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Threshold</label>
              <input
                type="number"
                value={alertThreshold}
                onChange={(e) => setAlertThreshold(e.target.value)}
                placeholder="e.g., 200"
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <button
              onClick={createAlert}
              disabled={!alertName || !alertThreshold}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              Create Alert
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Notifications List */}
        <div className="lg:col-span-2 bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">
                Notifications
                {unreadCount > 0 && (
                  <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                    {unreadCount} unread
                  </span>
                )}
              </h3>
              <Bell className="h-5 w-5 text-gray-400" />
            </div>
          </div>
          <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
            {notifications.length > 0 ? (
              notifications.map((notif) => {
                const config = SEVERITY_CONFIG[notif.severity] || SEVERITY_CONFIG.info;
                const SevIcon = config.icon;
                return (
                  <div
                    key={notif.id}
                    className={`px-4 py-4 hover:bg-gray-50 transition-colors ${
                      !notif.is_read ? 'bg-indigo-50' : ''
                    }`}
                  >
                    <div className="flex items-start space-x-3">
                      <div className={`flex-shrink-0 p-1 rounded-full ${config.bg}`}>
                        <SevIcon className={`h-4 w-4 ${config.color}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className={`text-sm font-medium ${!notif.is_read ? 'text-gray-900' : 'text-gray-700'}`}>
                            {notif.title}
                          </p>
                          {!notif.is_read && (
                            <button
                              onClick={() => markAsRead(notif.id)}
                              className="ml-2 text-indigo-600 hover:text-indigo-800"
                            >
                              <Check className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                        <p className="mt-1 text-sm text-gray-500">{notif.message}</p>
                        <p className="mt-1 text-xs text-gray-400">
                          {new Date(notif.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="px-4 py-12 text-center">
                <BellOff className="h-10 w-10 mx-auto text-gray-300 mb-3" />
                <p className="text-gray-500">No notifications yet</p>
                <p className="text-sm text-gray-400">Create alerts to start receiving notifications</p>
              </div>
            )}
          </div>
        </div>

        {/* Alerts Management */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">Active Alerts</h3>
              <AlertCircle className="h-5 w-5 text-gray-400" />
            </div>
          </div>
          <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
            {alerts.length > 0 ? (
              alerts.map((alert) => (
                <div key={alert.id} className="px-4 py-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{alert.name}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {alert.condition.type.replace(/_/g, ' ')}
                        {alert.condition.symbol && ` - ${alert.condition.symbol}`}
                        {' '}&middot; {alert.condition.threshold}
                      </p>
                      <div className="flex items-center mt-2 space-x-2">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          alert.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                        }`}>
                          {alert.is_active ? 'Active' : 'Paused'}
                        </span>
                        <span className="text-xs text-gray-400">
                          Triggered {alert.triggered_count}x
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 ml-2">
                      <button
                        onClick={() => toggleAlert(alert.id, alert.is_active)}
                        title={alert.is_active ? 'Pause alert' : 'Activate alert'}
                      >
                        {alert.is_active ? (
                          <ToggleRight className="h-6 w-6 text-green-500" />
                        ) : (
                          <ToggleLeft className="h-6 w-6 text-gray-400" />
                        )}
                      </button>
                      <button
                        onClick={() => deleteAlert(alert.id)}
                        className="text-gray-400 hover:text-red-500"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="px-4 py-12 text-center">
                <AlertCircle className="h-10 w-10 mx-auto text-gray-300 mb-3" />
                <p className="text-gray-500">No alerts configured</p>
                <p className="text-sm text-gray-400">Create your first alert to get started</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
