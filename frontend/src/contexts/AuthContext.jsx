import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { authApi, formatApiErrorDetail } from "../lib/api";

// undefined = checking, null = unauthenticated, object = user
const AuthContext = createContext({
  user: undefined,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
  refreshUser: async () => {},
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(undefined);

  const refreshUser = useCallback(async () => {
    try {
      const me = await authApi.me();
      setUser(me);
      return me;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (email, password) => {
    try {
      const me = await authApi.login({ email, password });
      setUser(me);
      return { ok: true, user: me };
    } catch (err) {
      return {
        ok: false,
        error: formatApiErrorDetail(err?.response?.data?.detail) || "Login failed",
      };
    }
  }, []);

  const register = useCallback(async (payload) => {
    try {
      const me = await authApi.register(payload);
      setUser(me);
      return { ok: true, user: me };
    } catch (err) {
      return {
        ok: false,
        error:
          formatApiErrorDetail(err?.response?.data?.detail) || "Registration failed",
      };
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      /* swallow */
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
