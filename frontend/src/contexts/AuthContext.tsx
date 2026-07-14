/**
 * Authentication Context Provider
 */
import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { AuthContextType, AuthState, User, LoginRequest, RegisterRequest } from '@/types/auth';
import { apiService } from '@/services/api';
import toast from 'react-hot-toast';

// Initial state
const initialState: AuthState = {
  user: null,
  token: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
};

// Action types
type AuthAction =
  | { type: 'AUTH_START' }
  | { type: 'AUTH_SUCCESS'; payload: { user: User; token: string; refreshToken: string } }
  | { type: 'AUTH_FAILURE'; payload: string }
  | { type: 'AUTH_LOGOUT' }
  | { type: 'CLEAR_ERROR' }
  | { type: 'SET_LOADING'; payload: boolean };

// Reducer
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'AUTH_START':
      return {
        ...state,
        isLoading: true,
        error: null,
      };

    case 'AUTH_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        refreshToken: action.payload.refreshToken,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      };

    case 'AUTH_FAILURE':
      return {
        ...state,
        user: null,
        token: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: action.payload,
      };

    case 'AUTH_LOGOUT':
      return {
        ...state,
        user: null,
        token: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      };

    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };

    default:
      return state;
  }
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider component
interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Initialize authentication state
  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const refreshToken = localStorage.getItem('refresh_token');
      const userStr = localStorage.getItem('user');

      if (token && refreshToken && userStr) {
        const user = JSON.parse(userStr);
        
        // Verify token is still valid
        try {
          const currentUser = await apiService.getCurrentUser();
          dispatch({
            type: 'AUTH_SUCCESS',
            payload: { user: currentUser, token, refreshToken },
          });
        } catch (error) {
          // Token might be expired, try to refresh
          try {
            const authResponse = await apiService.refreshToken();
            dispatch({
              type: 'AUTH_SUCCESS',
              payload: {
                user: authResponse.user,
                token: authResponse.access_token,
                refreshToken: authResponse.refresh_token,
              },
            });
          } catch (refreshError) {
            // Refresh failed, clear tokens
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            dispatch({ type: 'AUTH_LOGOUT' });
          }
        }
      } else {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    } catch (error) {
      console.error('Auth initialization error:', error);
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const login = async (credentials: LoginRequest) => {
    try {
      dispatch({ type: 'AUTH_START' });
      
      const response = await apiService.login(credentials);
      
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: {
          user: response.user,
          token: response.access_token,
          refreshToken: response.refresh_token,
        },
      });

      toast.success(`Welcome back, ${response.user.name}!`);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Login failed. Please try again.';
      dispatch({ type: 'AUTH_FAILURE', payload: errorMessage });
      toast.error(errorMessage);
      throw error;
    }
  };

  const register = async (userData: RegisterRequest) => {
    try {
      dispatch({ type: 'AUTH_START' });
      
      const response = await apiService.register(userData);
      
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: {
          user: response.user,
          token: response.access_token,
          refreshToken: response.refresh_token,
        },
      });

      toast.success(`Welcome to RNR Financial Analysis Platform, ${response.user.name}!`);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Registration failed. Please try again.';
      dispatch({ type: 'AUTH_FAILURE', payload: errorMessage });
      toast.error(errorMessage);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await apiService.logout();
      dispatch({ type: 'AUTH_LOGOUT' });
      toast.success('Logged out successfully');
    } catch (error) {
      console.error('Logout error:', error);
      // Still logout locally even if API call fails
      dispatch({ type: 'AUTH_LOGOUT' });
    }
  };

  const refreshToken = async () => {
    try {
      const response = await apiService.refreshToken();
      
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: {
          user: response.user,
          token: response.access_token,
          refreshToken: response.refresh_token,
        },
      });
    } catch (error) {
      dispatch({ type: 'AUTH_LOGOUT' });
      throw error;
    }
  };

  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  const contextValue: AuthContextType = {
    user: state.user,
    token: state.token,
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    error: state.error,
    login,
    register,
    logout,
    refreshToken,
    clearError,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook to use auth context
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;