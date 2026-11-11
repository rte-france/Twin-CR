/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createContext,
  useContext,
  createSignal,
  createEffect,
  onCleanup,
  type ParentComponent,
} from "solid-js";
import { isServer } from "solid-js/web";

type Theme = "light" | "dark" | "one-dark" | "isa-101" | "system";

interface ThemeContextType {
  theme: () => Theme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType>();

interface ThemeProviderProps {
  syncId: string;
}

export const ThemeProvider: ParentComponent<ThemeProviderProps> = (props) => {
  const STORAGE_KEY = `theme-${props.syncId}`;

  const [theme, setThemeState] = createSignal<Theme>(
    (!isServer && (localStorage.getItem(STORAGE_KEY) as Theme)) || "system",
  );

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    if (!isServer) {
      localStorage.setItem(STORAGE_KEY, newTheme);
    }
  };

  createEffect(() => {
    if (isServer) return;

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY && e.newValue) {
        setThemeState(e.newValue as Theme);
      }
    };

    window.addEventListener("storage", handleStorageChange);
    onCleanup(() => window.removeEventListener("storage", handleStorageChange));
  });

  createEffect(() => {
    if (isServer) return;
    const currentTheme = theme();

    const isSystemDark = window.matchMedia(
      "(prefers-color-scheme: dark)",
    ).matches;
    const effectiveIsDark =
      currentTheme === "dark" || (currentTheme === "system" && isSystemDark);

    document.documentElement.classList.remove("dark", "one-dark", "isa-101");

    if (currentTheme === "one-dark") {
      document.documentElement.classList.add("one-dark");
    } else if (currentTheme === "isa-101") {
      document.documentElement.classList.add("isa-101");
    } else if (effectiveIsDark) {
      document.documentElement.classList.add("dark");
    }
  });

  createEffect(() => {
    if (isServer) return;
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const handleChange = (e: MediaQueryListEvent) => {
      if (theme() === "system") {
        if (e.matches) {
          document.documentElement.classList.add("dark");
        } else {
          document.documentElement.classList.remove("dark");
        }
      }
    };

    mediaQuery.addEventListener("change", handleChange);
    onCleanup(() => mediaQuery.removeEventListener("change", handleChange));
  });

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {props.children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context)
    throw new Error("useTheme doit être utilisé dans un ThemeProvider");
  return context;
};
