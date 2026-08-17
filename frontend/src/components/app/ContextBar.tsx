import { contextLevel } from "@/lib/format";
import { cn } from "@/lib/cn";

export interface ContextBarProps {
  pct: number | null;
  className?: string;
  forceColor?: string;
}

export function ContextBar({ pct, className, forceColor }: ContextBarProps) {
  const level = contextLevel(pct);
  const color =
    forceColor ??
    (level === "over"
      ? "var(--destructive)"
      : level === "warn"
        ? "var(--warning)"
        : "var(--primary)");
  const clamped = pct === null ? 0 : Math.min(100, Math.max(0, pct));

  return (
    <div
      role="progressbar"
      aria-valuenow={pct ?? undefined}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn(
        "relative h-2 w-full overflow-hidden rounded-full bg-muted",
        className,
      )}
    >
      <div
        className="h-full rounded-full"
        style={{
          width: `${clamped}%`,
          backgroundColor: color,
          transition: "width var(--dur-dropdown) var(--ease-out)",
        }}
      />
    </div>
  );
}
