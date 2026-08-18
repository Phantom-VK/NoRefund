import { useCallback, useEffect, useState } from "react";

export type ThemeMode = "light" | "dark" | "system";

const STORAGE_KEY = "norefund.theme";

function systemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function resolve(mode: ThemeMode): "light" | "dark" {
  if (mode === "system") return systemPrefersDark() ? "dark" : "light";
  return mode;
}

// pywebview's private_mode disables localStorage entirely in WebKitGTK —
// accessing it there throws a ReferenceError, not a quota/security error, and
// synchronously during React's render phase that crash was invisible (no
// console output, blank window). Read/write are best-effort; Phase 03 wires
// this to the real Settings backend so this remains a soft fallback only.
function readStoredMode(): ThemeMode | null {
  try {
    return localStorage.getItem(STORAGE_KEY) as ThemeMode | null;
  } catch {
    return null;
  }
}

function writeStoredMode(mode: ThemeMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    // Storage unavailable (private mode, disabled cookies, etc.) — the
    // in-memory state set alongside this call is still correct for the
    // current session, it just won't survive a restart.
  }
}

export function useTheme() {
  const [mode, setModeState] = useState<ThemeMode>(
    () => readStoredMode() ?? "system",
  );
  const [resolved, setResolved] = useState<"light" | "dark">(() => resolve(mode));

  useEffect(() => {
    const apply = () => {
      const next = resolve(mode);
      setResolved(next);
      document.documentElement.classList.toggle("dark", next === "dark");
    };
    apply();
    if (mode !== "system") return;
    // Only track the OS while following it.
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [mode]);

  const setMode = useCallback((next: ThemeMode) => {
    writeStoredMode(next);
    setModeState(next);
  }, []);

  return { mode, resolved, setMode };
}
