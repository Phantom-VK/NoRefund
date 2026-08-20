import { FolderOpen } from "lucide-react";
import { Button } from "@/components/app/Button";
import { Card } from "@/components/app/Card";
import { elideMiddle, fmtBytes } from "@/lib/format";
import type { ManagedDir } from "@/lib/types";

const PATH_MAX_CHARS = 64;

export interface StorageRowProps {
  dir: ManagedDir;
  onOpenFolder: () => void;
}

export function StorageRow({ dir, onOpenFolder }: StorageRowProps) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <p className="type-label font-bold text-foreground">{dir.label}</p>
          <p className="type-small truncate font-mono text-muted-foreground" title={dir.path}>
            {elideMiddle(dir.path, PATH_MAX_CHARS)}
          </p>
        </div>
        <p className="type-body tabular shrink-0 text-muted-foreground">
          {fmtBytes(dir.size_bytes)} · {dir.file_count} file{dir.file_count !== 1 ? "s" : ""}
        </p>
        <span className="inline-flex shrink-0" title={!dir.exists ? "This folder doesn't exist yet" : undefined}>
          <Button type="button" variant="secondary" icon={FolderOpen} disabled={!dir.exists} onClick={onOpenFolder}>
            Open folder
          </Button>
        </span>
      </div>
    </Card>
  );
}
