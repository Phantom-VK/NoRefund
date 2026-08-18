// Pure cost/context math, ported from core/costing.py. Recompute must be
// synchronous (no bridge round-trip) since the Calculator recomputes on
// every keystroke -- see GUI_REBUILD/05-CALCULATOR.md. Any edge-case
// behaviour here (context_window <= 0, etc.) must match the Python exactly;
// tests in costing.test.ts assert parity with tests/test_costing.py.
import type { ModelInfo } from "./types";

// Tokens reserved for model output within the context window when chunking.
const RESERVED_OUTPUT = 1_024;

/** Percentage of the context window used, rounded to 2dp. `null` (not 0)
 *  when the window is zero or negative, so callers show "—" rather than a
 *  misleading 0%. */
export function contextUsagePct(tokens: number, window: number): number | null {
  if (window <= 0) return null;
  return Math.round((tokens / window) * 100 * 100) / 100;
}

export function fitsInContext(tokens: number, window: number): boolean {
  if (window <= 0) return false;
  return tokens <= window;
}

/** Minimum API calls needed to process the full document. */
export function minChunks(tokens: number, window: number): number {
  if (window <= 0) return 0;
  const usable = Math.max(window - RESERVED_OUTPUT, 1);
  return Math.ceil(tokens / usable);
}

export function inputCost(
  tokens: number,
  model: Pick<ModelInfo, "input_price_per_million">,
): number {
  return (tokens / 1_000_000) * model.input_price_per_million;
}

export function outputCost(
  tokens: number,
  model: Pick<ModelInfo, "output_price_per_million">,
): number {
  return (tokens / 1_000_000) * model.output_price_per_million;
}

export function totalCost(
  inputTokens: number,
  outputTokens: number,
  model: Pick<ModelInfo, "input_price_per_million" | "output_price_per_million">,
): number {
  return inputCost(inputTokens, model) + outputCost(outputTokens, model);
}
