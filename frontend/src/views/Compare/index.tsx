import { useEffect, useState } from "react";
import { BarChart2, FileText } from "lucide-react";
import { Button } from "@/components/app/Button";
import { EmptyState } from "@/components/app/EmptyState";
import { StatPill } from "@/components/app/StatPill";
import { TabBar } from "@/components/app/TabBar";
import { useApp } from "@/lib/appContext";
import { useJob } from "@/hooks/useJob";
import { bridge, BridgeError } from "@/lib/bridge";
import { parseIntSafe } from "@/lib/format";
import type { CompareReport, PortfolioProjection } from "@/lib/types";
import { InputCard } from "./InputCard";
import { ModelChecklist } from "./ModelChecklist";
import { ResultRow } from "./ResultRow";
import { ProjectionTab } from "./ProjectionTab";
import type { ExportFormat, Frequency } from "./ProjectionTab";

type TabId = "results" | "projection";

const EXPORT_LABELS: Record<ExportFormat, string> = { csv: "CSV", md: "MD", pdf: "PDF", html: "HTML" };
const FREQUENCY_LABELS: Record<Frequency, string> = {
  daily: "Per day",
  weekly: "Per week",
  monthly: "Per month",
};

interface ProjectCostsResult {
  projections: PortfolioProjection[];
  cheapest: PortfolioProjection | null;
}

