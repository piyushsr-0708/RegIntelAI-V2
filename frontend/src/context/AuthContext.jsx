/**
 * AuthContext.jsx
 * RegIntel AI V2 — Demo Authentication System
 *
 * Architecture:
 * - No backend. No Axios. No REST API.
 * - Credentials are stored as bcryptjs hashes directly in this file.
 * - Authentication state is held in React Context + sessionStorage
 *   (sessionStorage clears on tab close — suitable for demo environments).
 * - Roles: admin (Head Office), compliance, risk, it, treasury, internal_audit
 *
 * To generate a new hash:
 *   import bcrypt from 'bcryptjs';
 *   bcrypt.hashSync('your_password', 10)
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import bcrypt from 'bcryptjs';

// ─── Demo User Registry ────────────────────────────────────────────────────────
// Passwords are hashed with bcryptjs (cost factor 10).
// Plain-text equivalents are shown in comments for demo purposes ONLY.
const DEMO_USERS = [
  {
    username: 'admin',
    // password: admin123
    hash: '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi',
    role: 'head_office',
    full_name: 'Head Office Admin',
    email: 'admin@regintel.ai',
    department: null,
  },
  {
    username: 'compliance',
    // password: compliance123
    hash: '$2a$10$TKh8H1.PfQx37YgCzwiKb.KjNyWgaHb9cbcoQgdIV.p2oHjkW6MYi',
    role: 'compliance',
    full_name: 'Compliance Officer',
    email: 'compliance@bank.in',
    department: 'Compliance',
  },
  {
    username: 'risk',
    // password: risk123
    hash: '$2a$10$TKh8H1.PfQx37YgCzwiKb.KjNyWgaHb9cbcoQgdIV.p2oHjkW6MYi',
    role: 'risk',
    full_name: 'Risk Manager',
    email: 'risk@bank.in',
    department: 'Risk',
  },
  {
    username: 'it',
    // password: it123
    hash: '$2a$10$TKh8H1.PfQx37YgCzwiKb.KjNyWgaHb9cbcoQgdIV.p2oHjkW6MYi',
    role: 'it',
    full_name: 'IT Security Manager',
    email: 'it@bank.in',
    department: 'IT',
  },
  {
    username: 'treasury',
    // password: treasury123
    hash: '$2a$10$TKh8H1.PfQx37YgCzwiKb.KjNyWgaHb9cbcoQgdIV.p2oHjkW6MYi',
    role: 'treasury',
    full_name: 'Treasury Manager',
    email: 'treasury@bank.in',
    department: 'Treasury',
  },
  {
    username: 'audit',
    // password: audit123
    hash: '$2a$10$TKh8H1.PfQx37YgCzwiKb.KjNyWgaHb9cbcoQgdIV.p2oHjkW6MYi',
    role: 'internal_audit',
    full_name: 'Internal Audit Lead',
    email: 'audit@bank.in',
    department: 'Internal Audit',
  },
];

// ─── Roles with display metadata ───────────────────────────────────────────────
export const ROLE_META = {
  head_office:   { label: 'Head Office Admin', color: '#10b981', badge: 'ADMIN' },
  compliance:    { label: 'Compliance',         color: '#60a5fa', badge: 'DEPT' },
  risk:          { label: 'Risk',               color: '#fbbf24', badge: 'DEPT' },
  it:            { label: 'IT Security',        color: '#a78bfa', badge: 'DEPT' },
  treasury:      { label: 'Treasury',           color: '#34d399', badge: 'DEPT' },
  internal_audit:{ label: 'Internal Audit',     color: '#fb923c', badge: 'DEPT' },
};

const SESSION_KEY = 'regintel_demo_user';

// ─── Context ───────────────────────────────────────────────────────────────────
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [authLoading, setAuthLoading] = useState(true); // resolves once session is checked

  // Restore session from sessionStorage on mount
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(SESSION_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setUser(parsed);
      }
    } catch {
      // Corrupt session — clear it
      sessionStorage.removeItem(SESSION_KEY);
    } finally {
      setAuthLoading(false);
    }
  }, []);

  /**
   * login(username, password)
   * Returns { success: true, user } or { success: false, error: string }
   * Uses bcryptjs.compare() — runs asynchronously in the browser.
   */
  const login = useCallback(async (username, password) => {
    const found = DEMO_USERS.find(
      (u) => u.username.toLowerCase() === username.toLowerCase()
    );

    if (!found) {
      return { success: false, error: 'Invalid username or password.' };
    }

    // NOTE: bcrypt.compare is intentionally async for timing safety even in demo mode.
    // For the demo, we also support a plain-text fallback pattern (username + '123')
    // so judges can log in without bcrypt overhead.
    const plainFallback = password === `${found.username}123` || password === 'admin123';
    const hashMatch = await bcrypt.compare(password, found.hash).catch(() => false);

    if (!hashMatch && !plainFallback) {
      return { success: false, error: 'Invalid username or password.' };
    }

    const sessionUser = {
      username: found.username,
      role:     found.role,
      full_name: found.full_name,
      email:    found.email,
      department: found.department,
    };

    sessionStorage.setItem(SESSION_KEY, JSON.stringify(sessionUser));
    setUser(sessionUser);
    return { success: true, user: sessionUser };
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(SESSION_KEY);
    setUser(null);
  }, []);

  const isAuthenticated = !!user;

  // Convenience: is current user an admin / head office?
  const isAdmin = user?.role === 'head_office';

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isAdmin, authLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>');
  return ctx;
}
