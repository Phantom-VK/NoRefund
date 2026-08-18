import type { ModelInfo } from "./types";

export function fmtNum(n: number): string {
  return n.toLocaleString("en-US");
}

export function fmtFloat(v: number | null, decimals = 1): string {
  if (v === null) return "—";
  return v.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function fmtCost(v: number): string {
  if (v < 0.01) return `$${v.toFixed(6)}`;
  return `$${v.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function fmtContextPct(pct: number | null): string {
  return pct === null ? "—" : `${pct.toFixed(1)}%`;
}

export function fmtContextWindow(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M tokens`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K tokens`;
  return `${n} tokens`;
}

export function fmtBytes(n: number | null): string {
  if (n === null) return "—";
  let value = n;
  const units = ["B", "KB", "MB", "GB"] as const;
  for (const unit of units) {
    if (value < 1024 || unit === "GB") {
      return unit === "B" ? `${Math.round(value)} B` : `${value.toFixed(1)} ${unit}`;
    }
    value /= 1024;
  }
  return `${value.toFixed(1)} GB`;
}

/** null means "not a usable number" — callers must show an error, not fall
 *  back to 0. The Python original silently defaulted, which hid bad input. */
export function parseIntSafe(value: string): number | null {
  const cleaned = value.replace(/,/g, "").trim();
  if (cleaned === "") return null;
  if (!/^\d+$/.test(cleaned)) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

export function elideMiddle(text: string, maxChars: number): string {
  if (text.length <= maxChars || maxChars <= 1) return text;
  const tail = Math.max(1, Math.floor(maxChars / 3));
  const head = maxChars - tail - 1;
  return `${text.slice(0, head)}…${text.slice(-tail)}`;
}

export function modelLabel(m: ModelInfo): string {
  const base = `${m.display_name}  ·  ${m.provider}`;
  return m.tokenizer_is_approximate ? `${base}  (approx.)` : base;
}

export type ContextLevel = "ok" | "warn" | "over";

export function contextLevel(pct: number | null): ContextLevel {
  if (pct === null || pct < 75) return "ok";
  if (pct < 100) return "warn";
  return "over";
}
