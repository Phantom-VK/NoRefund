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
        // transform, not width -- width triggers layout on every frame
        // (00-OVERVIEW.md §4); scaleX + a left origin gets the same fill
        // effect off the main thread. backgroundColor is paint-only, so
        // transitioning it alongside costs nothing and turns the ok/warn/
        // over colour swap into a shift instead of a snap.
        className="h-full w-full origin-left rounded-full"
        style={{
          transform: `scaleX(${clamped / 100})`,
          backgroundColor: color,
          transition: "transform var(--dur-dropdown) var(--ease-out), background-color var(--dur-dropdown) var(--ease-out)",
        }}
      />
    </div>
  );
}
