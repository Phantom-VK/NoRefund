import { FileText, FolderOpen, X, XCircle, Zap } from "lucide-react";
import { Button } from "@/components/app/Button";
import { Card } from "@/components/app/Card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useFileDrop } from "@/hooks/useFileDrop";
import { basename } from "@/lib/format";
import { SUPPORTED_EXTENSIONS } from "@/lib/parsing";
import { cn } from "@/lib/cn";

export interface InputCardProps {
  text: string;
  onTextChange: (text: string) => void;
  paths: string[];
  onPaths: (paths: string[]) => void;
  onClearPaths: () => void;
  onPickFile: () => void;
  onPickFolder: () => void;
  outputTokens: string;
  onOutputTokensChange: (value: string) => void;
  outputTokensValid: boolean;
  running: boolean;
  cancelling: boolean;
  onRun: () => void;
  onCancel: () => void;
  /** Why Compare is disabled, shown as a title/tooltip -- never silently
   *  inert (GUI_REVIEW.md §4.3). Null means it's enabled. */
  runDisabledReason: string | null;
}

export function InputCard({
  text,
  onTextChange,
  paths,
  onPaths,
  onClearPaths,
  onPickFile,
  onPickFolder,
  outputTokens,
  onOutputTokensChange,
  outputTokensValid,
  running,
  cancelling,
  onRun,
  onCancel,
  runDisabledReason,
}: InputCardProps) {
  // Only one input source at a time: picking/dropping files disables the
  // textarea, and typed text disables file picking -- clearing whichever
  // one is active hands control back to the other.
  const hasFiles = paths.length > 0;
  const hasText = text.trim().length > 0;
  const textDisabled = running || hasFiles;
  const filesDisabled = running || hasText;

  // A drop here replaces the current selection, matching Pick File/Pick
  // Folder -- Compare tokenizes one input at a time, unlike Parser's
  // accumulating file list. Guarded the same as the pick buttons, since a
  // drop bypasses their disabled state.
  const { dropping, bind } = useFileDrop({
    onPaths: (p) => {
      if (!filesDisabled) onPaths(p);
    },
    extensions: SUPPORTED_EXTENSIONS,
  });

  return (
    <Card
      {...bind}
      className={cn(
        "p-4 transition-colors",
        dropping && "ring-2 ring-primary ring-offset-2 ring-offset-background",
      )}
    >
      <p className="type-label mb-2 text-foreground">Input</p>
      <textarea
        value={text}
        onChange={(e) => onTextChange(e.target.value)}
        placeholder="Paste text to compare…"
        rows={6}
        disabled={textDisabled}
        title={hasFiles ? "Clear the selected files first to paste text instead" : undefined}
        className="type-small w-full resize-none rounded-md border border-input bg-input-background px-3 py-2 font-mono outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
      />

      <div className="mt-2 flex gap-2">
        <Button
          type="button"
          variant="secondary"
          icon={FileText}
          disabled={filesDisabled}
          title={hasText ? "Clear the pasted text first to pick files instead" : undefined}
          onClick={onPickFile}
        >
          Pick File
        </Button>
        <Button
          type="button"
          variant="secondary"
          icon={FolderOpen}
          disabled={filesDisabled}
          title={hasText ? "Clear the pasted text first to pick files instead" : undefined}
          onClick={onPickFolder}
        >
          Pick Folder
        </Button>
      </div>

      {hasFiles && (
        <div className="mt-2">
          <div className="mb-1 flex items-center justify-between">
            <p className="type-small text-muted-foreground">Selected</p>
            <button
              type="button"
              disabled={running}
              onClick={onClearPaths}
              className="pressable type-small flex items-center gap-1 text-primary disabled:pointer-events-none disabled:opacity-50"
            >
              <XCircle size={12} aria-hidden="true" />
              Clear
            </button>
          </div>
          <ul className="flex flex-col gap-0.5">
            {paths.map((p) => (
              <li key={p} className="type-small truncate font-mono text-foreground">
                {basename(p)}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-3 flex items-center gap-2">
        <Label htmlFor="compare-output-tokens" className="type-small shrink-0 text-muted-foreground">
          Est. output tokens
        </Label>
        <Input
          id="compare-output-tokens"
          value={outputTokens}
          onChange={(e) => onOutputTokensChange(e.target.value)}
          aria-invalid={!outputTokensValid}
          className="w-24 font-mono"
        />
      </div>

      {running ? (
        <Button
          type="button"
          variant="danger"
          icon={cancelling ? undefined : X}
          loading={cancelling}
          disabled={cancelling}
          onClick={onCancel}
          className="mt-3 w-full"
        >
          {cancelling ? "Cancelling…" : "Cancel"}
        </Button>
      ) : (
        <Button
          type="button"
          variant="primary"
          icon={Zap}
          disabled={runDisabledReason !== null}
          title={runDisabledReason ?? undefined}
          onClick={onRun}
          className="mt-3 w-full"
        >
          Compare
        </Button>
      )}
    </Card>
  );
}
