import { FilePlus, FolderPlus, X, Zap } from "lucide-react";
import { Button } from "@/components/app/Button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ModelSelect } from "@/components/app/ModelSelect";
import type { ModelInfo } from "@/lib/types";

export interface ToolbarProps {
  onAddFiles: () => void;
  onAddFolder: () => void;
  onClear: () => void;
  clearDisabled: boolean;
  models: ModelInfo[];
  modelId: string;
  onModelChange: (m: ModelInfo) => void;
  outputRaw: string;
  onOutputChange: (v: string) => void;
  analyzing: boolean;
  cancelling: boolean;
  analyzeDisabled: boolean;
  onAnalyze: () => void;
  onCancel: () => void;
}

export function Toolbar({
  onAddFiles,
  onAddFolder,
  onClear,
  clearDisabled,
  models,
  modelId,
  onModelChange,
  outputRaw,
  onOutputChange,
  analyzing,
  cancelling,
  analyzeDisabled,
  onAnalyze,
  onCancel,
}: ToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 bg-card px-3 py-2">
      <Button type="button" variant="secondary" icon={FilePlus} onClick={onAddFiles}>
        Add File
      </Button>
      <Button type="button" variant="secondary" icon={FolderPlus} onClick={onAddFolder}>
        Add Folder
      </Button>
      <Button
        type="button"
        variant="danger"
        icon={X}
        disabled={clearDisabled}
        onClick={onClear}
      >
        Clear
      </Button>

      <div className="mx-1 h-6 w-px bg-border" />

      <ModelSelect
        models={models}
        value={modelId}
        onChange={onModelChange}
        className="w-56"
        id="parser-model"
      />

      <div className="flex items-center gap-2">
        <Label htmlFor="parser-output-tokens" className="text-muted-foreground">
          Est. output:
        </Label>
        <Input
          id="parser-output-tokens"
          value={outputRaw}
          onChange={(e) => onOutputChange(e.target.value)}
          inputMode="numeric"
          className="tabular w-24 font-mono"
        />
      </div>

      {analyzing ? (
        <Button
          type="button"
          variant="danger"
          icon={cancelling ? undefined : X}
          loading={cancelling}
          disabled={cancelling}
          onClick={onCancel}
          className="ml-auto"
        >
          {cancelling ? "Cancelling…" : "Cancel"}
        </Button>
      ) : (
        <Button
          type="button"
          variant="primary"
          icon={Zap}
          disabled={analyzeDisabled}
          onClick={onAnalyze}
          className="ml-auto"
        >
          Analyze
        </Button>
      )}
    </div>
  );
}
