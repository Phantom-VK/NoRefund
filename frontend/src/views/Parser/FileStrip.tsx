import { File, Folder, X } from "lucide-react";
import { hasSupportedExtension } from "@/lib/parsing";
import { basename } from "@/lib/format";
import { cn } from "@/lib/cn";

export interface FileStripProps {
  paths: string[];
  onRemove: (path: string) => void;
  dropping: boolean;
}

export function FileStrip({ paths, onRemove, dropping }: FileStripProps) {
  return (
    <div
      className={cn(
        "h-[132px] shrink-0 overflow-y-auto rounded-md border border-dashed px-3 py-2 transition-colors",
        dropping ? "border-primary bg-primary/5" : "border-transparent",
      )}
    >
      {paths.length === 0 ? (
        <p className="type-body flex h-full items-center justify-center text-center text-muted-foreground">
          No files selected. Click &apos;Add File&apos; or &apos;Add Folder&apos; to get
          started.
        </p>
      ) : (
        <ul className="flex flex-col gap-0.5">
          {paths.map((path) => {
            const Icon = hasSupportedExtension(path) ? File : Folder;
            return (
              <li
                key={path}
                className="flex items-center gap-2 rounded px-1 py-0.5 hover:bg-muted"
              >
                <Icon
                  size={14}
                  className="shrink-0 text-muted-foreground"
                  aria-hidden="true"
                />
                <span className="type-small flex-1 truncate font-mono">{path}</span>
                <button
                  type="button"
                  onClick={() => onRemove(path)}
                  aria-label={`Remove ${basename(path)}`}
                  className="pressable shrink-0 text-muted-foreground hover:text-foreground"
                >
                  <X size={12} aria-hidden="true" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
