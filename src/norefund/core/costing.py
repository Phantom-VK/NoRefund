"""Pure cost and context-window calculations."""

from __future__ import annotations

import math

from norefund.core.models_registry import ModelInfo

# Tokens reserved for model output within the context window when chunking
_RESERVED_OUTPUT = 1_024


def context_usage_pct(token_count: int, context_window: int) -> float | None:
    """Return percentage of context window used (rounded to 2 dp).

    Returns None (not 0) when context_window is zero or negative so the
    caller/GUI can display '—' rather than a misleading 0 %.
    """
    if context_window <= 0:
        return None
    return round(token_count / context_window * 100, 2)


def fits_in_context(token_count: int, context_window: int) -> bool:
    if context_window <= 0:
        return False
    return token_count <= context_window


def min_chunks(token_count: int, context_window: int) -> int:
    """Minimum API calls needed to process the full document."""
    if context_window <= 0:
        return 0
    usable = max(context_window - _RESERVED_OUTPUT, 1)
    return math.ceil(token_count / usable)


def _long_context_active(prompt_token_count: int, model: ModelInfo) -> bool:
    """Whether prompt_token_count crosses this model's long-context tier.

    The tier is decided by the prompt (input) size, per every provider that
    offers one -- not by the completion size, even when pricing output.
    """
    return (
        model.long_context_threshold is not None
        and prompt_token_count > model.long_context_threshold
    )


def input_cost(token_count: int, model: ModelInfo) -> float:
    """USD cost for processing token_count input/prompt tokens."""
    rate = model.input_price_per_million
    if (
        _long_context_active(token_count, model)
        and model.long_context_input_price_per_million is not None
    ):
        rate = model.long_context_input_price_per_million
    return (token_count / 1_000_000) * rate


def output_cost(
    token_count: int, model: ModelInfo, *, prompt_token_count: int | None = None
) -> float:
    """USD cost for token_count output tokens.

    prompt_token_count is the input/prompt size that decides which price
    tier applies. Defaults to token_count itself when omitted, which is
    only correct for flat-priced models (long_context_threshold is None) --
    callers pricing a tiered model must pass the real prompt size.
    """
    prompt_size = token_count if prompt_token_count is None else prompt_token_count
    rate = model.output_price_per_million
    if (
        _long_context_active(prompt_size, model)
        and model.long_context_output_price_per_million is not None
    ):
        rate = model.long_context_output_price_per_million
    return (token_count / 1_000_000) * rate


def total_cost(input_tokens: int, output_tokens: int, model: ModelInfo) -> float:
    return input_cost(input_tokens, model) + output_cost(
        output_tokens, model, prompt_token_count=input_tokens
    )
