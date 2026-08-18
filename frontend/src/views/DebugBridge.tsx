import { useState } from "react";
import { Button } from "@/components/app/Button";
import { Card } from "@/components/app/Card";
import { bridge, BridgeError } from "@/lib/bridge";
import { useJob } from "@/hooks/useJob";
import type { AnalysisResult } from "@/lib/types";

// Dev-only page exercising every bridge method. No product UI — Phase 03's
// job is the bridge itself, not a screen. Point App.tsx elsewhere once a
// real view exists.

type Result = { method: string; ok: boolean; value: unknown };

const ZERO_ARG_METHODS: Array<[label: string, fn: () => Promise<unknown>]> = [
  ["getModels", () => bridge.getModels()],
  ["getArchitectures", () => bridge.getArchitectures()],
  ["getHardware", () => bridge.getHardware()],
  ["getQuantizationLevels", () => bridge.getQuantizationLevels()],
  ["getKvCacheDtypes", () => bridge.getKvCacheDtypes()],
  ["getSettings", () => bridge.getSettings()],
  ["keyringAvailable", () => bridge.keyringAvailable()],
  ["hasHfToken", () => bridge.hasHfToken()],
  ["pickFiles", () => bridge.pickFiles()],
  ["pickFolder", () => bridge.pickFolder()],
  ["startResourceScan", () => bridge.startResourceScan()],
];

export default function DebugBridge() {
  const [results, setResults] = useState<Result[]>([]);
  const folderJob = useJob<AnalysisResult, AnalysisResult[]>();

  async function run(label: string, fn: () => Promise<unknown>) {
    try {
      const value = await fn();
      setResults((prev) => [{ method: label, ok: true, value }, ...prev]);
    } catch (err) {
      const value = err instanceof BridgeError ? err.message : String(err);
      setResults((prev) => [{ method: label, ok: false, value }, ...prev]);
    }
  }

  async function analyzeFolder() {
    await folderJob.start(async () => {
      const folder = await bridge.pickFolder();
      if (!folder) throw new Error("No folder selected");
      const models = await bridge.getModels();
      return bridge.startAnalysis([folder], models[0].id);
    });
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-6 overflow-y-auto p-6">
      <header>
        <h1 className="type-display">Bridge debug panel</h1>
        <p className="type-body text-muted-foreground">
          Every js_api method, called directly. Dev-only.
        </p>
      </header>

      <section className="flex flex-wrap gap-2">
        {ZERO_ARG_METHODS.map(([label, fn]) => (
          <Button key={label} variant="secondary" onClick={() => run(label, fn)}>
            {label}
          </Button>
        ))}
      </section>

      <Card>
        <div className="flex flex-col gap-3">
          <p className="type-title">Analyze a folder (job stream)</p>
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              onClick={analyzeFolder}
              disabled={folderJob.running}
            >
              Analyze this folder
            </Button>
            {folderJob.running && (
              <Button variant="ghost" onClick={folderJob.cancel}>
                Cancel
              </Button>
            )}
            <Button variant="ghost" onClick={folderJob.reset}>
              Reset
            </Button>
          </div>
          <p className="type-small text-muted-foreground">
            job: {folderJob.jobId ?? "—"} · running: {String(folderJob.running)} ·
            cancelled: {String(folderJob.cancelled)} · progress events:{" "}
            {folderJob.progress.length}
          </p>
          {folderJob.error && (
            <p className="type-small text-destructive">{folderJob.error}</p>
          )}
          {folderJob.result && (
            <p className="type-small text-muted-foreground">
              done: {folderJob.result.length} results
            </p>
          )}
        </div>
      </Card>

      <section className="flex flex-col gap-2">
        {results.map((r, i) => (
          <Card key={i}>
            <div className="flex flex-col gap-1">
              <p className="type-small">
                <span className={r.ok ? "text-primary" : "text-destructive"}>
                  {r.ok ? "ok" : "error"}
                </span>{" "}
                — {r.method}
              </p>
              <pre className="type-micro tabular max-h-40 overflow-auto whitespace-pre-wrap normal-case tracking-normal">
                {JSON.stringify(r.value, null, 2)}
              </pre>
            </div>
          </Card>
        ))}
      </section>
    </div>
  );
}
