import { useEffect, useMemo, useState, type ComponentType } from "react";
import { Header } from "@/components/app/Header";
import { Sidebar } from "@/components/app/Sidebar";
import { SettingsModal } from "@/components/app/SettingsModal";
import { NoticeBanner } from "@/components/app/NoticeBanner";
import { Spinner } from "@/components/app/Spinner";
import { AppContext, type AppContextValue } from "@/lib/appContext";
import { VIEWS, type ViewId } from "@/lib/views";
import { useSettings } from "@/hooks/useSettings";
import { useShortcuts } from "@/hooks/useShortcuts";
import { useJob } from "@/hooks/useJob";
import { useTheme, type ThemeMode } from "@/hooks/useTheme";
import { bridge, bridgeReady, BridgeError } from "@/lib/bridge";
import type { ModelInfo, ResourceReport } from "@/lib/types";

import Calculator from "@/views/Calculator";
import Parser from "@/views/Parser";
import Compare from "@/views/Compare";
import FitCheck from "@/views/FitCheck";
import Registry from "@/views/Registry";
import Resources from "@/views/Resources";

const VIEW_COMPONENTS: Record<ViewId, ComponentType> = {
  calculator: Calculator,
  parser: Parser,
  compare: Compare,
  fit_check: FitCheck,
  registry: Registry,
  resources: Resources,
};

const THEME_ORDER: ThemeMode[] = ["light", "dark", "system"];

export default function App() {
  const [bridgeErr, setBridgeErr] = useState<string | null>(null);
  const [models, setModels] = useState<ModelInfo[] | null>(null);
  const [activeView, setActiveView] = useState<ViewId>("calculator");
  const [lastAnalysisTokens, setLastAnalysisTokens] = useState<number | null>(null);
  const [fileCount, setFileCount] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [noticeDismissed, setNoticeDismissed] = useState(false);

  const { settings, save: saveSettings } = useSettings();
  const { mode, setMode } = useTheme();
  const onboardingScan = useJob<never, ResourceReport>();

  useEffect(() => {
    let cancelled = false;
    bridgeReady()
      .then(() => bridge.getModels())
      .then((m) => {
        if (!cancelled) setModels(m);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setBridgeErr(err instanceof BridgeError ? err.message : String(err));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // The backend Settings file is the source of truth for theme (it survives
  // a restart even where localStorage doesn't -- see useTheme.ts); once it
  // loads, reconcile the live theme to it.
  useEffect(() => {
    if (settings && settings.theme !== mode) {
      setMode(settings.theme);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings]);

  useEffect(() => {
    if (!settings || settings.onboarding_dismissed) return;
    void onboardingScan.start(() => bridge.startResourceScan());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings]);

  const showOnboardingNotice =
    !noticeDismissed &&
    !!onboardingScan.result &&
    !onboardingScan.result.tokenizers.some((t) => t.is_cached);

  function dismissNotice() {
    setNoticeDismissed(true);
    void saveSettings({ onboarding_dismissed: true });
  }

  function cycleTheme() {
    const next = THEME_ORDER[(THEME_ORDER.indexOf(mode) + 1) % THEME_ORDER.length];
    setMode(next);
    void saveSettings({ theme: next });
  }

  useShortcuts({
    onView: setActiveView,
    onEscape: () => {
      if (onboardingScan.running) onboardingScan.cancel();
    },
  });

  const ctxValue = useMemo<AppContextValue | null>(() => {
    if (!settings || !models) return null;
    return {
      models,
      settings,
      activeView,
      goto: setActiveView,
      lastAnalysisTokens,
      setLastAnalysisTokens,
      fileCount,
      setFileCount,
    };
  }, [models, settings, activeView, lastAnalysisTokens, fileCount]);

  if (bridgeErr) {
    return (
      <div className="flex h-full items-center justify-center bg-background p-6 text-center">
        <p className="type-body text-destructive">{bridgeErr}</p>
      </div>
    );
  }

  if (!ctxValue) {
    // Themed background, never a white flash -- create_app_window already
    // sets background_color to match this for the same reason.
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <Spinner size={32} />
      </div>
    );
  }

  const activeTitle = VIEWS.find((v) => v.id === activeView)?.title ?? "";

  return (
    <AppContext.Provider value={ctxValue}>
      <div className="flex h-full">
        <Sidebar activeView={activeView} onNavigate={setActiveView} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Header
            title={activeTitle}
            fileCount={activeView === "parser" ? fileCount : 0}
            themeMode={mode}
            onToggleTheme={cycleTheme}
            onOpenSettings={() => setSettingsOpen(true)}
          />
          {showOnboardingNotice && (
            <NoticeBanner
              message="No tokenizers downloaded yet — counts will be rough approximations."
              actionLabel="Open Resources"
              onAction={() => {
                setActiveView("resources");
                setNoticeDismissed(true);
              }}
              onDismiss={dismissNotice}
            />
          )}
          <div className="relative min-h-0 flex-1">
            {VIEWS.map((v) => {
              const ViewComponent = VIEW_COMPONENTS[v.id];
              return (
                <div
                  key={v.id}
                  hidden={activeView !== v.id}
                  className="absolute inset-0 overflow-y-auto"
                >
                  <ViewComponent />
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <SettingsModal
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        settings={ctxValue.settings}
        onSave={saveSettings}
      />
    </AppContext.Provider>
  );
}
