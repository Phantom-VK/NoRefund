import { BarChart2, FileText, XCircle } from "lucide-react";
import { Button } from "@/components/app/Button";
import { EmptyState } from "@/components/app/EmptyState";
import { StatPill } from "@/components/app/StatPill";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ProjectionRow } from "./ProjectionRow";
import type { PortfolioProjection } from "@/lib/types";

export type Frequency = "daily" | "weekly" | "monthly";
export type ExportFormat = "csv" | "md" | "pdf" | "html";

const FREQUENCY_OPTIONS: { value: Frequency; label: string }[] = [
  { value: "daily", label: "Per day" },
  { value: "weekly", label: "Per week" },
  { value: "monthly", label: "Per month" },
];

const EXPORT_LABELS: Record<ExportFormat, string> = {
  csv: "CSV",
  md: "MD",
  pdf: "PDF",
  html: "HTML",
};

export interface ProjectionTabProps {
  hasReport: boolean;
  sourceLabel: string | null;
  runs: string;
  onRunsChange: (v: string) => void;
  frequency: Frequency;
  onFrequencyChange: (f: Frequency) => void;
  projections: PortfolioProjection[];
  cheapestId: string | null;
  onExport: (fmt: ExportFormat) => void;
}

export function ProjectionTab({
  hasReport,
  sourceLabel,
  runs,
  onRunsChange,
  frequency,
  onFrequencyChange,
  projections,
  cheapestId,
  onExport,
}: ProjectionTabProps) {
  // fits-in-context first, then by monthly cost ascending -- matches
  // cheapest_that_fits(), which never picks a non-fitting model regardless
  // of how cheap it is.
  const sorted = [...projections].sort((a, b) => {
    if (a.fits_in_context !== b.fits_in_context) return a.fits_in_context ? -1 : 1;
    return a.monthly_cost - b.monthly_cost;
  });
  const cheapest = projections.find((p) => p.model.id === cheapestId) ?? null;

  return (
    <div className="flex h-full flex-col gap-3 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="compare-runs" className="type-small text-muted-foreground">
          Runs
        </label>
        <Input
          id="compare-runs"
          value={runs}
          onChange={(e) => onRunsChange(e.target.value)}
          className="w-20 font-mono"
        />
        <Select value={frequency} onValueChange={(v) => onFrequencyChange(v as Frequency)}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {FREQUENCY_OPTIONS.map((f) => (
              <SelectItem key={f.value} value={f.value}>
                {f.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="ml-auto flex items-center gap-1.5">
          {(Object.keys(EXPORT_LABELS) as ExportFormat[]).map((fmt) => (
            <Button
              key={fmt}
              type="button"
              variant="secondary"
              icon={FileText}
              disabled={!hasReport}
              onClick={() => onExport(fmt)}
            >
              Export {EXPORT_LABELS[fmt]}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {sourceLabel && <StatPill label="Source" value={sourceLabel} />}
        {cheapest && <StatPill label="Cheapest monthly" value={cheapest.model.display_name} />}
      </div>

      {!hasReport ? (
        <EmptyState
          icon={BarChart2}
          title="No comparison yet"
          description="Run Compare first to project volume costs"
        />
      ) : sorted.length === 0 ? (
        <EmptyState
          icon={XCircle}
          title="Nothing to project"
          description="No model in the last comparison tokenized successfully"
        />
      ) : (
        <div className="flex-1 overflow-y-auto">
          <div className="flex flex-col gap-2">
            {sorted.map((p) => (
              <ProjectionRow key={p.model.id} projection={p} isCheapest={p.model.id === cheapestId} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
