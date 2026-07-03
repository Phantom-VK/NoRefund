"""Shared colors and static UI constants for the desktop GUI."""

from __future__ import annotations

import customtkinter as ctk

FONT_FAMILY = "Inter"


def font(size: int, weight: str = "normal") -> ctk.CTkFont:
    """CTkFont in FONT_FAMILY; Tk falls back to the OS default if unavailable."""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def mono_font(size: int, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family="monospace", size=size, weight=weight)


ICONS = {
    "calculator": "🧮",
    "folder_open": "📂",
    "layers": "🗂",
    "plus": "+",
    "folder_plus": "📁",
    "x": "✕",
    "zap": "⚡",
    "check": "✓",
    "x_circle": "✕",
    "sun": "☀",
    "moon": "🌙",
    "settings": "⚙",
    "warning": "⚠",
    "bar_chart": "📊",
}

COLORS = {
    "bg": ("#f5f6f8", "#111318"),
    "card": ("#ffffff", "#1c2029"),
    "sidebar": ("#ffffff", "#181c23"),
    "muted": ("#e8eaed", "#242830"),
    "input": ("#eef0f3", "#242830"),
    "border": ("#d9dde3", "#30363d"),
    "text": ("#0f1117", "#e6edf3"),
    "muted_text": ("#6b7280", "#7d8590"),
    "primary": ("#00b894", "#00d4aa"),
    "primary_hover": ("#00a383", "#00bd98"),
    "primary_text": ("#ffffff", "#0d1117"),
    "danger": ("#ef4444", "#f85149"),
    "warning": ("#f59e0b", "#f59e0b"),
    "sidebar_accent": ("#f0faf8", "#17352f"),
}

PROVIDER_COLORS = {
    "OpenAI": "#10a37f",
    "Anthropic": "#d4a373",
    "Google": "#4285f4",
    "DeepSeek": "#5b5ea6",
    "Meta": "#0668e1",
    "Mistral": "#fa7343",
}

SUPPORTED_FILETYPES = [
    ("Supported files", "*.txt *.md *.pdf *.pptx *.docx *.py *.json"),
    ("All files", "*.*"),
]
