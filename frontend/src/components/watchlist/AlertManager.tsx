/**
 * Alert Manager Component
 */
import React, { useState, useEffect } from 'react';
import {
  Bell,
  Plus,
  Settings,
  Trash2,
  Edit,
  CheckCircle,
  AlertTriangle,
  Clock,
  Mail,
  Smartphone,
  MessageSquare,
  Webhook,
  TrendingUp,
  TrendingDown,
  Volume2,
  DollarSign,
  BarChart3,
} from 'lucide-react';
import { 
  Alert, 
  AlertType, 
  AlertCondition, 
  NotificationMethod,
  AlertTemplate,
  AlertNotification 
} from '@/types/watchlist';
import toast from 'react-hot-toast';

interface AlertManagerProps {
  watchlistItemId?: string;
  symbol?: string;
  companyName?: string;
  onClose?: () => void;
}

export function AlertManager({ 
  watchlistItemId, 
  symbol, 
  companyName, 
  onClose 
}: AlertManagerProps) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [notifications, setNotifications] = useState<AlertNotification[]>([]);
  const [templates, setTemplates] = useState<AlertTemplate[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Form state
  const [formData, setFormData] = useState({
    alert_type: 'price_above' as AlertType,
    condition: 'greater_than' as AlertCondition,
    threshold_value: 0,
    notification_methods: ['email'] as NotificationMethod[],
    message: '',
  });

  // Mock data for demonstration
  const mockTemplates: AlertTemplate[] = [
    {
      id: '1',
      name: 'Price Above Target',
      description: 'Alert when price goes above a specific value',
      alert_type: 'price_above',
      default_condition: 'greater_than',
      default_threshold: 100,
      is_system_template: true,
    },
    {
      id: '2',
      name: 'Price Below Support',
      description: 'Alert when price falls below support level',
      alert_type: 'price_below',
      default_condition: 'less_than',
      default_threshold: 50,
      is_system_template: true,
    },
    {
      id: '3',
      name: 'Volume Spike',
      description: 'Alert when trading volume spikes significantly',
      alert_type: 'volume_spike',
      default_condition: 'percentage_change',
      default_threshold: 200,
      is_system_template: true,
    },
    {
      id: '4',
      name: 'Price Change Alert',
      description: 'Alert on significant price percentage changes',
      alert_type: 'price_change_percentage',
      default_condition: 'percentage_change',
      default_threshold: 5,
      is_system_template: true,
    },
  ];

  const mockAlerts: Alert[] = [
    {
      id: '1',
      watchlist_item_id: watchlistItemId || '1',
      alert_type: 'price_above',
      condition: 'greater_than',
      threshold_value: 200,
      current_value: 197.80,
      is_active: true,
      is_triggered: false,
      created_at: '2023-01-15T00:00:00Z',
      notification_methods: ['email', 'push'],
      message: 'AAPL reached target price',
    },
    {
      id: '2',
      watchlist_item_id: watchlistItemId || '1',
      alert_type: 'volume_spike',
      condition: 'percentage_change',
      threshold_value: 150,
      current_value: 120,
      is_active: true,
      is_triggered: false,
      created_at: '2023-02-10T00:00:00Z',
      notification_methods: ['push'],
      message: 'Unusual volume activity detected',
    },
  ];

  const mockNotifications: AlertNotification[] = [
    {
      id: '1',
      alert_id: '1',
      symbol: symbol || 'AAPL',
      company_name: companyName || 'Apple Inc.',
      alert_type: 'price_above',
      message: 'AAPL price reached $200.00 target',
      current_value: 200.50,
      threshold_value: 200,
      triggered_at: '2023-12-01T10:30:00Z',
      is_read: false,
      severity: 'medium',
    },
  ];

  useEffect(() => {
    loadAlerts();
  }, [watchlistItemId]);

  const loadAlerts = async () => {
    try {
      setIsLoading(true);
      
      // In a real app, this would fetch from the API
      setTimeout(() => {
        setAlerts(mockAlerts);
        setNotifications(mockNotifications);
        setTemplates(mockTemplates);
        setIsLoading(false);
      }, 500);
      
    } catch (error) {
      console.error('Failed to load alerts:', error);
      toast.error('Failed to load alerts');
      setIsLoading(false);
    }
  };

  const getAlertTypeIcon = (type: AlertType) => {
    switch (type) {
      case 'price_above':
      case 'price_below':
        return <DollarSign className="h-4 w-4" />;
      case 'price_change_percentage':
        return <TrendingUp className="h-4 w-4" />;
      case 'volume_spike':
        return <Volume2 className="h-4 w-4" />;
      case 'technical_indicator':
        return <BarChart3 className="h-4 w-4" />;
      default:
        return <Bell className="h-4 w-4" />;
    }
  };

  const getNotificationMethodIcon = (method: NotificationMethod) => {
    switch (method) {
      case 'email':
        return <Mail className="h-4 w-4" />;
      case 'push':
      case 'in_app':
        return <Smartphone className="h-4 w-4" />;
      case 'sms':
        return <MessageSquare className="h-4 w-4" />;
      case 'webhook':
        return <Webhook className="h-4 w-4" />;
      default:
        return <Bell className="h-4 w-4" />;
    }
  };

  const getAlertStatusColor = (alert: Alert) => {
    if (!alert.is_active) return 'text-gray-400';
    if (alert.is_triggered) return 'text-red-500';
    return 'text-green-500';
  };

  const handleCreateAlert = async () => {
    try {
      const newAlert: Alert = {
        id: Date.now().toString(),
        watchlist_item_id: watchlistItemId || '1',
        ...formData,
        current_value: 0,
        is_active: true,
        is_triggered: false,
        created_at: new Date().toISOString(),
      };

      setAlerts([...alerts, newAlert]);
      setShowCreateForm(false);
      setFormData({
        alert_type: 'price_above',
        condition: 'greater_than',
        threshold_value: 0,
        notification_methods: ['email'],
        message: '',
      });
      
      toast.success('Alert created successfully');
    } catch (error) {
      toast.error('Failed to create alert');
    }
  };

  const handleDeleteAlert = async (alertId: string) => {
    if (confirm('Are you sure you want to delete this alert?')) {
      setAlerts(alerts.filter(a => a.id !== alertId));
      toast.success('Alert deleted successfully');
    }
  };

  const handleToggleAlert = async (alertId: string) => {
    setAlerts(alerts.map(alert => 
      alert.id === alertId 
        ? { ...alert, is_active: !alert.is_active }
        : alert
    ));
    toast.success('Alert status updated');
  };

  const handleUseTemplate = (template: AlertTemplate) => {
    setFormData({
      alert_type: template.alert_type,
      condition: template.default_condition,
      threshold_value: template.default_threshold || 0,
      notification_methods: ['email'],
      message: template.description,
    });
    setShowCreateForm(true);
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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Alert Manager</h2>
          {symbol && (
            <p className="text-sm text-gray-600">
              Managing alerts for {symbol} - {companyName}
            </p>
          )}
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowCreateForm(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Alert
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              Close
            </button>
          )}
        </div>
      </div>

      {/* Recent Notifications */}
      {notifications.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Notifications</h3>
          <div className="space-y-3">
            {notifications.map((notification) => (
              <div
                key={notification.id}
                className={`p-4 rounded-lg border-l-4 ${
                  notification.severity === 'high' ? 'border-red-500 bg-red-50' :
                  notification.severity === 'medium' ? 'border-yellow-500 bg-yellow-50' :
                  'border-blue-500 bg-blue-50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center">
                      <span className="font-medium text-gray-900">
                        {notification.symbol}
                      </span>
                      <span className="ml-2 text-sm text-gray-600">
                        {notification.message}
                      </span>
                    </div>
                    <div className="text-sm text-gray-500 mt-1">
                      {new Date(notification.triggered_at).toLocaleString()}
                    </div>
                  </div>
                  {!notification.is_read && (
                    <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Alerts */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Active Alerts</h3>
        </div>
        
        <div className="p-6">
          {alerts.length > 0 ? (
            <div className="space-y-4">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-center space-x-4">
                    <div className={`${getAlertStatusColor(alert)}`}>
                      {getAlertTypeIcon(alert.alert_type)}
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">
                        {alert.alert_type.replace('_', ' ').toUpperCase()} Alert
                      </div>
                      <div className="text-sm text-gray-600">
                        {alert.condition} {alert.threshold_value}
                        {alert.message && ` - ${alert.message}`}
                      </div>
                      <div className="flex items-center space-x-2 mt-1">
                        {alert.notification_methods.map((method) => (
                          <div
                            key={method}
                            className="flex items-center text-xs text-gray-500"
                          >
                            {getNotificationMethodIcon(method)}
                            <span className="ml-1">{method}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <div className="text-right text-sm">
                      <div className="text-gray-900">
                        Current: {alert.current_value}
                      </div>
                      <div className="text-gray-500">
                        Target: {alert.threshold_value}
                      </div>
                    </div>
                    
                    <button
                      onClick={() => handleToggleAlert(alert.id)}
                      className={`p-2 rounded-md ${
                        alert.is_active 
                          ? 'text-green-600 hover:bg-green-50' 
                          : 'text-gray-400 hover:bg-gray-50'
                      }`}
                      title={alert.is_active ? 'Disable Alert' : 'Enable Alert'}
                    >
                      {alert.is_active ? <CheckCircle className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
                    </button>
                    
                    <button
                      onClick={() => setEditingAlert(alert)}
                      className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-md"
                      title="Edit Alert"
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    
                    <button
                      onClick={() => handleDeleteAlert(alert.id)}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md"
                      title="Delete Alert"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Bell className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-gray-900 mb-2">No alerts configured</h4>
              <p className="text-gray-600 mb-4">
                Set up alerts to monitor price movements and other market events.
              </p>
              <button
                onClick={() => setShowCreateForm(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create First Alert
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Alert Templates */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Templates</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {templates.map((template) => (
            <div
              key={template.id}
              className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer"
              onClick={() => handleUseTemplate(template)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-900">{template.name}</div>
                  <div className="text-sm text-gray-600">{template.description}</div>
                </div>
                <Plus className="h-4 w-4 text-gray-400" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Create Alert Form Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Alert</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Alert Type</label>
                  <select
                    value={formData.alert_type}
                    onChange={(e) => setFormData({ ...formData, alert_type: e.target.value as AlertType })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="price_above">Price Above</option>
                    <option value="price_below">Price Below</option>
                    <option value="price_change_percentage">Price Change %</option>
                    <option value="volume_spike">Volume Spike</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Threshold Value</label>
                  <input
                    type="number"
                    value={formData.threshold_value}
                    onChange={(e) => setFormData({ ...formData, threshold_value: parseFloat(e.target.value) })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Enter threshold value"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Message (Optional)</label>
                  <input
                    type="text"
                    value={formData.message}
                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Custom alert message"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Notification Methods</label>
                  <div className="mt-2 space-y-2">
                    {(['email', 'push', 'sms'] as NotificationMethod[]).map((method) => (
                      <label key={method} className="flex items-center">
                        <input
                          type="checkbox"
                          checked={formData.notification_methods.includes(method)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setFormData({
                                ...formData,
                                notification_methods: [...formData.notification_methods, method]
                              });
                            } else {
                              setFormData({
                                ...formData,
                                notification_methods: formData.notification_methods.filter(m => m !== method)
                              });
                            }
                          }}
                          className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        <span className="ml-2 text-sm text-gray-700 capitalize">{method}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateAlert}
                  className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md"
                >
                  Create Alert
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AlertManager;