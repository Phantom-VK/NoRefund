import { Button } from "@/components/app/Button";
import { elideMiddle, fmtNum } from "@/lib/format";
import { cn } from "@/lib/cn";

export interface AnalysisProgressProps {
  done: number;
  /** null while scanning a folder -- the eventual count isn't known until
   *  the scan finishes, so there's nothing honest to show but indeterminate. */
  total: number | null;
  currentFile: string | null;
  cancelling: boolean;
  onCancel: () => void;
}

export function AnalysisProgress({
  done,
  total,
  currentFile,
  cancelling,
  onCancel,
}: AnalysisProgressProps) {
  const determinate = total !== null;
  const pct = determinate ? Math.min(1, done / Math.max(total, 1)) : 0;

  return (
    <div className="flex items-center gap-4 border-b border-border bg-card px-3 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <p className="type-small text-muted-foreground">
            {determinate ? `${fmtNum(done)} of ${fmtNum(total)}` : `${fmtNum(done)} files analysed`}
          </p>
          {currentFile && (
            <p className="type-small font-mono text-muted-foreground">
              {elideMiddle(currentFile, 48)}
            </p>
          )}
        </div>
        <div
          role="progressbar"
          aria-valuenow={determinate ? done : undefined}
          aria-valuemin={0}
          aria-valuemax={determinate ? total : undefined}
          className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted"
        >
          <div
            className={cn(
              "h-full w-full origin-left rounded-full bg-primary",
              !determinate && "animate-indeterminate",
            )}
            style={
              determinate
                ? { transform: `scaleX(${pct})`, transition: "transform var(--dur-dropdown) var(--ease-out)" }
                : undefined
            }
          />
        </div>
      </div>
      <Button
        type="button"
        variant="danger"
        loading={cancelling}
        disabled={cancelling}
        onClick={onCancel}
      >
        {cancelling ? "Cancelling…" : "Cancel"}
      </Button>
    </div>
  );
}
