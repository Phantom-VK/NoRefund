"""Pure cost and context-window calculations."""

from __future__ import annotations

import math
from typing import Optional

from norefund.core.models_registry import ModelInfo

# Tokens reserved for model output within the context window when chunking
_RESERVED_OUTPUT = 1_024


def context_usage_pct(token_count: int, context_window: int) -> Optional[float]:
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


def input_cost(token_count: int, model: ModelInfo) -> float:
    """USD cost for processing token_count input tokens."""
    return (token_count / 1_000_000) * model.input_price_per_million


def output_cost(token_count: int, model: ModelInfo) -> float:
    """USD cost for token_count output tokens."""
    return (token_count / 1_000_000) * model.output_price_per_million


def total_cost(input_tokens: int, output_tokens: int, model: ModelInfo) -> float:
    return input_cost(input_tokens, model) + output_cost(output_tokens, model)
