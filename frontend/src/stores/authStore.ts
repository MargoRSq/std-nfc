import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

interface User {
  id: string;
  email: string;
  role: string;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: User | null) => void;
  setAuth: (token: string, user: User | null) => void;
  logout: () => void;
}

const STORAGE_KEY = "std-cards-auth";

// "Запомнить меня" — persist to localStorage when on, sessionStorage when off.
// Default to whatever already holds a session so a plain refresh keeps the user logged in.
let useSessionStorage =
  typeof window !== "undefined" &&
  window.sessionStorage.getItem(STORAGE_KEY) !== null &&
  window.localStorage.getItem(STORAGE_KEY) === null;

export function setRememberMe(remember: boolean): void {
  useSessionStorage = !remember;
}

const rememberAwareStorage = {
  getItem: (name: string) =>
    window.sessionStorage.getItem(name) ?? window.localStorage.getItem(name),
  setItem: (name: string, value: string) => {
    if (useSessionStorage) {
      window.sessionStorage.setItem(name, value);
      window.localStorage.removeItem(name);
    } else {
      window.localStorage.setItem(name, value);
      window.sessionStorage.removeItem(name);
    }
  },
  removeItem: (name: string) => {
    window.localStorage.removeItem(name);
    window.sessionStorage.removeItem(name);
  },
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      setUser: (user) => set({ user }),
      setAuth: (accessToken, user) => set({ accessToken, user }),
      logout: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    { name: STORAGE_KEY, storage: createJSONStorage(() => rememberAwareStorage) },
  ),
);
