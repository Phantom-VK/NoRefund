import { BarChart2, CheckCircle, FileText, XCircle } from "lucide-react";
import { Button } from "@/components/app/Button";
import { ContextBar } from "@/components/app/ContextBar";
import { EmptyState } from "@/components/app/EmptyState";
import { StatPill } from "@/components/app/StatPill";
import { basename, contextLevel, fmtContextPct, fmtCost, fmtNum } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { AnalysisResult } from "@/lib/types";

export type ExportFormat = "csv" | "md" | "pdf" | "html";

export interface ResultsTableProps {
  results: AnalysisResult[];
  onExport: (fmt: ExportFormat) => void;
}

interface Column {
  key: string;
  label: string;
  weight: number;
  align: "left" | "right" | "center";
}

// One array, not two parallel lists that have to stay index-aligned.
const COLUMNS: Column[] = [
  { key: "file", label: "File", weight: 3, align: "left" },
  { key: "tokens", label: "Tokens", weight: 1, align: "right" },
  { key: "context", label: "Context %", weight: 2, align: "right" },
  { key: "fits", label: "Fits?", weight: 1, align: "center" },
  { key: "chunks", label: "Chunks", weight: 1, align: "right" },
  { key: "cost", label: "Input Cost", weight: 1, align: "right" },
  { key: "words", label: "Words", weight: 1, align: "right" },
  { key: "chars", label: "Chars", weight: 1, align: "right" },
];
const TOTAL_WEIGHT = COLUMNS.reduce((sum, c) => sum + c.weight, 0);

const EXPORT_LABELS: Record<ExportFormat, string> = {
  csv: "CSV",
  md: "MD",
  pdf: "PDF",
  html: "HTML",
};

function alignClass(align: Column["align"]): string {
  return align === "left" ? "text-left" : align === "center" ? "text-center" : "text-right";
}

function contextColor(pct: number | null): string {
  const level = contextLevel(pct);
  return level === "over" ? "text-destructive" : level === "warn" ? "text-warning" : "";
}

function ResultRow({ result }: { result: AnalysisResult }) {
  const name = basename(result.file_path);

  if (result.error !== null) {
    return (
      <tr className="hover:bg-muted">
        <td className="type-small px-2 py-1.5 font-mono">{name}</td>
        <td colSpan={COLUMNS.length - 1} className="px-2 py-1.5">
          <span className="flex items-center gap-1.5 text-destructive">
            <XCircle size={14} className="shrink-0" aria-hidden="true" />
            <span className="type-small">{result.error}</span>
          </span>
        </td>
      </tr>
    );
  }

  return (
    <tr className="hover:bg-muted">
      <td className="type-small truncate px-2 py-1.5 font-mono">{name}</td>
      <td className="type-small tabular px-2 py-1.5 text-right font-mono">
        {fmtNum(result.token_count)}
      </td>
      <td className="px-2 py-1.5">
        <div className="flex items-center justify-end gap-2">
          <ContextBar pct={result.context_usage_pct} className="w-14" />
          <span className={cn("type-small tabular w-11 shrink-0 text-right font-mono", contextColor(result.context_usage_pct))}>
            {fmtContextPct(result.context_usage_pct)}
          </span>
        </div>
      </td>
      <td className="px-2 py-1.5 text-center">
        {result.fits_in_context ? (
          <CheckCircle size={14} className="inline text-primary" aria-hidden="true" />
        ) : (
          <XCircle size={14} className="inline text-destructive" aria-hidden="true" />
        )}
      </td>
      <td className="type-small tabular px-2 py-1.5 text-right font-mono">
        {result.min_chunks_needed}
      </td>
      <td className="type-small tabular px-2 py-1.5 text-right font-mono">
        {fmtCost(result.estimated_input_cost)}
      </td>
      <td className="type-small tabular px-2 py-1.5 text-right font-mono">
        {fmtNum(result.word_count)}
      </td>
      <td className="type-small tabular px-2 py-1.5 text-right font-mono">
        {fmtNum(result.char_count)}
      </td>
    </tr>
  );
}

export function ResultsTable({ results, onExport }: ResultsTableProps) {
  const hasResults = results.length > 0;
  const successful = results.filter((r) => r.error === null);
  const totalTokens = successful.reduce((sum, r) => sum + r.token_count, 0);
  const totalCost = successful.reduce((sum, r) => sum + r.estimated_input_cost, 0);
  const pctValues = successful
    .map((r) => r.context_usage_pct)
    .filter((p): p is number => p !== null);
  const avgPct = pctValues.length > 0 ? pctValues.reduce((a, b) => a + b, 0) / pctValues.length : null;

  return (
    <div className="flex h-full flex-col">
      {/* Export controls are always rendered, disabled with no data rather
         than disappearing -- clicking them with nothing to export used to
         be a silent no-op (GUI_REVIEW.md §4.3). */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-3 py-2">
        <div className="flex flex-wrap items-center gap-3">
          {hasResults && (
            <>
              <StatPill label="Files" value={fmtNum(results.length)} mono />
              <StatPill label="Total tokens" value={fmtNum(totalTokens)} mono />
              <StatPill label="Input cost" value={fmtCost(totalCost)} mono />
              <StatPill label="Avg context" value={fmtContextPct(avgPct)} mono />
            </>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {(Object.keys(EXPORT_LABELS) as ExportFormat[]).map((fmt) => (
            <Button
              key={fmt}
              type="button"
              variant="secondary"
              icon={FileText}
              disabled={!hasResults}
              onClick={() => onExport(fmt)}
            >
              Export {EXPORT_LABELS[fmt]}
            </Button>
          ))}
        </div>
      </div>

      {!hasResults ? (
        <EmptyState
          icon={BarChart2}
          title="No results yet"
          description="Add files and click Analyze to see results"
        />
      ) : (
        <div className="flex-1 overflow-y-auto px-3 pb-3">
          <table className="w-full border-collapse">
            <colgroup>
              {COLUMNS.map((c) => (
                <col key={c.key} style={{ width: `${(c.weight / TOTAL_WEIGHT) * 100}%` }} />
              ))}
            </colgroup>
            <thead className="sticky top-0 z-10 bg-muted">
              <tr>
                {COLUMNS.map((c) => (
                  <th
                    key={c.key}
                    scope="col"
                    className={cn("type-micro px-2 py-1.5 text-muted-foreground", alignClass(c.align))}
                  >
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <ResultRow key={`${r.file_path}-${i}`} result={r} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
