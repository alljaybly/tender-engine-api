export interface User {
  id: number;
  email: string;
  full_name: string;
  plan: string;
  is_active: boolean;
  created_at: string | null;
}

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}