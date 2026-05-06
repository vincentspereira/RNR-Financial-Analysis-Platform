import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import * as SecureStore from 'expo-secure-store';
import { authApi } from '../services/api';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  useEffect(() => {
    restoreSession();
  }, []);

  async function restoreSession() {
    try {
      const token = await SecureStore.getItemAsync('auth_token');
      if (token) {
        const res = await authApi.me();
        setState({
          user: res.data,
          isLoading: false,
          isAuthenticated: true,
        });
        return;
      }
    } catch {
      await SecureStore.deleteItemAsync('auth_token');
    }
    setState({ user: null, isLoading: false, isAuthenticated: false });
  }

  async function login(email: string, password: string) {
    const res = await authApi.login(email, password);
    const { access_token, user } = res.data;
    await SecureStore.setItemAsync('auth_token', access_token);
    setState({ user, isLoading: false, isAuthenticated: true });
  }

  async function logout() {
    await SecureStore.deleteItemAsync('auth_token');
    setState({ user: null, isLoading: false, isAuthenticated: false });
  }

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
