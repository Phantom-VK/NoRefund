"""Pure cost and context calculation functions. No I/O, no state."""

import math

from norefund.core.models_registry import ModelInfo

# Tokens reserved for model output so input doesn't overflow the context window
_RESERVED_OUTPUT_TOKENS = 1024


def context_usage_pct(token_count: int, context_window: int) -> float:
    """Percentage of context window used by token_count."""
    return round((token_count / context_window) * 100, 2)


def fits_in_context(token_count: int, context_window: int) -> bool:
    return token_count <= context_window


def min_chunks(token_count: int, context_window: int) -> int:
    """Minimum API calls needed to process the full document."""
    usable = context_window - _RESERVED_OUTPUT_TOKENS
    return math.ceil(token_count / usable)


def input_cost(token_count: int, model: ModelInfo) -> float:
    """Estimated cost in USD for sending token_count input tokens."""
    return (token_count / 1_000_000) * model.input_price_per_million


def output_cost(token_count: int, model: ModelInfo) -> float:
    """Estimated cost in USD for receiving token_count output tokens."""
    return (token_count / 1_000_000) * model.output_price_per_million


def total_cost(input_tokens: int, output_tokens: int, model: ModelInfo) -> float:
    return input_cost(input_tokens, model) + output_cost(output_tokens, model)
