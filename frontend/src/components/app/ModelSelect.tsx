import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ProviderBadge } from "@/components/app/ProviderBadge";
import { modelLabel } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { ModelInfo } from "@/lib/types";

export interface ModelSelectProps {
  models: ModelInfo[];
  /** Selected model id. */
  value: string;
  onChange: (model: ModelInfo) => void;
  className?: string;
}

/** Radix-based replacement for gui/widgets.py's DropdownButton/DropdownPopover
 *  (~300 lines of hand-rolled popover). Shared by Calculator, Parser, and
 *  Compare -- built once here. */
export function ModelSelect({ models, value, onChange, className }: ModelSelectProps) {
  const selected = models.find((m) => m.id === value) ?? null;

  return (
    <Select
      value={value}
      onValueChange={(id) => {
        const model = models.find((m) => m.id === id);
        if (model) onChange(model);
      }}
    >
      <SelectTrigger className={cn("w-full", className)}>
        <SelectValue placeholder="Select a model">
          {selected && (
            <span className="flex min-w-0 items-center gap-2">
              <ProviderBadge provider={selected.provider} />
              <span className="truncate">{modelLabel(selected)}</span>
            </span>
          )}
        </SelectValue>
      </SelectTrigger>
      {/* Every row gets a leading badge, including providers with no brand
          colour (ProviderBadge falls back to a neutral one), so rows stay
          aligned instead of the mixed icon/no-icon look this replaces. */}
      <SelectContent className="max-h-[min(320px,var(--radix-select-content-available-height))]">
        {models.map((m) => (
          <SelectItem key={m.id} value={m.id}>
            <span className="flex min-w-0 items-center gap-2">
              <ProviderBadge provider={m.provider} />
              <span className="truncate">{modelLabel(m)}</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
