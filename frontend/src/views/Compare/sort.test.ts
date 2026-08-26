import { describe, expect, it } from "vitest";
import { cheapestResult, sortProjections, sortResults } from "./sort";
import type { ModelComparison, ModelInfo, PortfolioProjection } from "@/lib/types";

function model(id: string): ModelInfo {
  return {
    id,
    display_name: id,
    provider: "Test",
    tokenizer_backend: "tiktoken",
    tokenizer_name: "cl100k_base",
    context_window: 8192,
    input_price_per_million: 1,
    output_price_per_million: 2,
    currency: "USD",
    docs_url: null,
    tokenizer_is_approximate: false,
    long_context_threshold: null,
    long_context_input_price_per_million: null,
    long_context_output_price_per_million: null,
    pricing_note: null,
    pricing_verified_on: null,
  };
}

function result(id: string, totalCost: number, error: string | null = null): ModelComparison {
  return {
    model: model(id),
    token_count: 100,
    context_usage_pct: 1.2,
    fits_in_context: true,
    min_chunks_needed: 1,
    output_tokens: 500,
    input_cost: totalCost / 2,
    output_cost: totalCost / 2,
    total_cost: totalCost,
    tokenizer_is_approximate: false,
    error,
  };
}

function projection(id: string, monthlyCost: number, fits: boolean): PortfolioProjection {
  return {
    model: model(id),
    corpus_tokens: 100,
    fits_in_context: fits,
    cost_per_run: monthlyCost / 30,
    monthly_cost: monthlyCost,
    annual_cost: monthlyCost * 12,
  };
}

describe("sortResults", () => {
  it("sorts by ascending total cost", () => {
    const sorted = sortResults([result("b", 5), result("a", 1), result("c", 3)]);
    expect(sorted.map((r) => r.model.id)).toEqual(["a", "c", "b"]);
  });

  it("puts errored models last regardless of cost", () => {
    const sorted = sortResults([
      result("cheap-error", 0, "Tokenizer unavailable"),
      result("expensive-ok", 99),
    ]);
    expect(sorted.map((r) => r.model.id)).toEqual(["expensive-ok", "cheap-error"]);
  });

  it("does not mutate the input array", () => {
    const input = [result("b", 5), result("a", 1)];
    const original = [...input];
    sortResults(input);
    expect(input).toEqual(original);
  });
});

describe("cheapestResult", () => {
  it("picks the cheapest successful model", () => {
    const cheapest = cheapestResult([result("b", 5), result("a", 1), result("c", 3)]);
    expect(cheapest?.model.id).toBe("a");
  });

  it("ignores errored models even if cheaper", () => {
    const cheapest = cheapestResult([
      result("cheap-error", 0, "Tokenizer unavailable"),
      result("expensive-ok", 99),
    ]);
    expect(cheapest?.model.id).toBe("expensive-ok");
  });

  it("returns null when every model errored", () => {
    expect(cheapestResult([result("a", 0, "boom"), result("b", 0, "boom")])).toBeNull();
  });
});

describe("sortProjections", () => {
  it("puts fitting models before non-fitting ones regardless of cost", () => {
    const sorted = sortProjections([
      projection("cheap-no-fit", 1, false),
      projection("pricier-fits", 50, true),
    ]);
    expect(sorted.map((p) => p.model.id)).toEqual(["pricier-fits", "cheap-no-fit"]);
  });

  it("sorts fitting models by ascending monthly cost", () => {
    const sorted = sortProjections([
      projection("b", 30, true),
      projection("a", 10, true),
      projection("c", 20, true),
    ]);
    expect(sorted.map((p) => p.model.id)).toEqual(["a", "c", "b"]);
  });
});
