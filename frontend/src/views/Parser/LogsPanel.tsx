import { useEffect, useRef } from "react";
import { ScrollText } from "lucide-react";
import { EmptyState } from "@/components/app/EmptyState";
import { cn } from "@/lib/cn";
import type { LogEntry } from "@/lib/types";

export interface LogsPanelProps {
  entries: LogEntry[];
}

// Matches parser_view.py's LogsPanel._TAG_COLORS -- CSS custom properties,
// not colours resolved once at construction, so a theme toggle recolours
// the log immediately instead of going stale (GUI_REVIEW.md §3.7).
const LEVEL_CLASS: Record<string, string> = {
  INFO: "text-muted-foreground",
  WARNING: "text-warning",
  ERROR: "text-destructive",
  DEBUG: "text-muted-foreground",
};

const NEAR_BOTTOM_PX = 24;

export function LogsPanel({ entries }: LogsPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Starts true so the first batch of entries scrolls into view.
  const wasAtBottomRef = useRef(true);

  function handleScroll() {
    const el = containerRef.current;
    if (!el) return;
    wasAtBottomRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
  }

  useEffect(() => {
    const el = containerRef.current;
    // Never yank the viewport away from someone who scrolled up to read.
    if (!el || !wasAtBottomRef.current) return;
    el.scrollTop = el.scrollHeight;
  }, [entries]);

  if (entries.length === 0) {
    return (
      <EmptyState
        icon={ScrollText}
        title="No logs yet"
        description="Run an analysis to see activity here."
      />
    );
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="type-small h-full overflow-y-auto px-3 py-2 font-mono"
    >
      {entries.map((entry, i) => {
        const ctxStr = Object.entries(entry.ctx)
          .map(([k, v]) => `${k}=${v}`)
          .join(" ");
        return (
          <p
            key={i}
            className={cn(
              "whitespace-pre-wrap",
              LEVEL_CLASS[entry.level] ?? "text-muted-foreground",
            )}
          >
            {"›  "}[{entry.level}]  {entry.message}
            {ctxStr && `  ${ctxStr}`}
          </p>
        );
      })}
    </div>
  );
}
