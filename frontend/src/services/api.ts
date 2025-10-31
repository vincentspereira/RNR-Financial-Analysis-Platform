/**
 * API service layer with authentication and error handling
 */
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { AuthResponse, LoginRequest, RegisterRequest, User } from '@/types/auth';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiService {
  private api: AxiosInstance;
  private tokenRefreshPromise: Promise<string> | null = null;

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = this.getStoredToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for token refresh
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const newToken = await this.refreshAccessToken();
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return this.api(originalRequest);
          } catch (refreshError) {
            this.clearTokens();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private getStoredToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private getStoredRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  private setTokens(accessToken: string, refreshToken: string) {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  private clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  }

  private async refreshAccessToken(): Promise<string> {
    if (this.tokenRefreshPromise) {
      return this.tokenRefreshPromise;
    }

    this.tokenRefreshPromise = this.performTokenRefresh();
    
    try {
      const token = await this.tokenRefreshPromise;
      return token;
    } finally {
      this.tokenRefreshPromise = null;
    }
  }

  private async performTokenRefresh(): Promise<string> {
    const refreshToken = this.getStoredRefreshToken();
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
      refresh_token: refreshToken,
    });

    const { access_token, refresh_token: newRefreshToken } = response.data;
    this.setTokens(access_token, newRefreshToken);
    
    return access_token;
  }

  // Authentication endpoints
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await this.api.post<AuthResponse>('/api/v1/auth/login', credentials);
    const { access_token, refresh_token } = response.data;
    
    this.setTokens(access_token, refresh_token);
    localStorage.setItem('user', JSON.stringify(response.data.user));
    
    return response.data;
  }

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await this.api.post<AuthResponse>('/api/v1/auth/register', userData);
    const { access_token, refresh_token } = response.data;
    
    this.setTokens(access_token, refresh_token);
    localStorage.setItem('user', JSON.stringify(response.data.user));
    
    return response.data;
  }

  async logout(): Promise<void> {
    try {
      await this.api.post('/api/v1/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.clearTokens();
    }
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.api.get<User>('/api/v1/auth/me');
    return response.data;
  }

  async refreshToken(): Promise<AuthResponse> {
    const refreshToken = this.getStoredRefreshToken();
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await this.api.post<AuthResponse>('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });

    const { access_token, refresh_token: newRefreshToken } = response.data;
    this.setTokens(access_token, newRefreshToken);
    
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<{ status: string; features: string[] }> {
    const response = await this.api.get('/api/v1/health');
    return response.data;
  }

  // Financial endpoints
  async calculateFinancialRatios(data: {
    company_id: string;
    period_type: string;
    fiscal_year: number;
  }) {
    const response = await this.api.post('/api/v1/financial/ratios/calculate', data);
    return response.data;
  }

  async calculateValuation(data: {
    company_id: string;
    assumptions: Record<string, any>;
  }) {
    const response = await this.api.post('/api/v1/financial/valuation/calculate', data);
    return response.data;
  }

  // Data ingestion endpoints
  async ingestCompanyData(data: {
    symbol: string;
    force_update?: boolean;
  }) {
    const response = await this.api.post('/api/v1/data/ingest/company', data);
    return response.data;
  }

  async getDataSourcesStatus() {
    const response = await this.api.get('/api/v1/data/sources/status');
    return response.data;
  }

  // Generic request method
  async request<T = any>(config: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.api.request<T>(config);
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;