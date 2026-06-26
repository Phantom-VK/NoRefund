"""Shared colors and static UI constants for the desktop GUI."""

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
