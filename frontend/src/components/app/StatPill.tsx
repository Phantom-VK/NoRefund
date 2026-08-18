import { cn } from "@/lib/cn";

export interface StatPillProps {
  label: string;
  value: string;
  /** Tabular figures so digits don't jitter as the value updates. */
  mono?: boolean;
}

export function StatPill({ label, value, mono = false }: StatPillProps) {
  return (
    <div className="flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1">
      <span className="type-micro text-muted-foreground">{label}</span>
      <span className={cn("type-small text-foreground", mono && "tabular")}>
        {value}
      </span>
    </div>
  );
}
