"""Static design tokens for the GUI: colors, fonts, icons, filetypes.

Color values are ported from the NoRefund Desktop UI Design reference
(`NoRefund Desktop UI Design/src/styles/theme.css`). Each entry is a
``(light_hex, dark_hex)`` pair; CTk widgets accept these tuples directly for
``fg_color``/``text_color``/etc. and switch automatically with
``customtkinter.get_appearance_mode()``. This module has no dependency on
``core.settings`` — appearance-mode *selection* lives in app.py/main_view.py.
"""

from __future__ import annotations

import tkinter.font as tkfont

from norefund.core.parsing import SUPPORTED_EXTENSIONS

COLORS: dict[str, tuple[str, str]] = {
    "bg": ("#f5f6f8", "#111318"),
    "fg": ("#0f1117", "#e6edf3"),
    "card": ("#ffffff", "#1c2029"),
    "card_fg": ("#0f1117", "#e6edf3"),
    "popover": ("#ffffff", "#242830"),
    "popover_fg": ("#0f1117", "#e6edf3"),
    "primary": ("#00b894", "#00d4aa"),
    "primary_hover": ("#009f7f", "#00b894"),
    "primary_fg": ("#ffffff", "#0d1117"),
    "secondary": ("#eef0f3", "#242830"),
    "secondary_fg": ("#0f1117", "#e6edf3"),
    "muted": ("#e8eaed", "#242830"),
    "muted_fg": ("#6b7280", "#7d8590"),
    "destructive": ("#ef4444", "#f85149"),
    "destructive_fg": ("#ffffff", "#ffffff"),
    "border": ("#e2e2e4", "#2a2f39"),
    "input_bg": ("#eef0f3", "#242830"),
    "sidebar": ("#ffffff", "#181c23"),
    "sidebar_fg": ("#0f1117", "#e6edf3"),
    "sidebar_accent": ("#f0faf8", "#1a2e29"),
    "sidebar_accent_fg": ("#00b894", "#00d4aa"),
    "sidebar_border": ("#e9e9eb", "#22262e"),
    "warning": ("#f59e0b", "#f59e0b"),
    "warning_fg": ("#111318", "#111318"),
}

PROVIDER_COLORS: dict[str, str] = {
    "OpenAI": "#10a37f",
    "Anthropic": "#d4a373",
    "Google": "#4285f4",
    "DeepSeek": "#5b5ea6",
    "Meta": "#0668e1",
    "Mistral": "#fa7343",
}
_DEFAULT_PROVIDER_COLOR = "#8b949e"

ICONS: dict[str, str] = {
    "calculator": "\U0001f5a9",
    "folder_open": "\U0001f4c2",
    "layers": "\U0001f5c2",
    "plus": "+",
    "folder_plus": "\U0001f4c1",
    "x": "✕",
    "zap": "⚡",
    "check": "✓",
    "check_circle": "✓",
    "x_circle": "✗",
    "sun": "☀",
    "moon": "☾",
    "settings": "⚙",
    "warning": "⚠",
    "bar_chart": "\U0001f4ca",
    "chevron_right": "›",
    "chevron_down": "▾",
    "hash": "#",
    "external_link": "↗",
    "file_text": "\U0001f4c4",
    "refresh": "↻",
    "download": "⤓",
    "hard_drive": "\U0001f4be",
}

SUPPORTED_FILETYPES: list[tuple[str, str]] = [
    (
        "Supported documents",
        " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS)),
    ),
    ("All files", "*.*"),
]

_UI_FAMILY_CANDIDATES = ("Inter", "Segoe UI", "Helvetica", "Arial")
_MONO_FAMILY_CANDIDATES = ("JetBrains Mono", "Consolas", "Menlo", "monospace")

_ui_family: str | None = None
_mono_family: str | None = None


def _resolve_family(candidates: tuple[str, ...], fallback: str) -> str:
    available = set(tkfont.families())
    for name in candidates:
        if name in available:
            return name
    return fallback


def _ui_family_name() -> str:
    global _ui_family
    if _ui_family is None:
        _ui_family = _resolve_family(_UI_FAMILY_CANDIDATES, "TkDefaultFont")
    return _ui_family


def _mono_family_name() -> str:
    global _mono_family
    if _mono_family is None:
        _mono_family = _resolve_family(_MONO_FAMILY_CANDIDATES, "TkFixedFont")
    return _mono_family


def font(size: int = 13, weight: str = "normal") -> tuple[str, int, str]:
    """UI text font tuple, e.g. for CTkLabel(font=font(14, "bold"))."""
    return (_ui_family_name(), size, weight)


def mono_font(size: int = 13, weight: str = "normal") -> tuple[str, int, str]:
    """Monospace font tuple for numbers, paths, and log output."""
    return (_mono_family_name(), size, weight)


def resolve(token: str, dark: bool) -> str:
    """Resolve a COLORS token to a single hex string for non-CTk widgets
    (e.g. raw tkinter.Text tag colors) that don't auto-switch on appearance mode."""
    light_hex, dark_hex = COLORS[token]
    return dark_hex if dark else light_hex


def provider_color(provider: str) -> str:
    return PROVIDER_COLORS.get(provider, _DEFAULT_PROVIDER_COLOR)
