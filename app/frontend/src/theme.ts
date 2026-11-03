import { useEffect, useState } from "react";

export type Theme = "light" | "dark";

const KEY = "kaelo-theme";

export function getTheme(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

export function setTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    // storage unavailable: the choice lasts for this page only
  }
}

export function initTheme() {
  let saved: string | null = null;
  try {
    saved = localStorage.getItem(KEY);
  } catch {
    saved = null;
  }
  document.documentElement.dataset.theme = saved === "dark" ? "dark" : "light";
}

// Re-renders the caller when the theme changes, for colours set in JS (maps).
export function useTheme(): Theme {
  const [theme, set] = useState<Theme>(getTheme());
  useEffect(() => {
    const obs = new MutationObserver(() => set(getTheme()));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);
  return theme;
}
