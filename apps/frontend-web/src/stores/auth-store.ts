/**
 * Authentication store for web UI
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { getAuthToken, setAuthToken, clearAuthToken } from '../lib/auth';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (token: string) => Promise<boolean>;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (token: string) => {
        set({ isLoading: true, error: null });

        try {
          // Validate token by making a test request
          const response = await fetch('/api/health', {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });

          if (response.ok) {
            setAuthToken(token);
            set({ isAuthenticated: true, isLoading: false });
            return true;
          } else {
            set({ error: 'Invalid token', isLoading: false });
            return false;
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Login failed',
            isLoading: false,
          });
          return false;
        }
      },

      logout: () => {
        clearAuthToken();
        set({ isAuthenticated: false, error: null });
      },

      checkAuth: async () => {
        const token = getAuthToken();
        if (!token) {
          set({ isAuthenticated: false });
          return false;
        }

        set({ isLoading: true });

        try {
          const response = await fetch('/api/health', {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });

          if (response.ok) {
            set({ isAuthenticated: true, isLoading: false });
            return true;
          }

          // Only clear token on explicit auth failures (401/403)
          // Keep token on other errors (server issues, etc.)
          if (response.status === 401 || response.status === 403) {
            clearAuthToken();
            set({ isAuthenticated: false, isLoading: false });
          } else {
            // Server error but token might still be valid - keep it
            // User can try again when server is back
            set({ isAuthenticated: false, isLoading: false });
          }

          return false;
        } catch {
          // Network error - don't clear token, backend might just be starting up
          // Keep token so user doesn't have to re-enter it
          set({ isAuthenticated: false, isLoading: false });
          return false;
        }
      },
    }),
    {
      name: 'auto-claude-auth',
      partialize: (state) => ({
        // Don't persist isAuthenticated - always re-check on load
      }),
    }
  )
);
