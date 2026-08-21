import { CheckCircle, XCircle } from "lucide-react";
import { Card } from "@/components/app/Card";
import { ContextBar } from "@/components/app/ContextBar";
import { ProviderBadge } from "@/components/app/ProviderBadge";
import { fmtContextPct, fmtCost, fmtNum } from "@/lib/format";
import type { ModelComparison } from "@/lib/types";

export interface ResultRowProps {
  result: ModelComparison;
  isCheapest: boolean;
}

// GUI_REVIEW.md §4.1: the Tk version filled the whole cheapest-row card with
// --primary, which made the context bar 1:1 against its own background and
// turned the "doesn't fit" X white instead of red. Card's `accent` strip is
// the only thing that changes here -- every child below keeps its normal
// semantic color regardless of isCheapest.
export function ResultRow({ result, isCheapest }: ResultRowProps) {
  return (
    <Card accent={isCheapest} className="p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <ProviderBadge provider={result.model.provider} />
          <span className="type-title truncate text-foreground">{result.model.display_name}</span>
        </div>
        {isCheapest && (
          <span className="type-micro flex shrink-0 items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 font-semibold text-primary">
            <CheckCircle size={12} aria-hidden="true" />
            cheapest
          </span>
        )}
      </div>

      {result.error !== null ? (
        <p className="type-small mt-2 flex items-center gap-1.5 text-destructive">
          <XCircle size={14} className="shrink-0" aria-hidden="true" />
          {result.error}
        </p>
      ) : (
        <>
          <div className="mt-3 flex flex-wrap items-center gap-4">
            <span className="type-small tabular font-mono text-muted-foreground">
              Tokens: {fmtNum(result.token_count)}
              {result.tokenizer_is_approximate ? " (approx.)" : ""}
            </span>
            <div className="flex items-center gap-2">
              <ContextBar
                pct={result.context_usage_pct}
                className="w-24"
                label={`Context window usage for ${result.model.display_name}`}
              />
              <span className="type-small tabular font-mono text-muted-foreground">
                {fmtContextPct(result.context_usage_pct)}
              </span>
            </div>
            {result.fits_in_context ? (
              <CheckCircle size={14} className="text-primary" aria-hidden="true" />
            ) : (
              <XCircle size={14} className="text-destructive" aria-hidden="true" />
            )}
          </div>
          <p className="type-small tabular mt-2 font-mono font-semibold text-foreground">
            Input {fmtCost(result.input_cost)} · Output {fmtCost(result.output_cost)} · Total{" "}
            {fmtCost(result.total_cost)}
          </p>
        </>
      )}
    </Card>
  );
}
