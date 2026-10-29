import { createContext, useContext, useEffect, useState } from "react";
import { api, clearToken, getToken, setToken } from "./api";

interface AuthState {
  email: string | null;
  loading: boolean;
  login: (e: string, p: string) => Promise<void>;
  register: (e: string, p: string) => Promise<void>;
  logout: () => void;
}

const AuthCtx = createContext<AuthState>(null as any);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [email, setEmail] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      if (!getToken()) { setLoading(false); return; }
      try {
        const me = await api.me();
        setEmail(me.email);
      } catch {
        clearToken();
      }
      setLoading(false);
    })();
  }, []);

  const login = async (e: string, p: string) => {
    const t = await api.login(e, p);
    setToken(t.access_token);
    const me = await api.me();
    setEmail(me.email);
  };
  const register = async (e: string, p: string) => {
    const t = await api.register(e, p);
    setToken(t.access_token);
    setEmail(e);
  };
  const logout = () => { clearToken(); setEmail(null); };

  return (
    <AuthCtx.Provider value={{ email, loading, login, register, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);