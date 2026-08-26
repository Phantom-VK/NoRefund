"""Tests for pure costing functions."""

from norefund.core.costing import (
    context_usage_pct,
    fits_in_context,
    input_cost,
    min_chunks,
    output_cost,
    total_cost,
)
from norefund.core.models_registry import ModelInfo

# Reusable dummy model for cost tests
_MODEL = ModelInfo(
    id="test:model",
    display_name="Test Model",
    provider="Test",
    tokenizer_backend="tiktoken",
    tokenizer_name="cl100k_base",
    context_window=128_000,
    input_price_per_million=2.0,
    output_price_per_million=8.0,
)


def test_context_usage_pct_half():
    assert context_usage_pct(64_000, 128_000) == 50.0


def test_context_usage_pct_over_100():
    assert context_usage_pct(200_000, 128_000) > 100


def test_context_usage_pct_precision():
    assert context_usage_pct(1000, 128_000) == round(1000 / 128_000 * 100, 2)


def test_fits_in_context_true():
    assert fits_in_context(1000, 128_000) is True


def test_fits_in_context_exact_limit():
    assert fits_in_context(128_000, 128_000) is True


def test_fits_in_context_false():
    assert fits_in_context(128_001, 128_000) is False


def test_min_chunks_single():
    assert min_chunks(1000, 128_000) == 1


def test_min_chunks_multiple():
    # 500k tokens, 128k window (minus 1024 reserved) = needs multiple calls
    result = min_chunks(500_000, 128_000)
    assert result > 1


def test_input_cost_zero_for_free_model():
    free_model = ModelInfo(
        id="meta:llama-3-8b",
        display_name="Llama",
        provider="Meta",
        tokenizer_backend="tiktoken",
        tokenizer_name="cl100k_base",
        context_window=8192,
        input_price_per_million=0.0,
        output_price_per_million=0.0,
    )
    assert input_cost(100_000, free_model) == 0.0


def test_input_cost_calculation():
    # 1M tokens at $2.0/M = $2.0
    assert input_cost(1_000_000, _MODEL) == 2.0


def test_output_cost_calculation():
    # 1M tokens at $8.0/M = $8.0
    assert output_cost(1_000_000, _MODEL) == 8.0


def test_total_cost_sum():
    cost = total_cost(1_000_000, 1_000_000, _MODEL)
    assert cost == 10.0  # $2.0 input + $8.0 output


_TIERED_MODEL = ModelInfo(
    id="test:tiered-model",
    display_name="Test Tiered Model",
    provider="Test",
    tokenizer_backend="tiktoken",
    tokenizer_name="cl100k_base",
    context_window=1_000_000,
    input_price_per_million=2.0,
    output_price_per_million=8.0,
    long_context_threshold=200_000,
    long_context_input_price_per_million=4.0,
    long_context_output_price_per_million=16.0,
)


def test_input_cost_at_threshold_uses_short_rate():
    # Boundary is "above the threshold", not "at or above" -- exactly
    # long_context_threshold tokens still bills at the short-context rate.
    assert input_cost(200_000, _TIERED_MODEL) == (200_000 / 1_000_000) * 2.0


def test_input_cost_below_threshold_uses_short_rate():
    assert input_cost(199_999, _TIERED_MODEL) == (199_999 / 1_000_000) * 2.0


def test_input_cost_above_threshold_uses_long_rate():
    assert input_cost(200_001, _TIERED_MODEL) == (200_001 / 1_000_000) * 4.0


def test_output_cost_tier_follows_prompt_size_not_output_size():
    # A short prompt with a huge completion stays on the short-context
    # output rate -- the tier is decided by the prompt, not the output.
    cost = output_cost(500_000, _TIERED_MODEL, prompt_token_count=1_000)
    assert cost == (500_000 / 1_000_000) * 8.0


def test_output_cost_above_threshold_uses_long_rate():
    cost = output_cost(1_000, _TIERED_MODEL, prompt_token_count=200_001)
    assert cost == (1_000 / 1_000_000) * 16.0


def test_output_cost_defaults_prompt_size_to_own_token_count():
    # No prompt_token_count given: falls back to the output's own count.
    # Only correct for flat models, but must not crash for a tiered one.
    cost = output_cost(200_001, _TIERED_MODEL)
    assert cost == (200_001 / 1_000_000) * 16.0


def test_total_cost_tiers_output_by_input_size():
    # 300k input (above threshold) + 1k output must bill output at the
    # long-context rate, driven by the input size, not the output size.
    cost = total_cost(300_000, 1_000, _TIERED_MODEL)
    expected = (300_000 / 1_000_000) * 4.0 + (1_000 / 1_000_000) * 16.0
    assert cost == expected


def test_flat_model_ignores_missing_tier_fields():
    # _MODEL has no long_context_threshold -- tiering must be a no-op.
    assert input_cost(10_000_000, _MODEL) == (10_000_000 / 1_000_000) * 2.0
