/**
 * AuthContext.jsx
 * RegIntel AI V2 — Live Authentication System
 * Uses offline JWT tokens provided by FastAPI backend.
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiFetch } from '../utils/api';

const SESSION_KEY = 'regintel_jwt';

export const ROLE_META = {
  'Super Admin':     { label: 'Super Admin',     color: '#10b981', badge: 'ADMIN' },
  'Admin':           { label: 'Head Office Admin',color: '#10b981', badge: 'ADMIN' },
  'Compliance Head': { label: 'Compliance',       color: '#60a5fa', badge: 'DEPT' },
  'Risk Head':       { label: 'Risk',             color: '#fbbf24', badge: 'DEPT' },
  'IT Head':         { label: 'IT Security',      color: '#a78bfa', badge: 'DEPT' },
  'Audit Head':      { label: 'Internal Audit',   color: '#fb923c', badge: 'DEPT' },
  'Operations Head': { label: 'Operations',       color: '#34d399', badge: 'DEPT' },
  'Viewer':          { label: 'Viewer',           color: '#94a3b8', badge: 'GUEST' },
};

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // Restore session from backend on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = sessionStorage.getItem(SESSION_KEY);
      if (token) {
        try {
          const userData = await apiFetch('/auth/me');
          setUser(userData);
        } catch (err) {
          console.warn('Session invalid, clearing...', err);
          sessionStorage.removeItem(SESSION_KEY);
        }
      }
      setAuthLoading(false);
    };
    initAuth();
  }, []);

  const login = useCallback(async (username, password) => {
    try {
      const res = await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      sessionStorage.setItem(SESSION_KEY, res.access_token);
      
      const userData = await apiFetch('/auth/me');
      setUser(userData);
      return { success: true, user: userData };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(SESSION_KEY);
    setUser(null);
  }, []);

  const isAuthenticated = !!user;
  
  // Permission helper
  const can = useCallback((permission) => {
    if (!user || !user.permissions) return false;
    return user.permissions.includes('*') || user.permissions.includes(permission);
  }, [user]);

  // Legacy convenience getters mapping to actual permissions/roles
  const isAdmin = can('*') || can('user:write');

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isAdmin, authLoading, login, logout, can }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>');
  return ctx;
}
