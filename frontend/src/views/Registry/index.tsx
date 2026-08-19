import { useEffect, useMemo, useState } from "react";
import { useApp } from "@/lib/appContext";
import { ModelCard } from "./ModelCard";
import { ProviderFilter } from "./ProviderFilter";

export default function Registry() {
  const { models } = useApp();
  const [activeProvider, setActiveProvider] = useState("All");
  const [hasMounted, setHasMounted] = useState(false);

  // Stagger only the entrance on first mount -- re-triggering it on every
  // filter click would turn a nice cascade into noise.
  useEffect(() => setHasMounted(true), []);

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
          {models.length} models across {providers.length} providers — locally stored
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
          hasMounted
            ? "grid grid-cols-[repeat(auto-fill,minmax(340px,1fr))] gap-3"
            : "stagger grid grid-cols-[repeat(auto-fill,minmax(340px,1fr))] gap-3"
        }
      >
        {visible.map((model) => (
          <ModelCard key={model.id} model={model} />
        ))}
      </div>
    </div>
  );
}
