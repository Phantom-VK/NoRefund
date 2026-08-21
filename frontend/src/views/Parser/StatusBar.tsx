import { cn } from "@/lib/cn";

export interface StatusBarProps {
  left: string | null;
  right: string | null;
}

/** No visible footprint until there is something to say -- but the live
 *  region itself stays mounted, since a screen reader only announces a
 *  mutation inside an already-present aria-live node, not one that
 *  appears already populated (setStatus(null) at the start of a job
 *  would otherwise unmount and remount this on every run, and the
 *  completion announcement -- the one that matters -- would never
 *  fire). */
export function StatusBar({ left, right }: StatusBarProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "flex items-center justify-between",
        left && "border-t border-border bg-card px-3 py-1.5",
      )}
    >
      {left && <p className="type-small text-muted-foreground">{left}</p>}
      {right && (
        <p className="type-small tabular font-mono text-muted-foreground">{right}</p>
      )}
    </div>
  );
}
