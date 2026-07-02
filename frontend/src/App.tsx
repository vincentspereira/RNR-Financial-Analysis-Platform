/**
 * Main App Component with Code Splitting and Lazy Loading
 */
import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from '@/contexts/AuthContext';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { LoginForm } from '@/components/auth/LoginForm';
import { RegisterForm } from '@/components/auth/RegisterForm';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';

// Lazy load components for better performance
const Dashboard = React.lazy(() => import('@/pages/Dashboard').then(module => ({ default: module.Dashboard })));
const Analysis = React.lazy(() => import('@/pages/Analysis').then(module => ({ default: module.Analysis })));
const PortfolioPage = React.lazy(() => import('@/pages/Portfolio').then(module => ({ default: module.PortfolioPage })));
const WatchlistPage = React.lazy(() => import('@/pages/Watchlist').then(module => ({ default: module.WatchlistPage })));
const AnalyticsPage = React.lazy(() => import('@/pages/Analytics').then(module => ({ default: module.AnalyticsPage })));
const DataManagement = React.lazy(() => import('@/pages/DataManagement').then(module => ({ default: module.DataManagement })));

// Phase 5 pages
const RiskDashboard = React.lazy(() => import('@/pages/RiskDashboard').then(module => ({ default: module.RiskDashboard })));
const NotificationsPage = React.lazy(() => import('@/pages/Notifications').then(module => ({ default: module.Notifications })));
const PaperTradingPage = React.lazy(() => import('@/pages/PaperTrading').then(module => ({ default: module.PaperTrading })));
const StockScreenerPage = React.lazy(() => import('@/pages/StockScreener').then(module => ({ default: module.StockScreener })));
const AdminPage = React.lazy(() => import('@/pages/Admin').then(module => ({ default: module.Admin })));

// Phase 6: IBKR
const IBKRPage = React.lazy(() => import('@/pages/IBKR').then(module => ({ default: module.IBKR })));

// Placeholder components for future implementation
const SettingsPage = React.lazy(() => 
  Promise.resolve({
    default: () => (
      <div className="text-center py-12">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-2 text-gray-600">Coming soon - Account and application settings</p>
      </div>
    )
  })
);

// Loading component for Suspense fallback
const PageLoader = () => (
  <div className="flex items-center justify-center min-h-screen">
    <LoadingSpinner size="large" />
  </div>
);

// Route-specific loading components for better UX
const DashboardLoader = () => (
  <div className="p-6">
    <div className="animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-32 bg-gray-200 rounded"></div>
        ))}
      </div>
      <div className="h-64 bg-gray-200 rounded"></div>
    </div>
  </div>
);

const AnalysisLoader = () => (
  <div className="p-6">
    <div className="animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
      <div className="h-12 bg-gray-200 rounded mb-6"></div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="h-96 bg-gray-200 rounded"></div>
        <div className="h-96 bg-gray-200 rounded"></div>
      </div>
    </div>
  </div>
);

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Router>
          <div className="min-h-screen bg-gray-50">
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<LoginForm />} />
              <Route path="/register" element={<RegisterForm />} />
              
              {/* Protected routes with lazy loading */}
              <Route path="/" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                
                <Route 
                  path="dashboard" 
                  element={
                    <Suspense fallback={<DashboardLoader />}>
                      <Dashboard />
                    </Suspense>
                  } 
                />
                
                <Route 
                  path="analysis" 
                  element={
                    <Suspense fallback={<AnalysisLoader />}>
                      <Analysis />
                    </Suspense>
                  } 
                />
                
                <Route 
                  path="portfolio" 
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <PortfolioPage />
                    </Suspense>
                  } 
                />
                
                <Route 
                  path="watchlist" 
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <WatchlistPage />
                    </Suspense>
                  } 
                />
                
                <Route 
                  path="analytics" 
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <AnalyticsPage />
                    </Suspense>
                  } 
                />
                
                <Route 
                  path="data" 
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <DataManagement />
                    </Suspense>
                  } 
                />
                
                <Route
                  path="settings"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <SettingsPage />
                    </Suspense>
                  }
                />

                {/* Phase 5 routes */}
                <Route
                  path="risk"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <RiskDashboard />
                    </Suspense>
                  }
                />

                <Route
                  path="notifications"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <NotificationsPage />
                    </Suspense>
                  }
                />

                <Route
                  path="paper-trading"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <PaperTradingPage />
                    </Suspense>
                  }
                />

                <Route
                  path="ibkr"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <IBKRPage />
                    </Suspense>
                  }
                />

                <Route
                  path="screener"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <StockScreenerPage />
                    </Suspense>
                  }
                />

                <Route
                  path="admin"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <AdminPage />
                    </Suspense>
                  }
                />
              </Route>
              
              {/* Catch all route */}
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
            
            {/* Global toast notifications */}
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: '#363636',
                  color: '#fff',
                },
                success: {
                  duration: 3000,
                  iconTheme: {
                    primary: '#10B981',
                    secondary: '#fff',
                  },
                },
                error: {
                  duration: 5000,
                  iconTheme: {
                    primary: '#EF4444',
                    secondary: '#fff',
                  },
                },
              }}
            />
          </div>
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;