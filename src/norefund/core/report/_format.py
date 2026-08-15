"""Pure formatting helpers private to core/report -- mirrors gui/formatting.py's
number/cost/byte conventions but has no gui/theme.py dependency (core/ never
imports from gui/)."""

from __future__ import annotations


def fmt_num(n: int) -> str:
    return f"{n:,}"


def fmt_pct(pct: float | None) -> str:
    if pct is None:
        return "—"
    return f"{pct:.1f}%"


def fmt_cost(value: float) -> str:
    if value < 0.01:
        return f"${value:.6f}"
    return f"${value:,.2f}"


def fmt_bytes(n: int | None) -> str:
    if n is None:
        return "—"
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"
