import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

interface User {
  username: string;
  name: string;
  role: string;
}

interface AuthCtx {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx>({
  user: null,
  token: null,
  login: async () => {},
  logout: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

const API_BASE = (import.meta as any).env?.VITE_API_URL || "/api";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem("kaelo_token")
  );

  // On mount, verify stored token
  useEffect(() => {
    if (!token) return;
    fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error("expired");
        return r.json();
      })
      .then((data) =>
        setUser({ username: data.sub, name: data.name, role: data.role })
      )
      .catch(() => {
        localStorage.removeItem("kaelo_token");
        setToken(null);
        setUser(null);
      });
  }, [token]);

  const login = async (username: string, password: string) => {
    const r = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!r.ok) {
      const d = await r.json();
      throw new Error(d.detail || "Login failed");
    }
    const d = await r.json();
    localStorage.setItem("kaelo_token", d.token);
    setToken(d.token);
    setUser({
      username: d.user.username,
      name: d.user.full_name,
      role: d.user.role,
    });
  };

  const logout = () => {
    localStorage.removeItem("kaelo_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
