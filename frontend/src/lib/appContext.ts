import { createContext, useContext } from "react";
import type { ExchangeRates, ModelInfo, Settings } from "./types";
import type { ViewId } from "./views";

export interface AppContextValue {
  models: ModelInfo[];
  settings: Settings;
  activeView: ViewId;
  goto: (v: ViewId) => void;
  lastAnalysisTokens: number | null;
  setLastAnalysisTokens: (n: number) => void;
  fileCount: number;
  setFileCount: (n: number) => void;
  /** Cached rates -- always available instantly, no network. */
  exchangeRates: ExchangeRates;
  /** The only place in the frontend that triggers a network fetch of fresh
   *  rates -- wired to Settings' "Refresh rates" action. Throws BridgeError
   *  on failure; callers show that inline rather than this swallowing it. */
  refreshExchangeRates: () => Promise<void>;
}

export const AppContext = createContext<AppContextValue | null>(null);

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppContext.Provider");
  return ctx;
}
