import { CheckCircle, FileText, XCircle } from "lucide-react";
import { Button } from "@/components/app/Button";
import { Spinner } from "@/components/app/Spinner";
import { cn } from "@/lib/cn";
import type { FitResult } from "@/lib/types";

export interface VerdictHeaderProps {
  fit: FitResult | null;
  onExportPdf: () => void;
  onExportHtml: () => void;
}

// The error message is rendered here, immediately under the verdict row --
// not appended after the cards below it. The Tk original packed it as a
// child of the scroll frame but only pack()ed it into place on error, which
// put it at the *end* of the pack order (~950px below the verdict it
// explains). Keeping both in the same component makes that class of bug
// impossible here: there is only one place in the JSX for it to be.
export function VerdictHeader({ fit, onExportPdf, onExportHtml }: VerdictHeaderProps) {
  // fit is only null for the brief window before the first evaluateFit
  // call resolves -- that is "not computed yet", not a failed verdict, and
  // must not be collapsed into a confident red "Does not fit" (a `?? false`
  // on fit.fits would do exactly that).
  const hasError = fit !== null && fit.error !== null;
  const fits = fit !== null && fit.error === null && fit.fits;

  const colorClass =
    fit === null ? "text-muted-foreground" : hasError || !fits ? "text-destructive" : "text-primary";
  const text = fit === null ? "Calculating…" : hasError ? "Can't estimate" : fits ? "Fits on this hardware" : "Does not fit";

  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className={cn("flex items-center gap-2", colorClass)}>
          {fit === null ? (
            <Spinner size={20} />
          ) : hasError || !fits ? (
            <XCircle size={20} aria-hidden="true" />
          ) : (
            <CheckCircle size={20} aria-hidden="true" />
          )}
          <p className="type-heading">{text}</p>
        </div>
        <div className="flex items-center gap-1.5">
          <Button type="button" variant="secondary" icon={FileText} disabled={fit === null} onClick={onExportPdf}>
            Export PDF
          </Button>
          <Button type="button" variant="secondary" icon={FileText} disabled={fit === null} onClick={onExportHtml}>
            Export HTML
          </Button>
        </div>
      </div>
      {hasError && (
        <p className="type-body flex items-start gap-1.5 text-destructive">
          <XCircle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
          {fit.error}
        </p>
      )}
    </div>
  );
}
