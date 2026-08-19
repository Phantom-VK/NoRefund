import { useCallback, useRef, useState } from "react";
import type { DragEvent, HTMLAttributes } from "react";

export interface UseFileDropOptions {
  onPaths: (paths: string[]) => void;
  extensions: string[];
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
export function useFileDrop({ onPaths, extensions }: UseFileDropOptions): UseFileDropResult {
  const [dropping, setDropping] = useState(false);
  const dragDepth = useRef(0);

  const onDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
  }, []);

  const onDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault();
    dragDepth.current += 1;
    setDropping(true);
  }, []);

  const onDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) setDropping(false);
  }, []);

  const onDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      dragDepth.current = 0;
      setDropping(false);

      const items = e.dataTransfer.items;
      const paths: string[] = [];

      Array.from(e.dataTransfer.files).forEach((file, i) => {
        const path = (file as unknown as { path?: string }).path;
        if (!path) return;
        // webkitGetAsEntry is how a Chromium-based webview (every pywebview
        // desktop backend) tells a dropped directory apart from a file --
        // the standard File object gives no such signal on its own.
        const entry = items?.[i]?.webkitGetAsEntry?.();
        const isDirectory = entry?.isDirectory ?? false;
        if (isDirectory || hasExtension(file.name, extensions)) {
          paths.push(path);
        }
      });

      if (paths.length > 0) onPaths(paths);
    },
    [extensions, onPaths],
  );

  return { dropping, bind: { onDragOver, onDragEnter, onDragLeave, onDrop } };
}
