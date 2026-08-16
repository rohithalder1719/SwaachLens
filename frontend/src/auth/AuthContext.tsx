import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";

import { storage } from "@/src/utils/storage";

WebBrowser.maybeCompleteAuthSession();

const API = `${process.env.EXPO_PUBLIC_BACKEND_URL}/api`;
const TOKEN_KEY = "swachhlens_token";

export type Role = "citizen" | "staff";
export type User = { user_id: string; email: string; name: string; role: Role; picture?: string | null };

type AuthState = {
  user: User | null;
  loading: boolean;
  signup: (p: { email: string; password: string; name: string; role: Role; invite_code?: string }) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  claimStaff: (code: string) => Promise<void>;
  logout: () => Promise<void>;
  authFetch: (path: string, init?: RequestInit) => Promise<Response>;
};

const AuthContext = createContext<AuthState | null>(null);

let memoryToken: string | null = null;

async function exchangeSessionId(sessionId: string): Promise<{ token: string; user: User } | null> {
  const res = await fetch(`${API}/auth/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) return null;
  return res.json();
}

function extractSessionId(url: string | null): string | null {
  if (!url) return null;
  const match = url.match(/[?#&]session_id=([^&#]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const handledSessionIds = useRef<Set<string>>(new Set());

  const persistToken = useCallback(async (token: string) => {
    memoryToken = token;
    await storage.secureSet(TOKEN_KEY, token);
  }, []);

  const clearToken = useCallback(async () => {
    memoryToken = null;
    await storage.secureRemove(TOKEN_KEY);
  }, []);

  const authFetch = useCallback(async (path: string, init: RequestInit = {}) => {
    const token = memoryToken || (await storage.secureGet<string>(TOKEN_KEY, ""));
    const headers = { ...(init.headers || {}), Authorization: `Bearer ${token}` };
    return fetch(`${API}${path}`, { ...init, headers });
  }, []);

  const loadMe = useCallback(async () => {
    const token = memoryToken || (await storage.secureGet<string>(TOKEN_KEY, ""));
    if (!token) return null;
    memoryToken = token;
    const res = await fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) {
      await clearToken();
      return null;
    }
    const data = await res.json();
    return data.user as User;
  }, [clearToken]);

  const handleSessionId = useCallback(async (sessionId: string) => {
    if (handledSessionIds.current.has(sessionId)) return;
    handledSessionIds.current.add(sessionId);
    const result = await exchangeSessionId(sessionId);
    if (result) {
      await persistToken(result.token);
      setUser(result.user);
    }
  }, [persistToken]);

  useEffect(() => {
    (async () => {
      try {
        if (Platform.OS === "web" && typeof window !== "undefined") {
          const sid = extractSessionId(window.location.hash) || extractSessionId(window.location.search);
          if (sid) {
            await handleSessionId(sid);
            window.history.replaceState(window.history.state, "", window.location.pathname);
            return;
          }
        } else {
          const initial = await Linking.getInitialURL();
          const sid = extractSessionId(initial);
          if (sid) {
            await handleSessionId(sid);
            return;
          }
        }
        const me = await loadMe();
        if (me) setUser(me);
      } finally {
        setLoading(false);
      }
    })();

    const sub = Linking.addEventListener("url", ({ url }) => {
      const sid = extractSessionId(url);
      if (sid) handleSessionId(sid);
    });
    return () => sub.remove();
  }, [handleSessionId, loadMe]);

  const signup = useCallback(async (p: { email: string; password: string; name: string; role: Role; invite_code?: string }) => {
    const res = await fetch(`${API}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not create account");
    await persistToken(data.token);
    setUser(data.user);
  }, [persistToken]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Could not sign in");
    await persistToken(data.token);
    setUser(data.user);
  }, [persistToken]);

  const loginWithGoogle = useCallback(async () => {
    const redirectUrl = Platform.OS === "web" && typeof window !== "undefined"
      ? window.location.origin + "/"
      : Linking.createURL("");
    const authUrl = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
    if (Platform.OS === "web" && typeof window !== "undefined") {
      window.location.href = authUrl;
      return;
    }
    const result = await WebBrowser.openAuthSessionAsync(authUrl, redirectUrl);
    let url: string | null = result.type === "success" ? result.url : null;
    if (!url) url = await Linking.getInitialURL();
    const sid = extractSessionId(url);
    if (sid) await handleSessionId(sid);
  }, [handleSessionId]);

  const claimStaff = useCallback(async (code: string) => {
    const res = await authFetch("/auth/claim-staff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ invite_code: code }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Invalid invite code");
    setUser(data.user);
  }, [authFetch]);

  const logout = useCallback(async () => {
    try { await authFetch("/auth/logout", { method: "POST" }); } catch { /* local cleanup below */ }
    await clearToken();
    setUser(null);
  }, [authFetch, clearToken]);

  return (
    <AuthContext.Provider value={{ user, loading, signup, login, loginWithGoogle, claimStaff, logout, authFetch }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
