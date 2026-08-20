import * as React from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/cn";

export interface SelectOption {
  value: string;
  label: string;
  badge?: React.ReactNode;
}

export interface AppSelectProps {
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  /** Accessible name -- these are unlabelled controls otherwise even when a
   *  visible label sits next to them in the JSX. */
  label: string;
  className?: string;
  id?: string;
  disabled?: boolean;
}

/** Radix-based generic value select, extracted from ModelSelect so Fit
 *  Check's four plain-value pickers (and ModelSelect itself) share one
 *  implementation rather than maintaining two. */
export function AppSelect({ options, value, onChange, label, className, id, disabled }: AppSelectProps) {
  const selected = options.find((o) => o.value === value) ?? null;

  return (
    <Select value={value} disabled={disabled} onValueChange={onChange}>
      <SelectTrigger id={id} aria-label={label} className={cn("w-full", className)}>
        <SelectValue placeholder={label}>
          {selected && (
            <span className="flex min-w-0 items-center gap-2">
              {selected.badge}
              <span className="truncate">{selected.label}</span>
            </span>
          )}
        </SelectValue>
      </SelectTrigger>
      <SelectContent className="max-h-[min(320px,var(--radix-select-content-available-height))]">
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}>
            <span className="flex min-w-0 items-center gap-2">
              {o.badge}
              <span className="truncate">{o.label}</span>
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
