import { Info, TriangleAlert } from "lucide-react";
import { Card } from "@/components/app/Card";
import { SectionLabel } from "@/components/app/SectionLabel";
import { convertCurrency } from "@/lib/costing";
import { fmtCostIn } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { ExchangeRates, ModelInfo } from "@/lib/types";

export interface CostCardProps {
  /** USD. */
  inputCost: number | null;
  outputCost: number | null;
  totalCost: number | null;
  model: ModelInfo;
  /** Display currency (settings.currency) -- costs are converted into this
   *  from the model's USD prices before rendering. */
  currency: string;
  rates: ExchangeRates;
}

function rate(perMillionUsd: number, currency: string, rates: ExchangeRates): string {
  return `${fmtCostIn(convertCurrency(perMillionUsd, currency, rates), currency)} / 1M tokens`;
}

function Column({
  label,
  valueUsd,
  currency,
  rates,
  subtitle,
  bordered,
}: {
  label: string;
  valueUsd: number | null;
  currency: string;
  rates: ExchangeRates;
  subtitle: string;
  bordered: boolean;
}) {
  return (
    <div className={cn("flex-1", bordered && "border-l border-border pl-4")}>
      <SectionLabel>{label}</SectionLabel>
      <p className="type-display tabular text-primary">
        {valueUsd === null ? "—" : fmtCostIn(convertCurrency(valueUsd, currency, rates), currency)}
      </p>
      <p className="type-small text-muted-foreground">{subtitle}</p>
    </div>
  );
}

export function CostCard({
  inputCost,
  outputCost,
  totalCost,
  model,
  currency,
  rates,
}: CostCardProps) {
  return (
    <Card>
      <div className="flex gap-4">
        <Column
          label="Input cost"
          valueUsd={inputCost}
          currency={currency}
          rates={rates}
          subtitle={rate(model.input_price_per_million, currency, rates)}
          bordered={false}
        />
        <Column
          label="Output cost"
          valueUsd={outputCost}
          currency={currency}
          rates={rates}
          subtitle={rate(model.output_price_per_million, currency, rates)}
          bordered
        />
        <Column
          label="Total cost"
          valueUsd={totalCost}
          currency={currency}
          rates={rates}
          subtitle={currency}
          bordered
        />
      </div>
      <div className="my-4 h-px bg-border" />
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <TriangleAlert size={14} className="shrink-0 text-primary" aria-hidden="true" />
          <p className="type-small text-muted-foreground">
            Prices are estimates based on locally stored pricing data and may not reflect
            current provider rates.
          </p>
        </div>
        {currency !== "USD" && (
          <div className="flex items-center gap-2">
            <Info size={14} className="shrink-0 text-muted-foreground" aria-hidden="true" />
            <p className="type-small text-muted-foreground">
              Converted from USD using{" "}
              {rates.fetched_at ? "rates fetched from Settings" : "built-in approximate rates"}
              {" — "}refresh rates in Settings for the latest figures.
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}
