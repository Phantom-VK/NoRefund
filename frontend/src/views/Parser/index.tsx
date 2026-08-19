import { useEffect, useState } from "react";
import { FolderOpen } from "lucide-react";
import { EmptyState } from "@/components/app/EmptyState";
import { TabBar } from "@/components/app/TabBar";
import { useApp } from "@/lib/appContext";
import { useJob } from "@/hooks/useJob";
import { useFileDrop } from "@/hooks/useFileDrop";
import { bridge, BridgeError } from "@/lib/bridge";
import { SUPPORTED_EXTENSIONS, hasSupportedExtension } from "@/lib/parsing";
import { basename, fmtCost, fmtNum } from "@/lib/format";
import type { AnalysisResult, LogEntry } from "@/lib/types";
import { Toolbar } from "./Toolbar";
import { FileStrip } from "./FileStrip";
import { AnalysisProgress } from "./AnalysisProgress";
import { ResultsTable, type ExportFormat } from "./ResultsTable";
import { LogsPanel } from "./LogsPanel";
import { StatusBar } from "./StatusBar";

type TabId = "results" | "logs";

interface Status {
  left: string;
  right: string | null;
}

export default function Parser() {
  const { models, settings, setLastAnalysisTokens, setFileCount } = useApp();
  const [paths, setPaths] = useState<string[]>([]);
  const [modelId, setModelId] = useState(models[0]?.id ?? "");
  const [outputRaw, setOutputRaw] = useState(String(settings.default_output_tokens));
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>("results");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [cancelling, setCancelling] = useState(false);
  const [analysisTotal, setAnalysisTotal] = useState<number | null>(null);
  const [status, setStatus] = useState<Status | null>(null);

  const job = useJob<AnalysisResult, AnalysisResult[]>();
  const model = models.find((m) => m.id === modelId) ?? models[0];

  // Views stay mounted for the app's lifetime, so this doesn't get to
  // re-read the default just by remounting when Settings changes it.
  useEffect(() => {
    setOutputRaw(String(settings.default_output_tokens));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.default_output_tokens]);

  useEffect(() => {
    setFileCount(paths.length);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paths.length]);

  function addPaths(newPaths: string[]) {
    setPaths((prev) => {
      const existing = new Set(prev);
      const merged = [...prev];
      for (const p of newPaths) {
        if (!existing.has(p)) {
          merged.push(p);
          existing.add(p);
        }
      }
      return merged;
    });
  }

  const { dropping, bind: dropBind } = useFileDrop({
    onPaths: addPaths,
    extensions: SUPPORTED_EXTENSIONS,
  });

  async function handleAddFiles() {
    try {
      const picked = await bridge.pickFiles();
      if (picked.length > 0) addPaths(picked);
    } catch (err) {
      setStatus({ left: bridgeErrorMessage(err), right: null });
    }
  }

  async function handleAddFolder() {
    try {
      const picked = await bridge.pickFolder();
      if (picked) addPaths([picked]);
    } catch (err) {
      setStatus({ left: bridgeErrorMessage(err), right: null });
    }
  }

  function handleRemove(path: string) {
    setPaths((prev) => prev.filter((p) => p !== path));
  }

  function handleClear() {
    if (job.running) job.cancel();
    const clearedCount = paths.length;
    setPaths([]);
    setResults([]);
    job.reset();
    setCancelling(false);
    setStatus(
      clearedCount > 0 ? { left: `Cleared · ${clearedCount} file(s) removed`, right: null } : null,
    );
  }

  async function refreshLogs() {
    try {
      setLogs(await bridge.getLogs());
    } catch {
      // Logs are best-effort -- a failed fetch just leaves the panel as-is.
    }
  }

  function handleTabChange(id: TabId) {
    setActiveTab(id);
    if (id === "logs") void refreshLogs();
  }

  async function analyze() {
    if (!model || paths.length === 0 || job.running) return;
    setResults([]);
    setStatus(null);
    setCancelling(false);
    // Known only when every selected path is a plain file -- a folder's
    // contents aren't counted until analyze_folder actually walks it.
    setAnalysisTotal(paths.every(hasSupportedExtension) ? paths.length : null);
    await job.start(() => bridge.startAnalysis(paths, model.id));
  }

  function handleCancel() {
    setCancelling(true);
    job.cancel();
  }

  // Each progress event is one completed file. Append, never rebuild --
  // rebuilding the whole table on every event was the 26-second bug.
  useEffect(() => {
    if (job.progress.length === 0) return;
    setResults((prev) => [...prev, job.progress[job.progress.length - 1]]);
  }, [job.progress.length]);

  useEffect(() => {
    if (job.result === null) return;
    // Reconcile against the authoritative final list -- if the streamed
    // rows and the returned list ever differ, trust the payload.
    const final = job.result;
    setResults(final);
    setCancelling(false);
    const successful = final.filter((r) => r.error === null);
    const totalTokens = successful.reduce((sum, r) => sum + r.token_count, 0);
    const totalCost = successful.reduce((sum, r) => sum + r.estimated_input_cost, 0);
    if (totalTokens > 0) setLastAnalysisTokens(totalTokens);
    setStatus({
      left: `Done · ${final.length} file(s) analysed with ${model?.display_name ?? "model"}`,
      right: `Total tokens: ${fmtNum(totalTokens)}    Est. input cost: ${fmtCost(totalCost)}`,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.result]);

  useEffect(() => {
    if (!job.cancelled) return;
    setCancelling(false);
    setStatus({
      left: `Cancelled · ${results.length} file(s) analysed with ${model?.display_name ?? "model"}`,
      right: null,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.cancelled]);

  useEffect(() => {
    if (!job.error) return;
    setCancelling(false);
    setStatus({ left: `Analysis failed: ${job.error}`, right: null });
  }, [job.error]);

  // The Logs tab refetches once an analysis finishes so the run's own log
  // lines are there without a manual switch away and back.
  useEffect(() => {
    if (job.result === null && !job.cancelled) return;
    if (activeTab === "logs") void refreshLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.result, job.cancelled]);

  async function handleExport(fmt: ExportFormat) {
    try {
      const path = await bridge.exportAnalysis(results, fmt);
      // null means the save dialog was cancelled -- a legitimate no-op.
      if (path) setStatus({ left: `Exported to ${path}`, right: null });
    } catch (err) {
      setStatus({ left: `Export failed: ${bridgeErrorMessage(err)}`, right: null });
    }
  }

  if (!model) {
    return (
      <EmptyState
        icon={FolderOpen}
        title="No models available"
        description="The model registry is empty."
      />
    );
  }

  return (
    <div {...dropBind} className="flex h-full flex-col">
      <Toolbar
        onAddFiles={handleAddFiles}
        onAddFolder={handleAddFolder}
        onClear={handleClear}
        clearDisabled={paths.length === 0 && results.length === 0}
        models={models}
        modelId={model.id}
        onModelChange={(m) => setModelId(m.id)}
        outputRaw={outputRaw}
        onOutputChange={setOutputRaw}
        analyzing={job.running}
        cancelling={cancelling}
        analyzeDisabled={paths.length === 0 || job.running}
        onAnalyze={analyze}
        onCancel={handleCancel}
      />
      <FileStrip paths={paths} onRemove={handleRemove} dropping={dropping} />
      {job.running && (
        <AnalysisProgress
          done={results.length}
          total={analysisTotal}
          currentFile={results.length > 0 ? basename(results[results.length - 1].file_path) : null}
          cancelling={cancelling}
          onCancel={handleCancel}
        />
      )}
      <div className="px-3 pt-2">
        <TabBar
          tabs={[
            { id: "results", label: "Results", badge: results.length || undefined },
            { id: "logs", label: "Logs" },
          ]}
          value={activeTab}
          onChange={handleTabChange}
        />
      </div>
      <div className="min-h-0 flex-1">
        {activeTab === "results" ? (
          <ResultsTable results={results} onExport={handleExport} />
        ) : (
          <LogsPanel entries={logs} />
        )}
      </div>
      <StatusBar left={status?.left ?? null} right={status?.right ?? null} />
    </div>
  );
}

function bridgeErrorMessage(err: unknown): string {
  return err instanceof BridgeError ? err.message : String(err);
}
