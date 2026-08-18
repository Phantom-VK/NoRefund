import { useEffect, useRef } from "react";
import type { ViewId } from "@/lib/views";

const SHORTCUT_VIEWS: Record<string, ViewId> = {
  "1": "calculator",
  "2": "parser",
  "3": "compare",
  "4": "fit_check",
  "5": "registry",
  "6": "resources",
};

const isMac = navigator.platform.toLowerCase().includes("mac");

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  return target.tagName === "INPUT" || target.tagName === "TEXTAREA";
}

/** Registered once on window for the app's lifetime; the latest handlers
 *  are read through a ref so callers can pass fresh closures every render
 *  without re-subscribing the listener. */
export function useShortcuts(handlers: {
  onView: (v: ViewId) => void;
  onEscape: () => void;
}): void {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        handlersRef.current.onEscape();
        return;
      }
      if (isTypingTarget(e.target)) return;
      const modifierPressed = isMac ? e.metaKey : e.ctrlKey;
      if (!modifierPressed) return;
      const view = SHORTCUT_VIEWS[e.key];
      if (view) {
        e.preventDefault();
        handlersRef.current.onView(view);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);
}
