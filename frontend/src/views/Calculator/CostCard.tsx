import { TriangleAlert } from "lucide-react";
import { Card } from "@/components/app/Card";
import { SectionLabel } from "@/components/app/SectionLabel";
import { fmtCost } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { ModelInfo } from "@/lib/types";

export interface CostCardProps {
  inputCost: number | null;
  outputCost: number | null;
  totalCost: number | null;
  model: ModelInfo;
}

function rate(perMillion: number): string {
  return `$${perMillion.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} / 1M tokens`;
}

function Column({
  label,
  value,
  subtitle,
  bordered,
}: {
  label: string;
  value: number | null;
  subtitle: string;
  bordered: boolean;
}) {
  return (
    <div className={cn("flex-1", bordered && "border-l border-border pl-4")}>
      <SectionLabel>{label}</SectionLabel>
      <p className="type-display tabular text-primary">
        {value === null ? "—" : fmtCost(value)}
      </p>
      <p className="type-small text-muted-foreground">{subtitle}</p>
    </div>
  );
}

export function CostCard({ inputCost, outputCost, totalCost, model }: CostCardProps) {
  return (
    <Card>
      <div className="flex gap-4">
        <Column label="Input cost" value={inputCost} subtitle={rate(model.input_price_per_million)} bordered={false} />
        <Column label="Output cost" value={outputCost} subtitle={rate(model.output_price_per_million)} bordered />
        <Column label="Total cost" value={totalCost} subtitle={model.currency} bordered />
      </div>
      <div className="my-4 h-px bg-border" />
      <div className="flex items-center gap-2">
        <TriangleAlert size={14} className="shrink-0 text-primary" aria-hidden="true" />
        <p className="type-small text-muted-foreground">
          Prices are estimates based on locally stored pricing data and may not reflect
          current provider rates.
        </p>
      </div>
    </Card>
  );
}
