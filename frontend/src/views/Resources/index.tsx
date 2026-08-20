import { useEffect, useState } from "react";
import { Download, RefreshCw } from "lucide-react";
import { Button } from "@/components/app/Button";
import { SectionLabel } from "@/components/app/SectionLabel";
import { Spinner } from "@/components/app/Spinner";
import { StatPill } from "@/components/app/StatPill";
import { useDelayedFlag } from "@/hooks/useDelayedFlag";
import { useJob } from "@/hooks/useJob";
import { bridge, BridgeError } from "@/lib/bridge";
import { dirname, fmtBytes } from "@/lib/format";
import type { ResourceReport, TokenizerResource } from "@/lib/types";
import { TokenizerRow, type DownloadProgress } from "./TokenizerRow";
import { StorageRow } from "./StorageRow";

// report.py's exact ManagedDir labels for each backend's cache -- used to
// keep the Storage section's per-directory figures in step with a spliced
// download update instead of only bumping the aggregate total.
const DIR_LABEL_BY_BACKEND: Record<TokenizerResource["backend"], string> = {
  tiktoken: "tiktoken cache",
  hf: "HuggingFace cache",
};

export default function Resources() {
  const scanJob = useJob<never, ResourceReport>();
  const downloadJob = useJob<DownloadProgress, TokenizerResource>();

  const [report, setReport] = useState<ResourceReport | null>(null);
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);
  // True once downloadJob.start()'s bridge call has actually resolved and
  // useJob holds a real job id for the in-flight download -- start() is
  // async, so Cancel rendering the instant downloadingKey is set would let
  // an early click race ahead of the id existing, either no-op'ing or
  // cancelling whatever job id useJob still had leftover from the last run.
  const [downloadReady, setDownloadReady] = useState(false);
  const [queue, setQueue] = useState<string[]>([]);
  const [downloadErrors, setDownloadErrors] = useState<Record<string, string>>({});
  const [cancelling, setCancelling] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const showInitialSpinner = useDelayedFlag(!report && !scanJob.error);

  useEffect(() => {
    void scanJob.start(() => bridge.startResourceScan());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (scanJob.result) setReport(scanJob.result);
  }, [scanJob.result]);

  // A refresh that resolves late (after a download that started during it
  // completes) would otherwise overwrite the post-download splice with a
  // pre-download snapshot -- so the two must never overlap in *either*
  // direction, not just "no refresh while downloading".
  const busy = downloadingKey !== null || scanJob.running;

  useEffect(() => {
    if (!scanJob.error) return;
    setStatus(`Refresh failed: ${scanJob.error}`);
  }, [scanJob.error]);

  function refresh() {
    if (busy) return;
    void scanJob.start(() => bridge.startResourceScan());
  }

  async function startDownload(key: string) {
    setDownloadingKey(key);
    setDownloadReady(false);
    setCancelling(false);
    setDownloadErrors((prev) => {
      if (!(key in prev)) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
    await downloadJob.start(() => bridge.startDownload(key));
    setDownloadReady(true);
  }

  function handleCancel() {
    if (!downloadReady) return; // belt-and-suspenders; the button is disabled too
    setQueue([]);
    setCancelling(true);
    downloadJob.cancel();
  }

  function downloadAll() {
    if (busy || !report) return;
    const missing = report.tokenizers.filter((t) => !t.is_cached && t.source_url);
    if (missing.length === 0) return;
    setQueue(missing.slice(1).map((t) => t.key));
    void startDownload(missing[0].key);
  }

  // Whenever a download finishes (success, failure, or cancel) this clears
  // downloadingKey to null; this effect is the only place the queue
  // advances, so every completion path shares one route into the next
  // download instead of each handler re-implementing "start the next one".
  // Also waits out a running scan, for the same reason `busy` gates the
  // manual triggers above.
  useEffect(() => {
    if (downloadingKey !== null || queue.length === 0 || scanJob.running) return;
    const [next, ...rest] = queue;
    setQueue(rest);
    void startDownload(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [downloadingKey, queue, scanJob.running]);

  useEffect(() => {
    if (downloadJob.result === null) return;
    const updated = downloadJob.result;
    setDownloadingKey(null);
    setCancelling(false);
    // Splice the one row in place and recompute totals from the updated
    // list -- no rescan, per the acceptance criteria. That includes the
    // per-directory Storage figures, not just the aggregate: leaving
    // report.dirs untouched would make "Disk used" disagree with the
    // per-cache StorageRow sizes until the next manual refresh.
    setReport((prev) => {
      if (!prev) return prev;
      const previous = prev.tokenizers.find((t) => t.key === updated.key);
      const tokenizers = prev.tokenizers.map((t) => (t.key === updated.key ? updated : t));
      const sizeDelta = (updated.size_bytes ?? 0) - (previous?.size_bytes ?? 0);
      const becameCached = updated.is_cached && !previous?.is_cached;
      const dirLabel = DIR_LABEL_BY_BACKEND[updated.backend];
      const dirs = prev.dirs.map((d) =>
        d.label === dirLabel
          ? { ...d, exists: true, size_bytes: d.size_bytes + sizeDelta, file_count: d.file_count + (becameCached ? 1 : 0) }
          : d,
      );
      return {
        ...prev,
        tokenizers,
        dirs,
        total_tokenizer_bytes: tokenizers.reduce((sum, t) => sum + (t.size_bytes ?? 0), 0),
      };
    });
  }, [downloadJob.result]);

  useEffect(() => {
    if (!downloadJob.error) return;
    if (downloadingKey) {
      const key = downloadingKey;
      const message = downloadJob.error;
      setDownloadErrors((prev) => ({ ...prev, [key]: message }));
    }
    setDownloadingKey(null);
    setCancelling(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [downloadJob.error]);

  useEffect(() => {
    if (!downloadJob.cancelled) return;
    setDownloadingKey(null);
    setCancelling(false);
  }, [downloadJob.cancelled]);

  async function openTarget(path: string) {
    try {
      const ok = await bridge.openPath(path);
      // Clear on success too, not just set on failure -- otherwise an
      // earlier failure's message outlives it and still shows after a
      // later, successful Open folder.
      setStatus(ok ? null : `Couldn't open ${path}`);
    } catch (err) {
      setStatus(`Couldn't open ${path}: ${bridgeErrorMessage(err)}`);
    }
  }

  async function openUrl(url: string) {
    try {
      const ok = await bridge.openUrl(url);
      setStatus(ok ? null : `Couldn't open ${url}`);
    } catch (err) {
      setStatus(`Couldn't open ${url}: ${bridgeErrorMessage(err)}`);
    }
  }

  const cachedCount = report ? report.tokenizers.filter((t) => t.is_cached).length : 0;
  const totalCount = report?.tokenizers.length ?? 0;
  const hasMissing = report ? report.tokenizers.some((t) => !t.is_cached && t.source_url) : false;

  if (!report && scanJob.error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="type-body text-destructive">{scanJob.error}</p>
        <Button type="button" variant="secondary" icon={RefreshCw} onClick={refresh}>
          Retry
        </Button>
      </div>
    );
  }

  if (!report) {
    // A flash of spinner for a scan that resolves in well under 300ms
    // reads worse than a brief blank pause -- only show it once the wait
    // has actually gone on long enough to need explaining.
    return showInitialSpinner ? (
      <div className="flex h-full items-center justify-center">
        <Spinner size={32} />
      </div>
    ) : null;
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="type-heading text-foreground">Resources</h2>
          <p className="type-body text-muted-foreground">
            Tokenizers downloaded to this machine, and where they live on disk.
          </p>
          <p className="type-small text-muted-foreground">
            Downloading is the only time NoRefund uses the network.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <StatPill label="Downloaded" value={`${cachedCount} of ${totalCount}`} mono />
          <StatPill label="Disk used" value={fmtBytes(report.total_tokenizer_bytes)} mono />
          <Button
            type="button"
            variant="secondary"
            icon={RefreshCw}
            loading={scanJob.running}
            disabled={downloadingKey !== null}
            onClick={refresh}
          >
            Refresh
          </Button>
          <Button
            type="button"
            variant="primary"
            icon={Download}
            disabled={busy || !hasMissing}
            onClick={downloadAll}
          >
            Download all
          </Button>
        </div>
      </div>

      <div>
        <SectionLabel className="mb-2">Tokenizers</SectionLabel>
        <div className="flex flex-col gap-2">
          {report.tokenizers.map((resource) => (
            <TokenizerRow
              key={resource.key}
              resource={resource}
              downloading={downloadingKey === resource.key}
              progress={downloadingKey === resource.key ? (downloadJob.progress.at(-1) ?? null) : null}
              busy={busy}
              cancelling={cancelling && downloadingKey === resource.key}
              cancelReady={downloadReady}
              error={downloadErrors[resource.key] ?? null}
              onDownload={() => startDownload(resource.key)}
              onCancel={handleCancel}
              onOpenFolder={() => resource.cache_path && void openTarget(dirname(resource.cache_path))}
              onOpenSourceUrl={() => resource.source_url && void openUrl(resource.source_url)}
            />
          ))}
        </div>
      </div>

      <div>
        <SectionLabel className="mb-2 mt-2">Storage</SectionLabel>
        <div className="flex flex-col gap-2">
          {report.dirs.map((dir) => (
            <StorageRow key={dir.path} dir={dir} onOpenFolder={() => void openTarget(dir.path)} />
          ))}
        </div>
      </div>

      {status && <p className="type-small text-muted-foreground">{status}</p>}
    </div>
  );
}

function bridgeErrorMessage(err: unknown): string {
  return err instanceof BridgeError ? err.message : String(err);
}
