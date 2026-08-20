import { FileText, FolderOpen, X, Zap } from "lucide-react";
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
  // A drop here replaces the current selection, matching Pick File/Pick
  // Folder -- Compare tokenizes one input at a time, unlike Parser's
  // accumulating file list.
  const { dropping, bind } = useFileDrop({ onPaths, extensions: SUPPORTED_EXTENSIONS });

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
        className="type-small w-full resize-none rounded-md border border-input bg-input-background px-3 py-2 font-mono outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
      />

      <div className="mt-2 flex gap-2">
        <Button type="button" variant="secondary" icon={FileText} onClick={onPickFile}>
          Pick File
        </Button>
        <Button type="button" variant="secondary" icon={FolderOpen} onClick={onPickFolder}>
          Pick Folder
        </Button>
      </div>

      {paths.length > 0 && (
        <ul className="mt-2 flex flex-col gap-0.5">
          {paths.map((p) => (
            <li key={p} className="type-small truncate font-mono text-foreground">
              {basename(p)}
            </li>
          ))}
        </ul>
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
