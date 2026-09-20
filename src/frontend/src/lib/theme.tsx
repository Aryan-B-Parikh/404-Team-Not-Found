import React, { createContext, useContext, useEffect, useState } from "react";

export type Theme = "dark" | "light";
export type ThemeMode = "dark" | "light" | "system";

interface ThemeContextType {
  theme: Theme;
  themeMode: ThemeMode;
  setTheme: (theme: Theme) => void;
  setThemeMode: (mode: ThemeMode) => void;
  toggleTheme: () => void;
  cycleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const STORAGE_KEY = "portflow_theme_mode";

function getSystemTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") return "dark";
    const saved = localStorage.getItem(STORAGE_KEY) as ThemeMode | null;
    if (saved === "dark" || saved === "light" || saved === "system") return saved;
    return "dark";
  });

  const [systemTheme, setSystemTheme] = useState<Theme>(getSystemTheme);

  const resolvedTheme: Theme = themeMode === "system" ? systemTheme : themeMode;

  const applyTheme = (t: Theme) => {
    const root = document.documentElement;
    root.setAttribute("data-theme", t);
    if (t === "dark") {
      root.classList.add("dark");
      root.classList.remove("light");
    } else {
      root.classList.add("light");
      root.classList.remove("dark");
    }
  };

  useEffect(() => {
    applyTheme(resolvedTheme);
    try {
      localStorage.setItem(STORAGE_KEY, themeMode);
    } catch {
      // ignore storage errors
    }
  }, [resolvedTheme, themeMode]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: light)");
    const handler = (e: MediaQueryListEvent) => {
      setSystemTheme(e.matches ? "light" : "dark");
    };
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  const setTheme = (newTheme: Theme) => {
    setThemeModeState(newTheme);
  };

  const setThemeMode = (mode: ThemeMode) => {
    setThemeModeState(mode);
  };

  const toggleTheme = () => {
    setThemeModeState((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const cycleTheme = () => {
    setThemeModeState((prev) => {
      if (prev === "dark") return "light";
      if (prev === "light") return "system";
      return "dark";
    });
  };

  return (
    <ThemeContext.Provider
      value={{
        theme: resolvedTheme,
        themeMode,
        setTheme,
        setThemeMode,
        toggleTheme,
        cycleTheme,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
