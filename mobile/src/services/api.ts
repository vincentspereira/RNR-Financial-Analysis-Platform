import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

const API_BASE = __DEV__
  ? 'http://10.0.2.2:8000/api/v1'
  : 'https://api.finanalytica.com/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      await SecureStore.deleteItemAsync('auth_token');
    }
    return Promise.reject(error);
  },
);

// Auth
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (data: { email: string; password: string; first_name: string; last_name: string }) =>
    api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
};

// Companies
export const companiesApi = {
  search: (query: string) => api.get('/companies', { params: { search: query } }),
  getBySymbol: (symbol: string) => api.get(`/companies/${symbol}`),
};

// Market Data
export const marketApi = {
  getQuote: (symbol: string) => api.get(`/market-data/${symbol}`),
  getHistory: (symbol: string, range: string = '1M') =>
    api.get(`/market-data/${symbol}/history`, { params: { range } }),
};

// Portfolios
export const portfolioApi = {
  list: () => api.get('/portfolios'),
  get: (id: string) => api.get(`/portfolios/${id}`),
  positions: (id: string) => api.get(`/portfolios/${id}/positions`),
};

// Analytics
export const analyticsApi = {
  predict: (symbol: string, days: number = 30) =>
    api.post('/analytics/predict/stock-price', { symbol, days_ahead: days }),
  dlPredict: (symbol: string, days: number = 5, model: string = 'lstm') =>
    api.post('/analytics/dl/predict', { symbol, days_ahead: days, model_type: model }),
  risk: (portfolio: Record<string, number>) =>
    api.post('/analytics/analyze/portfolio-risk', { portfolio }),
};

// Sentiment
export const sentimentApi = {
  getSentiment: (symbol: string) => api.get(`/sentiment/${symbol}`),
  nlpAnalyze: (text: string) => api.post('/analytics/sentiment/nlp', { text }),
};

// Screener
export const screenerApi = {
  run: (filters: Record<string, any>) => api.get('/screener', { params: filters }),
};

export default api;
