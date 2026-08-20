import { cn } from "@/lib/cn";

export interface StatPillProps {
  label: string;
  value: string;
  /** Tabular figures so digits don't jitter as the value updates. */
  mono?: boolean;
  /** Override the value's default text-foreground, e.g. text-destructive
   *  for an over-budget headroom figure. */
  valueClassName?: string;
}

export function StatPill({ label, value, mono = false, valueClassName }: StatPillProps) {
  return (
    <div className="flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1">
      <span className="type-micro text-muted-foreground">{label}</span>
      <span className={cn("type-small text-foreground", mono && "tabular", valueClassName)}>
        {value}
      </span>
    </div>
  );
}
