import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_verified: boolean;
  mfa_enabled: boolean;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: CurrentUser | null;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: CurrentUser) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setTokens: (access, refresh) => set({ accessToken: access, refreshToken: refresh }),
      setUser: (user) => set({ user }),
      logout: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    { name: "erp-auth-storage" }
  )
);
