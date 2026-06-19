import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { authApi, formatApiErrorDetail, setAuthToken } from "../lib/api";

// undefined = checking, null = unauthenticated, object = user
const AuthContext = createContext({
  user: undefined,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
  refreshUser: async () => {},
});

const isUserPayload = (data) =>
  data && typeof data === "object" && data.email && data.id;

// Login / register endpoints return either { user, access_token } (new) or just a UserPublic (legacy).
const extractAuth = (data) => {
  if (!data) return { user: null, token: null };
  if (isUserPayload(data)) return { user: data, token: null }; // legacy shape
  if (data.user && isUserPayload(data.user))
    return { user: data.user, token: data.access_token || null };
  return { user: null, token: null };
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(undefined);

  const refreshUser = useCallback(async () => {
    try {
      const me = await authApi.me();
      setUser(me);
      return me;
    } catch {
      setUser(null);
      setAuthToken(null);
      return null;
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (email, password) => {
    try {
      const data = await authApi.login({ email, password });
      const { user: u, token } = extractAuth(data);
      if (token) setAuthToken(token);
      setUser(u);
      return { ok: true, user: u };
    } catch (err) {
      return {
        ok: false,
        error: formatApiErrorDetail(err?.response?.data?.detail) || "Login failed",
      };
    }
  }, []);

  const register = useCallback(async (payload) => {
    try {
      const data = await authApi.register(payload);
      const { user: u, token } = extractAuth(data);
      if (token) setAuthToken(token);
      setUser(u);
      return { ok: true, user: u };
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
    setAuthToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
