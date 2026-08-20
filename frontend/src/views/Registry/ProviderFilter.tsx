import { cn } from "@/lib/cn";

export interface ProviderFilterProps {
  providers: string[];
  active: string;
  onChange: (provider: string) => void;
}

export function ProviderFilter({ providers, active, onChange }: ProviderFilterProps) {
  return (
    <div
      role="group"
      aria-label="Filter by provider"
      className="flex flex-wrap gap-1.5"
    >
      {["All", ...providers].map((label) => {
        const isActive = label === active;
        return (
          <button
            key={label}
            type="button"
            onClick={() => onChange(label)}
            aria-pressed={isActive}
            className={cn(
              "pressable type-micro rounded-full px-2.5 py-1 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
              isActive
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-border",
            )}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
