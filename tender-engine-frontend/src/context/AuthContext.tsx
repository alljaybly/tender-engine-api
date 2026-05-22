import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from 'react';
import type { AuthContextType, User } from '../types/auth';
import * as authService from '../services/auth';
import { clearToken, getStoredToken, isTokenExpired, ApiRequestError } from '../services/api';

const AuthContext = createContext<AuthContextType | null>(null);

/**
 * Maximum number of retries for auth restoration on mount.
 * Handles Render cold starts where the backend can take 35-40s to wake up.
 * With 4 retries and exponential backoff, we wait approximately:
 *   3s + 6s + 12s + 24s = ~45s before giving up — enough for a cold start.
 */
const MAX_AUTH_RETRIES = 4;

/**
 * Base delay in ms between auth restoration retries.
 * Actual delay = BASE_RETRY_DELAY * (2 ^ attempt) — exponential backoff.
 * Sequence:  3s, 6s, 12s, 24s
 */
const BASE_RETRY_DELAY = 3000;

/**
 * Wait this long before the first auth/me call after detecting a valid stored token.
 * This gives the Render backend a head start to wake up before we even try.
 */
const INITIAL_DEFER_MS = 3000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const mountedRef = useRef(true);

  // ── Restore auth state on mount (page refresh) ───────────────────
  // Handles Render cold start gracefully: retries /auth/me with
  // exponential backoff before concluding the token is invalid.
  useEffect(() => {
    mountedRef.current = true;

    async function restoreAuth() {
      const token = getStoredToken();

      // No token stored — not authenticated
      if (!token) {
        setIsLoading(false);
        return;
      }

      // Preemptively check token expiry before making a server call.
      if (isTokenExpired(token)) {
        console.log('[AuthContext] Stored token is expired — clearing session');
        clearToken();
        setIsLoading(false);
        return;
      }

      // ── Token exists and is not expired — verify with backend ──
      // We use retry logic to handle Render cold starts gracefully.
      // The backend may take 15-30s to wake up on first request.
      // Instead of immediately clearing the token on failure, we
      // retry up to MAX_AUTH_RETRIES times with exponential backoff.
      for (let attempt = 0; attempt <= MAX_AUTH_RETRIES; attempt++) {
        if (!mountedRef.current) return;

        try {
          // On first attempt, add a short initial defer to give Render
          // a head start on waking up before we even make the request.
          if (attempt === 0) {
            await new Promise((r) => setTimeout(r, INITIAL_DEFER_MS));
            if (!mountedRef.current) return;
          }

          const userData = await authService.getCurrentUser();
          
          if (mountedRef.current) {
            setUser(userData);
            setIsLoading(false);
          }
          return; // Success — exit retry loop
        } catch (err) {
          const isNetworkError =
            err instanceof ApiRequestError &&
            (err.status === 0 || err.code === 'network_error');
          
          const isServerError =
            err instanceof ApiRequestError && err.status >= 500;
          
          const isAuthError =
            err instanceof ApiRequestError && err.status === 401;

          // If it's a confirmed auth error (401), clear immediately
          if (isAuthError) {
            console.log('[AuthContext] Stored token rejected by backend — clearing session');
            if (mountedRef.current) {
              clearToken();
              setUser(null);
              setIsLoading(false);
            }
            return;
          }

          // For network errors (cold start) or server errors, retry
          if ((isNetworkError || isServerError) && attempt < MAX_AUTH_RETRIES) {
            const delay = BASE_RETRY_DELAY * (2 ** attempt);
            console.log(
              `[AuthContext] Auth restoration attempt ${attempt + 1}/${MAX_AUTH_RETRIES} failed ` +
              `(status=${err instanceof ApiRequestError ? err.status : 'unknown'}) — ` +
              `retrying in ${delay}ms`,
            );
            await new Promise((r) => setTimeout(r, delay));
            continue;
          }

          // Non-retryable error, or max retries exhausted — clear token
          console.log('[AuthContext] Auth restoration failed after retries — clearing session');
          if (mountedRef.current) {
            clearToken();
            setUser(null);
            setIsLoading(false);
          }
          return;
        }
      }

      // Should not reach here, but safety net
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }

    restoreAuth();

    return () => {
      mountedRef.current = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await authService.login({ email, password });
    const userData = await authService.getCurrentUser();
    setUser(userData);
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      await authService.register({ email, password, full_name: fullName });
      const userData = await authService.getCurrentUser();
      setUser(userData);
    },
    [],
  );

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  const value: AuthContextType = {
    user,
    isAuthenticated: user !== null,
    isLoading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;