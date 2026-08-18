import { describe, expect, it } from "vitest";
import {
  contextUsagePct,
  convertCurrency,
  fitsInContext,
  inputCost,
  minChunks,
  outputCost,
  totalCost,
} from "./costing";

// Mirrors tests/test_costing.py's _MODEL.
const MODEL = { input_price_per_million: 2.0, output_price_per_million: 8.0 };

describe("contextUsagePct", () => {
  it("is null when the window is zero", () => {
    expect(contextUsagePct(100, 0)).toBeNull();
  });
  it("is null when the window is negative", () => {
    expect(contextUsagePct(100, -1)).toBeNull();
  });
  it("is a percentage of the window", () => {
    expect(contextUsagePct(64_000, 128_000)).toBe(50);
  });
  it("can exceed 100", () => {
    expect(contextUsagePct(256_000, 128_000)).toBeGreaterThan(100);
  });
  it("rounds to 2dp", () => {
    expect(contextUsagePct(1000, 128_000)).toBe(
      Math.round((1000 / 128_000) * 100 * 100) / 100,
    );
  });
});

describe("fitsInContext", () => {
  it("is true under the window", () => expect(fitsInContext(1000, 128_000)).toBe(true));
  it("is true exactly at the window", () =>
    expect(fitsInContext(128_000, 128_000)).toBe(true));
  it("is false over the window", () =>
    expect(fitsInContext(128_001, 128_000)).toBe(false));
  it("is false when the window is zero or negative", () => {
    expect(fitsInContext(0, 0)).toBe(false);
    expect(fitsInContext(10, -1)).toBe(false);
  });
});

describe("minChunks", () => {
  // 1024 tokens are reserved for output within the window (matching
  // core/costing.py's RESERVED_OUTPUT), so the usable size for chunking
  // math is window - 1024, not the raw window -- these cases use a window
  // large enough for that reservation not to swamp the arithmetic.
  it("is 0 for no tokens", () => expect(minChunks(0, 100_000)).toBe(0));
  it("is 1 when it fits exactly", () => expect(minChunks(98_976, 100_000)).toBe(1));
  it("rounds up", () => expect(minChunks(98_977, 100_000)).toBe(2));
  it("is 0 when the window is zero", () => expect(minChunks(10, 0)).toBe(0));
  it("needs multiple chunks for a large corpus", () => {
    expect(minChunks(500_000, 128_000)).toBeGreaterThan(1);
  });
});

describe("inputCost / outputCost / totalCost", () => {
  it("prices per million tokens", () => {
    expect(inputCost(1_000_000, MODEL)).toBeCloseTo(2.0);
    expect(outputCost(1_000_000, MODEL)).toBeCloseTo(8.0);
  });
  it("is zero for a free model", () => {
    const free = { input_price_per_million: 0, output_price_per_million: 0 };
    expect(inputCost(100_000, free)).toBe(0);
  });
  it("sums input and output", () => {
    expect(totalCost(1_000_000, 1_000_000, MODEL)).toBeCloseTo(10.0);
  });
});

describe("convertCurrency", () => {
  it("applies the rate for the target currency", () => {
    const rates = { base: "USD", rates: { EUR: 0.5 }, fetched_at: null };
    expect(convertCurrency(10, "EUR", rates)).toBe(5);
  });
  it("is the identity for USD", () => {
    const rates = { base: "USD", rates: { USD: 1.0, EUR: 0.5 }, fetched_at: null };
    expect(convertCurrency(10, "USD", rates)).toBe(10);
  });
  it("falls through unconverted for a currency missing from the cache", () => {
    const rates = { base: "USD", rates: { EUR: 0.5 }, fetched_at: null };
    expect(convertCurrency(10, "JPY", rates)).toBe(10);
  });
});
