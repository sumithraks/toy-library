"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiFetch, setToken } from "./api-client";
import type { User } from "./types";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    const hasToken = typeof window !== "undefined" && window.localStorage.getItem("toy_library_token");
    if (!hasToken) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await apiFetch<User>("/auth/me/");
      setUser(me);
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, refresh, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
