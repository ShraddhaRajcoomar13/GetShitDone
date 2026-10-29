import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

export interface ThemeState {
  theme: string;
  accentColor: string;
  bgImage: string;
  bgOpacity: number;
}

const DEFAULT: ThemeState = { theme: "paper", accentColor: "", bgImage: "", bgOpacity: 60 };

export const THEMES = {
  paper:    { dark: false, label: "Paper",    vars: { paper: "253 251 246", ink: "31 27 20",  accent: "199 112 60",  accent2: "60 107 107" } },
  ocean:    { dark: false, label: "Ocean",    vars: { paper: "240 247 250", ink: "15 30 40",  accent: "40 100 160",  accent2: "60 140 160" } },
  rose:     { dark: false, label: "Rose",     vars: { paper: "253 244 244", ink: "40 20 25",  accent: "190 70 110",  accent2: "140 70 130" } },
  midnight: { dark: true,  label: "Midnight", vars: { paper: "15 15 25",   ink: "235 235 245", accent: "120 160 255", accent2: "80 200 200" } },
  forest:   { dark: true,  label: "Forest",   vars: { paper: "15 25 20",   ink: "235 245 235", accent: "110 200 130", accent2: "180 200 100" } },
  slate:    { dark: true,  label: "Slate",    vars: { paper: "25 27 32",   ink: "230 232 236", accent: "150 170 220", accent2: "120 180 170" } },
} as const;

export type ThemeName = keyof typeof THEMES;

const CACHE_KEY = "gsd_theme";

function readCache(): ThemeState {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (raw) return { ...DEFAULT, ...JSON.parse(raw) };
  } catch {}
  return DEFAULT;
}

function hexToRgb(hex: string): string | null {
  const m = hex.replace("#", "").match(/^([0-9a-f]{6})$/i);
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return `${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255}`;
}

const ThemeCtx = createContext<ThemeState & {
  setName: (n: string) => void;
  setAccent: (c: string) => void;
  setBgImage: (u: string) => void;
  setBgOpacity: (n: number) => void;
  themes: typeof THEMES;
}>(null as any);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { email } = useAuth();
  const [state, setState] = useState<ThemeState>(readCache);

  // Load from backend once logged in
  useEffect(() => {
    if (!email) return;
    (async () => {
      try {
        const p: any = await api.prefs();
        setState({
          theme: p.theme || "paper",
          accentColor: p.accent_color || "",
          bgImage: p.bg_image || "",
          bgOpacity: p.bg_opacity ?? 60,
        });
      } catch {}
    })();
  }, [email]);

  // Apply to DOM + cache
  useEffect(() => {
    const root = document.documentElement;
    const t: any = (THEMES as any)[state.theme] || THEMES.paper;

    root.classList.toggle("dark", t.dark);
    root.style.setProperty("--color-paper", t.vars.paper);
    root.style.setProperty("--color-ink", t.vars.ink);
    root.style.setProperty("--color-accent-2", t.vars.accent2);

    const custom = state.accentColor ? hexToRgb(state.accentColor) : null;
    root.style.setProperty("--color-accent", custom || t.vars.accent);

    if (state.bgImage) {
      root.style.setProperty("--bg-image", `url("${state.bgImage.replace(/"/g, '\\"')}")`);
      root.style.setProperty("--bg-opacity", String(state.bgOpacity / 100));
    } else {
      root.style.setProperty("--bg-image", "none");
      root.style.setProperty("--bg-opacity", "0");
    }

    try { localStorage.setItem(CACHE_KEY, JSON.stringify(state)); } catch {}
  }, [state]);

  const persist = async (patch: Partial<ThemeState>) => {
    const next = { ...state, ...patch };
    setState(next);
    try {
      await api.updatePrefs({
        theme: next.theme,
        accent_color: next.accentColor,
        bg_image: next.bgImage,
        bg_opacity: next.bgOpacity,
      } as any);
    } catch {}
  };

  return (
    <ThemeCtx.Provider value={{
      ...state,
      setName: (n) => persist({ theme: n }),
      setAccent: (c) => persist({ accentColor: c }),
      setBgImage: (u) => persist({ bgImage: u }),
      setBgOpacity: (n) => persist({ bgOpacity: n }),
      themes: THEMES,
    }}>
      {children}
    </ThemeCtx.Provider>
  );
}

export const useTheme = () => useContext(ThemeCtx);