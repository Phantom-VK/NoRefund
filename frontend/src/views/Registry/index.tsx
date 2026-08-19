import { useEffect, useMemo, useState } from "react";
import { useApp } from "@/lib/appContext";
import { ModelCard } from "./ModelCard";
import { ProviderFilter } from "./ProviderFilter";

// Worst-case stagger completion: last card's 200ms delay + 260ms animation
// (see motion.css's .stagger). Comfortably clears it before we stop
// re-applying the entrance class.
const STAGGER_SETTLE_MS = 500;

export default function Registry() {
  const { models, settings, exchangeRates, activeView } = useApp();
  const [activeProvider, setActiveProvider] = useState("All");
  const [hasEnteredOnce, setHasEnteredOnce] = useState(false);

  // App.tsx mounts every view at startup (hidden, not unmounted), so a
  // plain "run once on mount" effect fires while Registry is still
  // display:none -- long before the user ever sees it, which silently
  // strips the stagger class before the entrance can play. Gate on this
  // view actually being the active one, and hold the class for the
  // animation's full duration once it is, not just until the next tick.
  useEffect(() => {
    if (activeView !== "registry" || hasEnteredOnce) return;
    const timer = setTimeout(() => setHasEnteredOnce(true), STAGGER_SETTLE_MS);
    return () => clearTimeout(timer);
  }, [activeView, hasEnteredOnce]);

  const providers = useMemo(
    () => Array.from(new Set(models.map((m) => m.provider))).sort(),
    [models],
  );
  const visible =
    activeProvider === "All" ? models : models.filter((m) => m.provider === activeProvider);

  return (
    <div className="flex flex-col gap-5 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <p className="type-body text-muted-foreground">
          {models.length} models across {providers.length} providers. Locally stored
          pricing data.
        </p>
        <ProviderFilter
          providers={providers}
          active={activeProvider}
          onChange={setActiveProvider}
        />
      </div>

      <div
        className={
          hasEnteredOnce
            ? "grid grid-cols-[repeat(auto-fill,minmax(340px,1fr))] gap-3"
            : "stagger grid grid-cols-[repeat(auto-fill,minmax(340px,1fr))] gap-3"
        }
      >
        {visible.map((model) => (
          <ModelCard
            key={model.id}
            model={model}
            currency={settings.currency}
            rates={exchangeRates}
          />
        ))}
      </div>
    </div>
  );
}
