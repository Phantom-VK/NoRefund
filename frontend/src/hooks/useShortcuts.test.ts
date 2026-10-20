import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("react", () => {
  return {
    useRef: <T>(initial: T) => ({ current: initial }),
    useEffect: (fn: () => void | (() => void)) => {
      return fn();
    },
  };
});

import {
  handleShortcutEvent,
  isMac,
  useShortcuts,
} from "./useShortcuts";

describe("handleShortcutEvent", () => {
  it("handles Escape key by calling onEscape when not prevented", () => {
    const onView = vi.fn();
    const onEscape = vi.fn();
    const onHelp = vi.fn();

    handleShortcutEvent(
      { key: "Escape", defaultPrevented: false, target: null } as unknown as KeyboardEvent,
      { onView, onEscape, onHelp },
    );

    expect(onEscape).toHaveBeenCalledTimes(1);
    expect(onView).not.toHaveBeenCalled();
    expect(onHelp).not.toHaveBeenCalled();
  });

  it("does not call onEscape when defaultPrevented is true (topmost surface already handled Escape)", () => {
    const onView = vi.fn();
    const onEscape = vi.fn();
    const onHelp = vi.fn();

    handleShortcutEvent(
      { key: "Escape", defaultPrevented: true, target: null } as unknown as KeyboardEvent,
      { onView, onEscape, onHelp },
    );

    expect(onEscape).not.toHaveBeenCalled();
  });

  it("handles '?' key by calling onHelp", () => {
    const onView = vi.fn();
    const onEscape = vi.fn();
    const onHelp = vi.fn();
    const preventDefault = vi.fn();

    handleShortcutEvent(
      {
        key: "?",
        defaultPrevented: false,
        metaKey: false,
        ctrlKey: false,
        altKey: false,
        target: null,
        preventDefault,
      } as unknown as KeyboardEvent,
      { onView, onEscape, onHelp },
    );

    expect(onHelp).toHaveBeenCalledTimes(1);
    expect(preventDefault).toHaveBeenCalledTimes(1);
    expect(onView).not.toHaveBeenCalled();
  });

  it("ignores '?' when defaultPrevented is true", () => {
    const onView = vi.fn();
    const onEscape = vi.fn();
    const onHelp = vi.fn();
    const preventDefault = vi.fn();

    handleShortcutEvent(
      {
        key: "?",
        defaultPrevented: true,
        metaKey: false,
        ctrlKey: false,
        altKey: false,
        target: null,
        preventDefault,
      } as unknown as KeyboardEvent,
      { onView, onEscape, onHelp },
    );

    expect(onHelp).not.toHaveBeenCalled();
    expect(preventDefault).not.toHaveBeenCalled();
  });

  it("ignores '?' when typing inside an input or textarea or contenteditable element", () => {
    const onView = vi.fn();
    const onEscape = vi.fn();
    const onHelp = vi.fn();
    const preventDefault = vi.fn();

    const inputTarget = {
      tagName: "INPUT",
      isContentEditable: false,
    } as unknown as HTMLElement;

    handleShortcutEvent(
      {
        key: "?",
        defaultPrevented: false,
        metaKey: false,
        ctrlKey: false,
        altKey: false,
        target: inputTarget,
        preventDefault,
      } as unknown as KeyboardEvent,
      { onView, onEscape, onHelp },
    );

    expect(onHelp).not.toHaveBeenCalled();
    expect(preventDefault).not.toHaveBeenCalled();
  });

  it("switches views on modifier + number key for Mac (metaKey)", () => {
    const onView = vi.fn();
    const onEscape = vi.fn();
    const onHelp = vi.fn();
    const preventDefault = vi.fn();

    handleShortcutEvent(
      {
        key: "1",
        defaultPrevented: false,
        metaKey: true,
        ctrlKey: false,
        target: null,
        preventDefault,
      } as unknown as KeyboardEvent,
      { onView, onEscape, onHelp },
      true, // isMac
    );

    expect(onView).toHaveBeenCalledWith("calculator");
    expect(preventDefault).toHaveBeenCalledTimes(1);

    handleShortcutEvent(
      {
        key: "4",
        defaultPrevented: false,
        metaKey: true,
        ctrlKey: false,
        target: null,
        preventDefault,
      } as unknown as KeyboardEvent,
      { onView, onEscape, onHelp },
      true, // isMac
    );

    expect(onView).toHaveBeenCalledWith("fit_check");
  });

  it("switches views on modifier + number key for non-Mac (ctrlKey)", () => {
    const onView = vi.fn();
    const onEscape = vi.fn();
    const onHelp = vi.fn();
    const preventDefault = vi.fn();

    handleShortcutEvent(
      {
        key: "2",
        defaultPrevented: false,
        metaKey: false,
        ctrlKey: true,
        target: null,
        preventDefault,
      } as unknown as KeyboardEvent,
      { onView, onEscape, onHelp },
      false, // non-Mac
    );

    expect(onView).toHaveBeenCalledWith("parser");
    expect(preventDefault).toHaveBeenCalledTimes(1);
  });

  it("ignores number keys when modifier key is not pressed", () => {
    const onView = vi.fn();
    const onEscape = vi.fn();
    const preventDefault = vi.fn();

    handleShortcutEvent(
      {
        key: "1",
        defaultPrevented: false,
        metaKey: false,
        ctrlKey: false,
        target: null,
        preventDefault,
      } as unknown as KeyboardEvent,
      { onView, onEscape },
      true,
    );

    expect(onView).not.toHaveBeenCalled();
    expect(preventDefault).not.toHaveBeenCalled();
  });
});

