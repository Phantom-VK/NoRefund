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
