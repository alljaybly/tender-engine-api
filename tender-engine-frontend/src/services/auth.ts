/**
 * Auth service — handles login, register, and current user retrieval.
 * Uses the api client which auto-injects JWT tokens.
 */
import api, { setToken, clearToken } from './api';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: number;
  email: string;
  full_name: string;
  plan: string;
  is_active: boolean;
  created_at: string | null;
}

/**
 * Login with email and password.
 * Stores JWT token in localStorage on success.
 *
 * NOTE: Endpoint paths must include /api prefix since the backend router
 * is mounted at /api (see api/main.py: app.include_router(api_router, prefix="/api"))
 */
export async function login(credentials: LoginRequest): Promise<TokenResponse> {
  const data = await api.post<TokenResponse>('/api/auth/login', credentials);
  setToken(data.access_token);
  return data;
}

/**
 * Register a new account.
 * Stores JWT token in localStorage on success (auto-login).
 */
export async function register(
  payload: RegisterRequest,
): Promise<TokenResponse> {
  const data = await api.post<TokenResponse>('/api/auth/register', payload);
  setToken(data.access_token);
  return data;
}

/**
 * Get the currently authenticated user's profile.
 * Requires a valid JWT token in localStorage.
 */
export async function getCurrentUser(): Promise<UserResponse> {
  return api.get<UserResponse>('/api/auth/me');
}

/**
 * Logout: clear token from localStorage.
 */
export function logout(): void {
  clearToken();
}