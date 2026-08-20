import { CheckCircle, XCircle } from "lucide-react";
import { Card } from "@/components/app/Card";
import { fmtCost } from "@/lib/format";
import type { PortfolioProjection } from "@/lib/types";

export interface ProjectionRowProps {
  projection: PortfolioProjection;
  isCheapest: boolean;
}

// Same accent-strip treatment as ResultRow, for the same reason -- see
// GUI_REVIEW.md §4.1. A non-fitting corpus is flagged regardless of cost
// and is never marked cheapest, matching core/portfolio.py's
// cheapest_that_fits().
export function ProjectionRow({ projection, isCheapest }: ProjectionRowProps) {
  return (
    <Card accent={isCheapest} className="p-4">
      <div className="flex items-start justify-between gap-2">
        <span className="type-title truncate text-foreground">{projection.model.display_name}</span>
        {!projection.fits_in_context ? (
          <span className="type-micro flex shrink-0 items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 font-semibold text-destructive">
            <XCircle size={12} aria-hidden="true" />
            corpus doesn&apos;t fit
          </span>
        ) : (
          isCheapest && (
            <span className="type-micro flex shrink-0 items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 font-semibold text-primary">
              <CheckCircle size={12} aria-hidden="true" />
              cheapest
            </span>
          )
        )}
      </div>
      <p className="type-small tabular mt-2 font-mono font-semibold text-foreground">
        Per run {fmtCost(projection.cost_per_run)} · Monthly {fmtCost(projection.monthly_cost)} · Annual{" "}
        {fmtCost(projection.annual_cost)}
      </p>
    </Card>
  );
}
