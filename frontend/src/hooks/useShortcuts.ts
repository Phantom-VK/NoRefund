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

export const isMac =
  typeof navigator !== "undefined"
    ? navigator.platform.toLowerCase().includes("mac")
    : false;

function isTypingTarget(target: EventTarget | null): boolean {
  if (!target) return false;
  if (typeof HTMLElement !== "undefined" && !(target instanceof HTMLElement)) return false;
  const el = target as { isContentEditable?: boolean; tagName?: string };
  if (el.isContentEditable) return true;
  return el.tagName === "INPUT" || el.tagName === "TEXTAREA";
}

export interface ShortcutHandlers {
  onView: (v: ViewId) => void;
  onEscape: () => void;
  onHelp?: () => void;
}

export function handleShortcutEvent(
  e: KeyboardEvent,
  handlers: ShortcutHandlers,
  mac = isMac,
): void {
  if (e.defaultPrevented) return;
  if (e.key === "Escape") {
    handlers.onEscape();
    return;
  }
  if (isTypingTarget(e.target)) return;
  if (e.key === "?" && !e.metaKey && !e.ctrlKey && !e.altKey) {
    e.preventDefault();
    handlers.onHelp?.();
    return;
  }
  const modifierPressed = mac ? e.metaKey : e.ctrlKey;
  if (!modifierPressed) return;
  const view = SHORTCUT_VIEWS[e.key];
  if (view) {
    e.preventDefault();
    handlers.onView(view);
  }
}

/** Registered once on window for the app's lifetime; the latest handlers
 *  are read through a ref so callers can pass fresh closures every render
 *  without re-subscribing the listener. */
export function useShortcuts(handlers: ShortcutHandlers): void {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      handleShortcutEvent(e, handlersRef.current, isMac);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);
}
