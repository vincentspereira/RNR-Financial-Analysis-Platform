/**
 * ML Models Dashboard Component
 */
import React, { useState, useEffect } from 'react';
import {
  Brain,
  TrendingUp,
  Target,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Settings,
  Play,
  Pause,
  RefreshCw,
  BarChart3,
  Zap,
  Shield,
  Eye,
  Download,
} from 'lucide-react';
import {
  MLModel,
  ModelType,
  ModelStatus,
  Prediction,
  ModelPerformance,
  ModelTraining,
} from '@/types/analytics';
import { FinancialChart } from '@/components/charts/FinancialChart';
import toast from 'react-hot-toast';
import { apiService } from '@/services/api';

export function MLModelsDashboard() {
  const [models, setModels] = useState<MLModel[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [performance, setPerformance] = useState<ModelPerformance[]>([]);
  const [training, setTraining] = useState<ModelTraining[]>([]);
  const [activeTab, setActiveTab] = useState<'models' | 'predictions' | 'performance' | 'training'>('models');
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Mock data for demonstration
  const mockModels: MLModel[] = [
    {
      id: '1',
      name: 'Stock Price Predictor',
      type: 'price_prediction',
      version: '2.1.0',
      description: 'LSTM-based model for short-term price prediction',
      status: 'active',
      accuracy: 0.847,
      last_trained: '2023-11-28T10:00:00Z',
      training_data_size: 50000,
      features: ['price', 'volume', 'rsi', 'macd', 'bollinger_bands', 'news_sentiment'],
      target_variable: 'next_day_price',
      performance_metrics: {
        accuracy: 0.847,
        precision: 0.823,
        recall: 0.856,
        f1_score: 0.839,
        mse: 0.0234,
        mae: 0.0156,
        r_squared: 0.789,
      },
      created_at: '2023-01-15T00:00:00Z',
      updated_at: '2023-11-28T10:00:00Z',
    },
    {
      id: '2',
      name: 'Market Trend Analyzer',
      type: 'trend_analysis',
      version: '1.8.3',
      description: 'Ensemble model for market trend detection',
      status: 'active',
      accuracy: 0.762,
      last_trained: '2023-11-25T14:30:00Z',
      training_data_size: 75000,
      features: ['technical_indicators', 'market_breadth', 'sector_rotation', 'volatility'],
      target_variable: 'trend_direction',
      performance_metrics: {
        accuracy: 0.762,
        precision: 0.745,
        recall: 0.778,
        f1_score: 0.761,
      },
      created_at: '2023-02-01T00:00:00Z',
      updated_at: '2023-11-25T14:30:00Z',
    },
    {
      id: '3',
      name: 'Sentiment Analyzer',
      type: 'sentiment_analysis',
      version: '3.0.1',
      description: 'NLP model for financial news sentiment analysis',
      status: 'training',
      accuracy: 0.891,
      last_trained: '2023-11-20T09:15:00Z',
      training_data_size: 120000,
      features: ['news_text', 'source_credibility', 'article_length', 'social_mentions'],
      target_variable: 'sentiment_score',
      performance_metrics: {
        accuracy: 0.891,
        precision: 0.887,
        recall: 0.894,
        f1_score: 0.890,
      },
      created_at: '2023-03-10T00:00:00Z',
      updated_at: '2023-11-20T09:15:00Z',
    },
    {
      id: '4',
      name: 'Risk Assessment Engine',
      type: 'risk_assessment',
      version: '1.5.2',
      description: 'Multi-factor risk assessment model',
      status: 'active',
      accuracy: 0.823,
      last_trained: '2023-11-22T16:45:00Z',
      training_data_size: 35000,
      features: ['volatility', 'beta', 'correlation', 'liquidity', 'market_cap'],
      target_variable: 'risk_score',
      performance_metrics: {
        accuracy: 0.823,
        precision: 0.815,
        recall: 0.831,
        f1_score: 0.823,
      },
      created_at: '2023-04-05T00:00:00Z',
      updated_at: '2023-11-22T16:45:00Z',
    },
  ];

  const mockPredictions: Prediction[] = [
    {
      id: '1',
      model_id: '1',
      symbol: 'AAPL',
      prediction_type: 'price_target',
      predicted_value: 205.50,
      confidence: 0.847,
      features_used: {
        current_price: 197.80,
        volume: 45678900,
        rsi: 62.3,
        macd: 1.23,
        sentiment: 0.65,
      },
      prediction_date: '2023-12-01T10:00:00Z',
      target_date: '2023-12-02T10:00:00Z',
      explanation: 'Strong technical indicators and positive sentiment suggest upward movement',
    },
    {
      id: '2',
      model_id: '2',
      symbol: 'MSFT',
      prediction_type: 'trend_direction',
      predicted_value: 1, // 1 = bullish, 0 = neutral, -1 = bearish
      confidence: 0.762,
      features_used: {
        trend_strength: 0.78,
        market_breadth: 0.65,
        sector_momentum: 0.72,
      },
      prediction_date: '2023-12-01T10:00:00Z',
      target_date: '2023-12-08T10:00:00Z',
      explanation: 'Technical analysis indicates continued bullish trend',
    },
  ];

  useEffect(() => {
    loadMLModels();
  }, []);

  const loadMLModels = async () => {
    try {
      setIsLoading(true);

      // Fetch real ML model data from API
      const [modelsRes, predictionsRes] = await Promise.all([
        apiService.request({ method: 'GET', url: '/api/v1/analytics/models/performance' }),
        apiService.request({ method: 'GET', url: '/api/v1/analytics/predictions/history' }),
      ]);

      if (modelsRes.data?.models) {
        setModels(modelsRes.data.models);
      }
      if (predictionsRes.data?.predictions) {
        setPredictions(predictionsRes.data.predictions);
      }

    } catch (error) {
      console.error('Failed to load ML models:', error);
      toast.error('Failed to load ML models');
      setIsLoading(false);
    }
  };

  const getModelTypeIcon = (type: ModelType) => {
    switch (type) {
      case 'price_prediction':
        return <TrendingUp className="h-5 w-5" />;
      case 'trend_analysis':
        return <BarChart3 className="h-5 w-5" />;
      case 'sentiment_analysis':
        return <Eye className="h-5 w-5" />;
      case 'risk_assessment':
        return <Shield className="h-5 w-5" />;
      case 'volatility_forecast':
        return <Activity className="h-5 w-5" />;
      case 'anomaly_detection':
        return <AlertTriangle className="h-5 w-5" />;
      default:
        return <Brain className="h-5 w-5" />;
    }
  };

  const getStatusIcon = (status: ModelStatus) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'training':
        return <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'inactive':
        return <Pause className="h-4 w-4 text-gray-500" />;
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getStatusColor = (status: ModelStatus) => {
    switch (status) {
      case 'active':
        return 'text-green-600 bg-green-100';
      case 'training':
        return 'text-blue-600 bg-blue-100';
      case 'inactive':
        return 'text-gray-600 bg-gray-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-yellow-600 bg-yellow-100';
    }
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const handleToggleModel = (modelId: string) => {
    setModels(models.map(model => 
      model.id === modelId 
        ? { ...model, status: model.status === 'active' ? 'inactive' : 'active' }
        : model
    ));
    toast.success('Model status updated');
  };

  const handleRetrainModel = (modelId: string) => {
    toast.info('Model retraining initiated');
    // TODO: Implement model retraining
  };

  const handleRunPrediction = (modelId: string) => {
    toast.success('Prediction job started');
    // TODO: Implement prediction run
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
          <h1 className="text-2xl font-bold text-gray-900">ML Models Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage and monitor machine learning models for financial insights
          </p>
        </div>
        
        <div className="mt-4 sm:mt-0 flex space-x-3">
          <button className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
            <Download className="h-4 w-4 mr-2" />
            Export Models
          </button>
          <button className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700">
            <Brain className="h-4 w-4 mr-2" />
            Deploy Model
          </button>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Brain className="h-8 w-8 text-indigo-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Active Models
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {models.filter(m => m.status === 'active').length}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Target className="h-8 w-8 text-green-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Avg Accuracy
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {formatPercentage(models.reduce((sum, m) => sum + m.accuracy, 0) / models.length)}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Zap className="h-8 w-8 text-blue-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Predictions Today
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {predictions.length * 12} {/* Mock daily predictions */}
                </dd>
              </dl>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <RefreshCw className="h-8 w-8 text-purple-600" />
            </div>
            <div className="ml-5 w-0 flex-1">
              <dl>
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Training Jobs
                </dt>
                <dd className="text-lg font-medium text-gray-900">
                  {models.filter(m => m.status === 'training').length}
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
              { id: 'models', name: 'Models', icon: Brain },
              { id: 'predictions', name: 'Predictions', icon: Target },
              { id: 'performance', name: 'Performance', icon: BarChart3 },
              { id: 'training', name: 'Training', icon: RefreshCw },
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
          {/* Models Tab */}
          {activeTab === 'models' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {models.map((model) => (
                  <div key={model.id} className="bg-gray-50 rounded-lg p-6 hover:bg-gray-100 transition-colors">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center">
                        <div className="text-indigo-600 mr-3">
                          {getModelTypeIcon(model.type)}
                        </div>
                        <div>
                          <h3 className="text-lg font-medium text-gray-900">{model.name}</h3>
                          <p className="text-sm text-gray-600">v{model.version}</p>
                        </div>
                      </div>
                      <div className="flex items-center">
                        {getStatusIcon(model.status)}
                        <span className={`ml-2 inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(model.status)}`}>
                          {model.status}
                        </span>
                      </div>
                    </div>

                    <p className="text-sm text-gray-600 mb-4">{model.description}</p>

                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Accuracy</span>
                        <span className="font-medium text-gray-900">{formatPercentage(model.accuracy)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Training Data</span>
                        <span className="font-medium text-gray-900">{model.training_data_size.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Features</span>
                        <span className="font-medium text-gray-900">{model.features.length}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Last Trained</span>
                        <span className="font-medium text-gray-900">
                          {new Date(model.last_trained).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    <div className="flex space-x-2 mt-6">
                      <button
                        onClick={() => handleToggleModel(model.id)}
                        className="flex-1 inline-flex items-center justify-center px-3 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                      >
                        {model.status === 'active' ? <Pause className="h-4 w-4 mr-1" /> : <Play className="h-4 w-4 mr-1" />}
                        {model.status === 'active' ? 'Pause' : 'Activate'}
                      </button>
                      <button
                        onClick={() => handleRetrainModel(model.id)}
                        className="flex-1 inline-flex items-center justify-center px-3 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Retrain
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Predictions Tab */}
          {activeTab === 'predictions' && (
            <div className="space-y-6">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Model & Symbol
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Prediction
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Confidence
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Target Date
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {predictions.map((prediction) => {
                      const model = models.find(m => m.id === prediction.model_id);
                      return (
                        <tr key={prediction.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <div className="text-indigo-600 mr-3">
                                {getModelTypeIcon(model?.type || 'price_prediction')}
                              </div>
                              <div>
                                <div className="text-sm font-medium text-gray-900">
                                  {prediction.symbol}
                                </div>
                                <div className="text-sm text-gray-500">
                                  {model?.name}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900">
                              {prediction.prediction_type === 'price_target' 
                                ? `$${prediction.predicted_value.toFixed(2)}`
                                : prediction.predicted_value > 0 ? 'Bullish' : 'Bearish'
                              }
                            </div>
                            <div className="text-sm text-gray-500">
                              {prediction.prediction_type.replace('_', ' ')}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                                <div
                                  className="bg-indigo-600 h-2 rounded-full"
                                  style={{ width: `${prediction.confidence * 100}%` }}
                                />
                              </div>
                              <span className="text-sm text-gray-900">
                                {formatPercentage(prediction.confidence)}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {new Date(prediction.target_date).toLocaleDateString()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <button
                              onClick={() => handleRunPrediction(prediction.model_id)}
                              className="text-indigo-600 hover:text-indigo-900"
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Performance Tab */}
          {activeTab === 'performance' && (
            <div className="space-y-6">
              <div className="text-center py-12">
                <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Model Performance Analytics
                </h3>
                <p className="text-gray-600">
                  Detailed performance metrics, accuracy trends, and model comparison analytics coming soon.
                </p>
              </div>
            </div>
          )}

          {/* Training Tab */}
          {activeTab === 'training' && (
            <div className="space-y-6">
              <div className="text-center py-12">
                <RefreshCw className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Model Training Pipeline
                </h3>
                <p className="text-gray-600">
                  Training job management, hyperparameter tuning, and model versioning features coming soon.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}