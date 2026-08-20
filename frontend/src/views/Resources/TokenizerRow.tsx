import { Download, ExternalLink, FolderOpen, X } from "lucide-react";
import { Button } from "@/components/app/Button";
import { Card } from "@/components/app/Card";
import { elideMiddle, fmtBytes, fmtNum } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { TokenizerResource } from "@/lib/types";

export interface DownloadProgress {
  downloaded: number;
  total: number | null;
}

export interface TokenizerRowProps {
  resource: TokenizerResource;
  /** This row's own download is in flight. */
  downloading: boolean;
  progress: DownloadProgress | null;
  /** Any download (this row or another) is in flight -- disables Download
   *  on every other row, since only one runs at a time. */
  busy: boolean;
  cancelling: boolean;
  /** False for the brief window between clicking Download and useJob
   *  actually holding a job id -- Cancel can't do anything useful yet. */
  cancelReady: boolean;
  /** This row's own last download failure. Kept separate from
   *  resource.notes (a static hint from the probe, e.g. a gated-repo
   *  warning) so a transient failure and a standing note never collapse
   *  into the same colour -- the Tk original rendered both through one
   *  field named _error_label regardless of which one it actually was. */
  error: string | null;
  onDownload: () => void;
  onCancel: () => void;
  onOpenFolder: () => void;
  onOpenSourceUrl: () => void;
}

const PATH_MAX_CHARS = 64;

export function TokenizerRow({
  resource,
  downloading,
  progress,
  busy,
  cancelling,
  cancelReady,
  error,
  onDownload,
  onCancel,
  onOpenFolder,
  onOpenSourceUrl,
}: TokenizerRowProps) {
  const showLink = resource.backend === "hf" && !!resource.source_url && !!resource.notes;
  const pathText = resource.cache_path ? elideMiddle(resource.cache_path, PATH_MAX_CHARS) : "not downloaded";

  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <span
          className={cn("mt-1.5 size-2.5 shrink-0 rounded-full", resource.is_cached ? "bg-primary" : "bg-muted-foreground")}
          role="img"
          aria-label={resource.is_cached ? "Downloaded" : "Not downloaded"}
        />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="type-title text-foreground">{resource.name}</p>
            <span className="type-micro rounded-full bg-muted px-2 py-0.5 text-muted-foreground">
              {resource.backend}
            </span>
          </div>
          <p className="type-small text-muted-foreground">
            used by {fmtNum(resource.model_ids.length)} model{resource.model_ids.length !== 1 ? "s" : ""}
          </p>
          <p className="type-small truncate font-mono text-muted-foreground" title={resource.cache_path ?? undefined}>
            {pathText}
          </p>
          {resource.notes && (
            <p className="type-small mt-1 text-muted-foreground">
              {resource.notes}
              {showLink && (
                <button
                  type="button"
                  onClick={onOpenSourceUrl}
                  className="pressable ml-1.5 inline-flex items-center gap-1 rounded text-primary underline outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
                >
                  open page <ExternalLink size={11} aria-hidden="true" />
                </button>
              )}
            </p>
          )}
          {error && <p className="type-small mt-1 text-destructive">{error}</p>}
        </div>

        <p className="type-body tabular shrink-0 text-muted-foreground">{fmtBytes(resource.size_bytes)}</p>

        <div className="shrink-0">
          {resource.is_cached ? (
            <Button type="button" variant="secondary" icon={FolderOpen} onClick={onOpenFolder}>
              Open folder
            </Button>
          ) : downloading ? (
            <div className="flex items-center gap-2">
              <DownloadProgressBar progress={progress} />
              <Button
                type="button"
                variant="danger"
                icon={cancelling ? undefined : X}
                loading={cancelling}
                disabled={cancelling || !cancelReady}
                onClick={onCancel}
              >
                {cancelling ? "Cancelling…" : "Cancel"}
              </Button>
            </div>
          ) : (
            <span
              className="inline-flex"
              title={
                !resource.source_url
                  ? "No download source known for this tokenizer"
                  : busy
                    ? "Another download is already in progress"
                    : undefined
              }
            >
              <Button
                type="button"
                variant="primary"
                icon={Download}
                disabled={!resource.source_url || busy}
                onClick={onDownload}
              >
                Download
              </Button>
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}

function DownloadProgressBar({ progress }: { progress: DownloadProgress | null }) {
  const determinate = progress?.total != null;
  const pct = determinate ? Math.min(1, progress.downloaded / Math.max(progress.total ?? 1, 1)) : 0;

  return (
    <div
      role="progressbar"
      aria-valuenow={determinate ? progress.downloaded : undefined}
      aria-valuemin={0}
      aria-valuemax={determinate ? (progress.total ?? undefined) : undefined}
      className="h-1.5 w-28 overflow-hidden rounded-full bg-muted"
    >
      <div
        className={cn("h-full w-full origin-left rounded-full bg-primary", !determinate && "animate-indeterminate")}
        style={determinate ? { transform: `scaleX(${pct})`, transition: "transform var(--dur-dropdown) var(--ease-out)" } : undefined}
      />
    </div>
  );
}
