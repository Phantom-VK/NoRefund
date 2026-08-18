import { useCallback, useEffect, useState } from "react";
import { bridge, BridgeError } from "@/lib/bridge";
import type { Settings } from "@/lib/types";

export interface SettingsState {
  settings: Settings | null;
  save: (patch: Partial<Settings>) => Promise<void>;
  error: string | null;
}

export function useSettings(): SettingsState {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    bridge
      .getSettings()
      .then((s) => {
        if (!cancelled) setSettings(s);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof BridgeError ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const save = useCallback(
    async (patch: Partial<Settings>) => {
      if (!settings) return;
      const next = { ...settings, ...patch };
      setSettings(next);
      try {
        const saved = await bridge.saveSettings(next);
        setSettings(saved);
        setError(null);
      } catch (err) {
        setError(err instanceof BridgeError ? err.message : String(err));
      }
    },
    [settings],
  );

  return { settings, save, error };
}
