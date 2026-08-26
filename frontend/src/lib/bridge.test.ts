import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { bridge, bridgeReady, BridgeError } from "./bridge";

// pywebview injects window.pywebview.api asynchronously, on its own timing
// relative to the page's own scripts. A component that calls a bridge
// method the instant it mounts can win or lose that race depending on the
// machine -- these tests pin down that every call waits it out instead of
// failing the moment the api object isn't there yet (the bug behind PR #43:
// useSettings called bridge.getSettings() directly, lost the race on some
// machines, and the resulting error was silently swallowed into a state
// nothing rendered -- an infinite loading spinner with no error on screen).

function setPywebview(api: Record<string, (...args: unknown[]) => Promise<unknown>> | undefined) {
  (globalThis as { window: unknown }).window = api ? { pywebview: { api } } : {};
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date"] });
  setPywebview(undefined);
});

afterEach(() => {
  vi.useRealTimers();
  delete (globalThis as { window?: unknown }).window;
});

describe("bridgeReady", () => {
  it("resolves once window.pywebview.api appears, even if it wasn't there yet", async () => {
    const ready = bridgeReady();
    await vi.advanceTimersByTimeAsync(100);
    setPywebview({});
    await vi.advanceTimersByTimeAsync(100);
    await expect(ready).resolves.toBeUndefined();
  });

  it("rejects if the bridge never becomes ready within the timeout", async () => {
    const ready = bridgeReady();
    ready.catch(() => {}); // fake-timer advancement below is what settles it; avoid an unhandled-rejection warning in between
    // A touch past the 10s deadline -- the poll loop checks Date.now() >
    // deadline, so landing exactly on it is one tick short of tripping.
    await vi.advanceTimersByTimeAsync(10_100);
    await expect(ready).rejects.toThrow(/did not become ready/);
  });
});

describe("bridge calls", () => {
  it("wait for a not-yet-ready bridge instead of rejecting immediately", async () => {
    const get_settings = vi.fn().mockResolvedValue({ ok: true, data: { theme: "dark" } });
    const promise = bridge.getSettings();

    // Still not ready -- must not have rejected synchronously with
    // "Python bridge is not ready" the way a naive `if (!api) throw` would.
    await vi.advanceTimersByTimeAsync(100);

    setPywebview({ get_settings });
    await vi.advanceTimersByTimeAsync(100);

    await expect(promise).resolves.toEqual({ theme: "dark" });
  });

  it("still rejects for a method the backend never exposed", async () => {
    setPywebview({});
    await expect(bridge.getSettings()).rejects.toThrow(/Unknown bridge method/);
  });

  it("surfaces a backend error via BridgeError", async () => {
    setPywebview({ get_settings: vi.fn().mockResolvedValue({ ok: false, error: "boom" }) });
    await expect(bridge.getSettings()).rejects.toThrow(BridgeError);
    await expect(bridge.getSettings()).rejects.toThrow("boom");
  });
});
