import { useCallback, useRef, useState } from "react";
import type { DragEvent, HTMLAttributes } from "react";

export interface UseFileDropOptions {
  onPaths: (paths: string[]) => void;
  extensions: string[];
  /** No-ops every handler, including skipping dragover's preventDefault
   *  (so the browser shows its own "not a drop target" cursor instead of
   *  the highlight lighting up for a drop that will be silently discarded). */
  disabled?: boolean;
}

export interface UseFileDropResult {
  dropping: boolean;
  bind: HTMLAttributes<HTMLElement>;
}

function hasExtension(name: string, extensions: string[]): boolean {
  const lower = name.toLowerCase();
  return extensions.some((ext) => lower.endsWith(ext.toLowerCase()));
}

/** pywebview's desktop webviews attach the real filesystem path to each
 *  dropped File as `.path` (non-standard, Electron/CEF-style) -- this is
 *  what makes drag-and-drop usable for a desktop app at all, since the
 *  standard File API never exposes a path in a browser. Verify per-platform
 *  in Phase 12 per the plan; falls back to doing nothing where `.path` is
 *  absent (a plain browser during dev) rather than guessing. */
export function useFileDrop({
  onPaths,
  extensions,
  disabled = false,
}: UseFileDropOptions): UseFileDropResult {
  const [dropping, setDropping] = useState(false);
  const dragDepth = useRef(0);

  const onDragOver = useCallback(
    (e: DragEvent) => {
      if (disabled) return;
      e.preventDefault();
    },
    [disabled],
  );

  const onDragEnter = useCallback(
    (e: DragEvent) => {
      if (disabled) return;
      e.preventDefault();
      dragDepth.current += 1;
      setDropping(true);
    },
    [disabled],
  );

  const onDragLeave = useCallback(
    (e: DragEvent) => {
      if (disabled) return;
      e.preventDefault();
      dragDepth.current = Math.max(0, dragDepth.current - 1);
      if (dragDepth.current === 0) setDropping(false);
    },
    [disabled],
  );

  const onDrop = useCallback(
    (e: DragEvent) => {
      if (disabled) return;
      e.preventDefault();
      dragDepth.current = 0;
      setDropping(false);

      const paths: string[] = [];
      const items = e.dataTransfer.items;

      // dataTransfer.items and dataTransfer.files are NOT guaranteed to be
      // index-aligned -- a drag that also carries a text/uri-list or
      // text/plain representation (common from real file managers, e.g.
      // GNOME Nautilus) adds non-file entries into `items` that `files`
      // silently filters out, shifting every index after it. Read file and
      // entry off the *same* item instead of correlating two lists by i.
      if (items) {
        Array.from(items).forEach((item) => {
          if (item.kind !== "file") return;
          const file = item.getAsFile();
          const path = (file as unknown as { path?: string } | null)?.path;
          if (!file || !path) return;
          // webkitGetAsEntry is how a Chromium/WebKit-based webview (every
          // pywebview desktop backend) tells a dropped directory apart from
          // a file -- the standard File object gives no such signal alone.
          const entry = item.webkitGetAsEntry?.();
          const isDirectory = entry?.isDirectory ?? false;
          if (isDirectory || hasExtension(file.name, extensions)) {
            paths.push(path);
          }
        });
      } else {
        // Fallback for a plain browser dev environment where `.path` is
        // absent anyway, so directory detection wouldn't matter.
        Array.from(e.dataTransfer.files).forEach((file) => {
          const path = (file as unknown as { path?: string }).path;
          if (path && hasExtension(file.name, extensions)) paths.push(path);
        });
      }

      if (paths.length > 0) onPaths(paths);
    },
    [disabled, extensions, onPaths],
  );

  return { dropping, bind: { onDragOver, onDragEnter, onDragLeave, onDrop } };
}
