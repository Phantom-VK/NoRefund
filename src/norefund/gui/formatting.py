"""Formatting and model calculation helpers for GUI views."""

from __future__ import annotations

import math

from norefund.core.models_registry import ModelInfo
from norefund.gui.theme import COLORS, PROVIDER_COLORS


def fmt_num(value: int | float) -> str:
    return f"{value:,.0f}"


def fmt_float(value: float, decimals: int = 1) -> str:
    return f"{value:,.{decimals}f}"


def fmt_cost(value: float) -> str:
    if value < 0.01:
        return f"${value:.6f}"
    return f"${value:,.2f}"


def parse_int(value: str) -> int:
    try:
        return max(0, int(value.replace(",", "").strip() or "0"))
    except ValueError:
        return 0


def context_color(pct: float) -> str:
    if pct >= 100:
        return COLORS["danger"][1]
    if pct >= 75:
        return COLORS["warning"][1]
    return COLORS["primary"][1]


def provider_color(provider: str) -> str:
    return PROVIDER_COLORS.get(provider, COLORS["primary"][1])


def context_pct(tokens: int, model: ModelInfo) -> float:
    if model.context_window <= 0:
        return 0
    return (tokens / model.context_window) * 100


def chunks(tokens: int, model: ModelInfo) -> int:
    if tokens <= 0:
        return 0
    if model.context_window <= 0:
        return 0
    return max(1, math.ceil(tokens / model.context_window))


def model_label(model: ModelInfo) -> str:
    return f"{model.display_name}  ·  {model.provider}"