export default function Compare() {
  const { models, settings } = useApp();
  const [text, setText] = useState("");
  const [paths, setPaths] = useState<string[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set(models.map((m) => m.id)));
  const [outputTokens, setOutputTokens] = useState(String(settings.default_output_tokens));
  const [runs, setRuns] = useState("100");
  const [frequency, setFrequency] = useState<Frequency>("daily");
  const [report, setReport] = useState<CompareReport | null>(null);
  const [projection, setProjection] = useState<ProjectCostsResult | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>("results");
  const [status, setStatus] = useState<string | null>(null);

  const job = useJob<string, CompareReport>();
  const selectedModels = models.filter((m) => selectedIds.has(m.id));
  const outputTokensValid = parseIntSafe(outputTokens) !== null;
  const hasInput = paths.length > 0 || text.trim().length > 0;

  async function pickFile() {
    try {
      const picked = await bridge.pickFiles();
      if (picked.length > 0) setPaths(picked);
    } catch (err) {
      setStatus(`Pick file failed: ${bridgeErrorMessage(err)}`);
    }
  }

  async function pickFolder() {
    try {
      const picked = await bridge.pickFolder();
      if (picked) setPaths([picked]);
    } catch (err) {
      setStatus(`Pick folder failed: ${bridgeErrorMessage(err)}`);
    }
  }

  const runDisabledReason =
    selectedModels.length === 0
      ? "Select at least one model to compare"
      : !hasInput
        ? "Enter text or add files to compare"
        : null;

  async function handleRun() {
    if (job.running || runDisabledReason !== null) return;
    setCancelling(false);
    setStatus(null);
    const outTokens = parseIntSafe(outputTokens) ?? settings.default_output_tokens;
    await job.start(() =>
      bridge.startCompare(text, paths, selectedModels.map((m) => m.id), outTokens),
    );
  }

  function handleCancel() {
    setCancelling(true);
    job.cancel();
  }

  useEffect(() => {
    if (job.result === null) return;
    setReport(job.result);
    setCancelling(false);
  }, [job.result]);

  useEffect(() => {
    if (!job.cancelled) return;
    setCancelling(false);
  }, [job.cancelled]);

  useEffect(() => {
    if (!job.error) return;
    setCancelling(false);
    setStatus(`Compare failed: ${job.error}`);
  }, [job.error]);

  // what_if: recompute cost fields for the new output-token assumption
  // without re-tokenizing -- a cheap synchronous call per model, no job.
  useEffect(() => {
    const tokens = parseIntSafe(outputTokens);
    if (tokens === null || report === null) return;
    let cancelled = false;
    void (async () => {
      try {
        const updated = await Promise.all(report.results.map((r) => bridge.whatIf(r, tokens)));
        if (!cancelled) {
          setReport((prev) => (prev ? { source_label: prev.source_label, results: updated } : prev));
        }
      } catch {
        // Best-effort recompute; keep the existing report on failure.
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [outputTokens]);

  // Projection extends the last comparison's per-model token counts across
  // a run frequency -- re-derives whenever the report, output tokens, runs,
  // or frequency changes.
  useEffect(() => {
    if (report === null) {
      setProjection(null);
      return;
    }
    const corpusTokens: Record<string, number> = {};
    for (const r of report.results) {
      if (r.error === null) corpusTokens[r.model.id] = r.token_count;
    }
    const modelIds = Object.keys(corpusTokens);
    if (modelIds.length === 0) {
      setProjection({ projections: [], cheapest: null });
      return;
    }
    const outTokens = parseIntSafe(outputTokens) ?? 0;
    const runsNum = parseIntSafe(runs) ?? 0;
    let cancelled = false;
    void (async () => {
      try {
        const result = await bridge.projectCosts(corpusTokens, outTokens, runsNum, frequency, modelIds);
        if (!cancelled) setProjection(result);
      } catch {
        // Best-effort; leave the previous projection on failure.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [report, outputTokens, runs, frequency]);

  async function handleExport(fmt: ExportFormat) {
    if (!report) return;
    try {
      const runsNum = parseIntSafe(runs);
      const frequencyLabel =
        projection && runsNum !== null ? `${runsNum} runs ${FREQUENCY_LABELS[frequency]}` : null;
      const path = await bridge.exportComparison(report, projection?.projections ?? null, frequencyLabel, fmt);
      if (path) setStatus(`Exported to ${path}`);
    } catch (err) {
      setStatus(`Export failed: ${bridgeErrorMessage(err)}`);
    }
  }

  const successful = report ? report.results.filter((r) => r.error === null) : [];
  const cheapest =
    successful.length > 0 ? successful.reduce((a, b) => (a.total_cost <= b.total_cost ? a : b)) : null;
  const sortedResults = report
    ? [...report.results].sort((a, b) => {
        if ((a.error !== null) !== (b.error !== null)) return a.error !== null ? 1 : -1;
        return a.total_cost - b.total_cost;
      })
    : [];

  return (
    <div className="flex h-full gap-4 p-4">
      <div className="flex w-[340px] shrink-0 flex-col gap-3 overflow-y-auto">
        <InputCard
          text={text}
          onTextChange={setText}
          paths={paths}
          onPaths={setPaths}
          onPickFile={pickFile}
          onPickFolder={pickFolder}
          outputTokens={outputTokens}
          onOutputTokensChange={setOutputTokens}
          outputTokensValid={outputTokensValid}
          running={job.running}
          cancelling={cancelling}
          onRun={handleRun}
          onCancel={handleCancel}
          runDisabledReason={runDisabledReason}
        />
        <ModelChecklist models={models} selected={selectedIds} onChange={setSelectedIds} />
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <TabBar
          tabs={[
            {
              id: "results",
              label: "Results",
              badge: report?.results.length || undefined,
              panel: (
                <div className="flex h-full flex-col gap-3 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-3">
                      {report && <StatPill label="Source" value={report.source_label} />}
                      {cheapest && <StatPill label="Cheapest" value={cheapest.model.display_name} />}
                    </div>
                    <div className="flex items-center gap-1.5">
                      {(Object.keys(EXPORT_LABELS) as ExportFormat[]).map((fmt) => (
                        <Button
                          key={fmt}
                          type="button"
                          variant="secondary"
                          icon={FileText}
                          disabled={!report}
                          onClick={() => handleExport(fmt)}
                        >
                          Export {EXPORT_LABELS[fmt]}
                        </Button>
                      ))}
                    </div>
                  </div>
                  {!report ? (
                    <EmptyState
                      icon={BarChart2}
                      title="No results yet"
                      description="Enter text or pick a file, choose models, and click Compare"
                    />
                  ) : (
                    <div className="flex-1 overflow-y-auto">
                      <div className="flex flex-col gap-2">
                        {sortedResults.map((r) => (
                          <ResultRow key={r.model.id} result={r} isCheapest={cheapest?.model.id === r.model.id} />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ),
            },
            {
              id: "projection",
              label: "Projection",
              panel: (
                <ProjectionTab
                  hasReport={report !== null}
                  sourceLabel={report?.source_label ?? null}
                  runs={runs}
                  onRunsChange={setRuns}
                  frequency={frequency}
                  onFrequencyChange={setFrequency}
                  projections={projection?.projections ?? []}
                  cheapestId={projection?.cheapest?.model.id ?? null}
                  onExport={handleExport}
                />
              ),
            },
          ]}
          value={activeTab}
          onChange={setActiveTab}
        />
        {status && <p className="type-small px-3 py-2 text-muted-foreground">{status}</p>}
      </div>
    </div>
  );
}

function bridgeErrorMessage(err: unknown): string {
  return err instanceof BridgeError ? err.message : String(err);
}
