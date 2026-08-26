// Pure cost/context math, ported from core/costing.py. Recompute must be
// synchronous (no bridge round-trip) since the Calculator recomputes on
// every keystroke -- see GUI_REBUILD/05-CALCULATOR.md. Any edge-case
// behaviour here (context_window <= 0, etc.) must match the Python exactly;
// tests in costing.test.ts assert parity with tests/test_costing.py.
import type { ExchangeRates, ModelInfo } from "./types";

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

type TieredPricingFields = Pick<
  ModelInfo,
  | "long_context_threshold"
  | "long_context_input_price_per_million"
  | "long_context_output_price_per_million"
>;

/** Whether promptTokens crosses this model's long-context tier -- decided by
 *  the prompt (input) size, per every provider that offers one, not by the
 *  completion size even when pricing output. */
function longContextActive(promptTokens: number, model: TieredPricingFields): boolean {
  return (
    model.long_context_threshold !== null && promptTokens > model.long_context_threshold
  );
}

export function inputCost(
  tokens: number,
  model: Pick<ModelInfo, "input_price_per_million"> & TieredPricingFields,
): number {
  const rate =
    longContextActive(tokens, model) && model.long_context_input_price_per_million !== null
      ? model.long_context_input_price_per_million
      : model.input_price_per_million;
  return (tokens / 1_000_000) * rate;
}

/** promptTokens is the input size that decides which price tier applies.
 *  Defaults to tokens itself when omitted, which is only correct for
 *  flat-priced models (long_context_threshold null) -- callers pricing a
 *  tiered model must pass the real prompt size. */
export function outputCost(
  tokens: number,
  model: Pick<ModelInfo, "output_price_per_million"> & TieredPricingFields,
  promptTokens?: number,
): number {
  const promptSize = promptTokens ?? tokens;
  const rate =
    longContextActive(promptSize, model) &&
    model.long_context_output_price_per_million !== null
      ? model.long_context_output_price_per_million
      : model.output_price_per_million;
  return (tokens / 1_000_000) * rate;
}

export function totalCost(
  inputTokens: number,
  outputTokens: number,
  model: Pick<ModelInfo, "input_price_per_million" | "output_price_per_million"> &
    TieredPricingFields,
): number {
  return inputCost(inputTokens, model) + outputCost(outputTokens, model, inputTokens);
}

/** Convert a USD amount into toCurrency using the given rates -- mirrors
 *  core/currency.py's convert() exactly, including falling through
 *  unconverted (rate 1.0) for a currency the cache doesn't have a rate for,
 *  rather than throwing. */
export function convertCurrency(
  amountUsd: number,
  toCurrency: string,
  rates: ExchangeRates,
): number {
  const rate = rates.rates[toCurrency] ?? 1.0;
  return amountUsd * rate;
}
