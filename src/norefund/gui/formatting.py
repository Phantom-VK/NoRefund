"""Pure, None-safe formatting helpers shared by every GUI view.

Kept side-effect free and independent of any live widget so it can be
unit-tested without a Tk root (see tests/test_formatting.py).
"""

from __future__ import annotations

from norefund.core.models_registry import ModelInfo
from norefund.gui.theme import COLORS


def model_label(model: ModelInfo) -> str:
    label = f"{model.display_name}  ·  {model.provider}"
    if model.tokenizer_is_approximate:
        label += "  (approx.)"
    return label


def fmt_num(n: int) -> str:
    return f"{n:,}"


def fmt_float(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:,.{decimals}f}"


def fmt_context_pct(pct: float | None) -> str:
    if pct is None:
        return "—"
    return f"{pct:.1f}%"


def fmt_cost(value: float) -> str:
    if value < 0.01:
        return f"${value:.6f}"
    return f"${value:,.2f}"


def fmt_context_window(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M tokens".replace(".0M", "M")
    if n >= 1_000:
        return f"{n / 1_000:.0f}K tokens"
    return f"{n} tokens"


def fmt_bytes(n: int | None) -> str:
    if n is None:
        return "—"
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def parse_int(value: str, default: int = 0) -> int:
    cleaned = value.replace(",", "").strip()
    if not cleaned:
        return default
    try:
        return int(float(cleaned))
    except ValueError:
        return default


def is_valid_int(value: str) -> bool:
    """Whether `value` would parse as a real number for parse_int(), rather
    than silently falling back to its default -- lets a numeric entry flag
    unparseable input instead of correcting it with no feedback."""
    cleaned = value.replace(",", "").strip()
    if not cleaned:
        return False
    try:
        int(float(cleaned))
        return True
    except ValueError:
        return False


def context_color(pct: float | None) -> tuple[str, str]:
    """Returns a (light_hex, dark_hex) COLORS-style tuple for the given
    context-usage percentage: primary <75%, warning 75-100%, destructive >=100%."""
    if pct is None or pct < 75:
        return COLORS["primary"]
    if pct < 100:
        return COLORS["warning"]
    return COLORS["destructive"]


def elide_middle(text: str, max_chars: int) -> str:
    """Truncate long text in the middle, keeping the tail (usually a
    filename) visible since that's the part that identifies the resource."""
    if len(text) <= max_chars or max_chars <= 1:
        return text
    tail_len = max(1, max_chars // 3)
    head_len = max_chars - tail_len - 1
    return f"{text[:head_len]}…{text[-tail_len:]}"


def tint(accent_hex: str, bg_hex: str, alpha: float) -> str:
    """Alpha-blend accent_hex over bg_hex, returning a flat hex color."""
    a = _hex_to_rgb(accent_hex)
    b = _hex_to_rgb(bg_hex)
    blended = tuple(round(b[i] + (a[i] - b[i]) * alpha) for i in range(3))
    return "#{:02x}{:02x}{:02x}".format(*blended)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
