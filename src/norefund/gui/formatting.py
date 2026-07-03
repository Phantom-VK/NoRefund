"""Formatting helpers for GUI views."""

from __future__ import annotations

from typing import Optional

from norefund.core.models_registry import ModelInfo
from norefund.gui.theme import COLORS, PROVIDER_COLORS


def fmt_num(value: int | float) -> str:
    return f"{value:,.0f}"


def fmt_float(value: Optional[float], decimals: int = 1) -> str:
    """Format a float to *decimals* decimal places with thousand separators.

    Returns '\u2014' (em-dash) when *value* is None so the GUI renders a
    clean placeholder instead of crashing.  This is the expected path for
    context_usage_pct when context_window <= 0.
    """
    if value is None:
        return "\u2014"
    return f"{value:,.{decimals}f}"


def fmt_context_pct(pct: Optional[float]) -> str:
    """Format context-window usage percentage for table cells.

    Returns '\u2014' when *pct* is None (e.g. model has no context window set).
    Returns e.g. '42.3%' otherwise.
    """
    if pct is None:
        return "\u2014"
    return f"{pct:,.1f}%"


def fmt_cost(value: float) -> str:
    if value < 0.01:
        return f"${value:.6f}"
    return f"${value:,.2f}"


def parse_int(value: str) -> int:
    try:
        return max(0, int(value.replace(",", "").strip() or "0"))
    except ValueError:
        return 0


def context_color(pct: Optional[float]) -> str:
    """Return the appropriate accent colour for a context-usage percentage.

    Falls back to primary colour when *pct* is None so callers never crash.
    """
    if pct is None:
        return COLORS["primary"][1]
    if pct >= 100:
        return COLORS["danger"][1]
    if pct >= 75:
        return COLORS["warning"][1]
    return COLORS["primary"][1]


def provider_color(provider: str) -> str:
    return PROVIDER_COLORS.get(provider, COLORS["primary"][1])


def _blend(fg_hex: str, bg_hex: str, alpha: float) -> str:
    """Blend fg_hex over bg_hex at the given alpha (0-1), returning a hex color."""
    fg = tuple(int(fg_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    bg = tuple(int(bg_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    blended = tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg))
    return "#{:02x}{:02x}{:02x}".format(*blended)


def tint(accent_hex: str, alpha: float = 0.09) -> tuple[str, str]:
    """Blend an accent color over the card background for light/dark mode.

    CTk widget fg_color can't do real alpha compositing, so this pre-blends
    the accent into a flat hex per mode instead.
    """
    return (
        _blend(accent_hex, COLORS["card"][0], alpha),
        _blend(accent_hex, COLORS["card"][1], alpha),
    )


def model_label(model: ModelInfo) -> str:
    return f"{model.display_name}  \u00b7  {model.provider}"