describe("useShortcuts", () => {
  let listeners: Record<string, EventListener> = {};

  beforeEach(() => {
    listeners = {};
    (globalThis as { window: unknown }).window = {
      addEventListener: vi.fn((event: string, handler: EventListener) => {
        listeners[event] = handler;
      }),
      removeEventListener: vi.fn((event: string) => {
        delete listeners[event];
      }),
    };
  });

  afterEach(() => {
    delete (globalThis as { window?: unknown }).window;
  });

  it("exports useShortcuts and isMac", () => {
    expect(typeof useShortcuts).toBe("function");
    expect(typeof isMac).toBe("boolean");
  });

  it("registers keydown listener and closes only the topmost surface on Escape", () => {
    const onEscape = vi.fn();
    const onView = vi.fn();

    useShortcuts({ onView, onEscape });

    expect((window.addEventListener as unknown as ReturnType<typeof vi.fn>)).toHaveBeenCalledWith(
      "keydown",
      expect.any(Function),
    );

    const onKeyDown = listeners["keydown"];
    expect(onKeyDown).toBeDefined();

    // 1. Topmost surface (e.g. nested dropdown or modal) already handled Escape
    // so it set defaultPrevented = true. onEscape must NOT be called.
    onKeyDown({
      key: "Escape",
      defaultPrevented: true,
      target: null,
    } as unknown as KeyboardEvent);

    expect(onEscape).not.toHaveBeenCalled();

    // 2. Unhandled Escape (no topmost surface consumed it): onEscape IS called.
    onKeyDown({
      key: "Escape",
      defaultPrevented: false,
      target: null,
    } as unknown as KeyboardEvent);

    expect(onEscape).toHaveBeenCalledTimes(1);
  });

  it("does not trigger onHelp if '?' was already handled by an inner surface", () => {
    const onHelp = vi.fn();
    const preventDefault = vi.fn();

    useShortcuts({ onView: vi.fn(), onEscape: vi.fn(), onHelp });

    const onKeyDown = listeners["keydown"];
    onKeyDown({
      key: "?",
      defaultPrevented: true,
      metaKey: false,
      ctrlKey: false,
      altKey: false,
      target: null,
      preventDefault,
    } as unknown as KeyboardEvent);

    expect(onHelp).not.toHaveBeenCalled();
    expect(preventDefault).not.toHaveBeenCalled();
  });
});
