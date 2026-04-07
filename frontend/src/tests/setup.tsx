/**
 * Test setup configuration for the Financial Analysis Platform frontend
 */
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, afterAll } from 'vitest';

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock Chart.js
vi.mock('chart.js', () => ({
  Chart: {
    register: vi.fn(),
  },
  CategoryScale: vi.fn(),
  LinearScale: vi.fn(),
  PointElement: vi.fn(),
  LineElement: vi.fn(),
  BarElement: vi.fn(),
  ArcElement: vi.fn(),
  Title: vi.fn(),
  Tooltip: vi.fn(),
  Legend: vi.fn(),
  Filler: vi.fn(),
}));

// Mock react-chartjs-2
vi.mock('react-chartjs-2', () => ({
  Line: vi.fn(() => <div data-testid="line-chart" />),
  Bar: vi.fn(() => <div data-testid="bar-chart" />),
  Doughnut: vi.fn(() => <div data-testid="doughnut-chart" />),
  Pie: vi.fn(() => <div data-testid="pie-chart" />),
}));

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
  Toaster: vi.fn(() => <div data-testid="toaster" />),
}));

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useLocation: () => ({
      pathname: '/test',
      search: '',
      hash: '',
      state: null,
    }),
    useParams: () => ({}),
  };
});

// Mock API service
vi.mock('@/services/api', () => ({
  apiService: {
    auth: {
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn(),
      getCurrentUser: vi.fn(),
    },
    companies: {
      search: vi.fn(),
      getCompany: vi.fn(),
      getFinancialData: vi.fn(),
    },
    portfolio: {
      getPortfolios: vi.fn(),
      createPortfolio: vi.fn(),
      updatePortfolio: vi.fn(),
      deletePortfolio: vi.fn(),
    },
    watchlist: {
      getWatchlists: vi.fn(),
      createWatchlist: vi.fn(),
      updateWatchlist: vi.fn(),
      deleteWatchlist: vi.fn(),
    },
  },
}));

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
});

// Mock fetch
global.fetch = vi.fn();

// Mock environment variables
vi.mock('@/config/env', () => ({
  API_BASE_URL: 'http://localhost:8000',
  APP_NAME: 'Financial Analysis Platform',
  APP_VERSION: '1.0.0',
}));

// Setup and cleanup
beforeAll(() => {
  // Global test setup
});

afterEach(() => {
  // Clean up after each test
  cleanup();
  vi.clearAllMocks();
  localStorageMock.clear();
  sessionStorageMock.clear();
});

afterAll(() => {
  // Global test cleanup
});

// Custom render function for testing with providers
import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Custom render with providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialState?: any;
}

import { AuthProvider } from '@/contexts/AuthContext';

export const renderWithProviders = (
  ui: React.ReactElement,
  {
    ...renderOptions
  }: CustomRenderOptions = {}
) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );

  return {
    queryClient,
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  };
};

// Test utilities
export const createMockUser = () => ({
  id: '123e4567-e89b-12d3-a456-426614174000',
  email: 'test@example.com',
  firstName: 'Test',
  lastName: 'User',
  isActive: true,
  isVerified: true,
});

export const createMockCompany = () => ({
  id: '123e4567-e89b-12d3-a456-426614174001',
  symbol: 'AAPL',
  name: 'Apple Inc.',
  exchange: 'NASDAQ',
  sector: 'Technology',
  industry: 'Consumer Electronics',
  marketCap: 3000000000000,
  description: 'Apple Inc. designs, manufactures, and markets smartphones.',
});

export const createMockPortfolio = () => ({
  id: '123e4567-e89b-12d3-a456-426614174002',
  name: 'Test Portfolio',
  description: 'A test portfolio',
  totalValue: 100000,
  totalGainLoss: 5000,
  totalGainLossPercent: 5.0,
  positions: [],
});

export const createMockWatchlist = () => ({
  id: '123e4567-e89b-12d3-a456-426614174003',
  name: 'Test Watchlist',
  description: 'A test watchlist',
  items: [],
});

// Export everything for easy importing
export * from '@testing-library/react';
export * from '@testing-library/user-event';
export { vi } from 'vitest';