import { createContext, useContext } from "react";
import type { ModelInfo, Settings } from "./types";
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
}

export const AppContext = createContext<AppContextValue | null>(null);

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppContext.Provider");
  return ctx;
}
