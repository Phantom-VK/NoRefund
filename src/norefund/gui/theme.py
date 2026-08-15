"""Static design tokens for the GUI: colors, type/spacing/control scales, icons.

Color values are ported from the NoRefund Desktop UI Design reference
(`NoRefund Desktop UI Design/src/styles/theme.css`). Each entry is a
``(light_hex, dark_hex)`` pair; CTk widgets accept these tuples directly for
``fg_color``/``text_color``/etc. and switch automatically with
``customtkinter.get_appearance_mode()``. This module has no dependency on
``core.settings`` — appearance-mode *selection* lives in app.py/main_view.py.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk
from PIL import Image, ImageDraw

from norefund.core.parsing import SUPPORTED_EXTENSIONS
from norefund.core.paths import bundled_resource

COLORS: dict[str, tuple[str, str]] = {
    "bg": ("#f5f6f8", "#111318"),
    "fg": ("#0f1117", "#e6edf3"),
    "card": ("#ffffff", "#1c2029"),
    "card_fg": ("#0f1117", "#e6edf3"),
    "popover": ("#ffffff", "#242830"),
    "popover_fg": ("#0f1117", "#e6edf3"),
    # Deliberately distinct from "muted" -- muted's dark value (#242830) is
    # byte-identical to popover's dark background, so it was invisible as a
    # row-hover color on dark popovers. This is a step lighter.
    "popover_hover": ("#e8eaed", "#343b47"),
    "primary": ("#00b894", "#00d4aa"),
    "primary_hover": ("#009f7f", "#00b894"),
    # Dark text, not white: white-on-#00b894 is ~2.5:1 contrast, well under
    # WCAG AA's 4.5:1 for text. Dark mode's value already got this right
    # (#0d1117 on #00d4aa) -- light mode now matches it, since primary's
    # own brightness barely changes between modes.
    "primary_fg": ("#0d1117", "#0d1117"),
    "secondary": ("#eef0f3", "#242830"),
    "secondary_fg": ("#0f1117", "#e6edf3"),
    "muted": ("#e8eaed", "#242830"),
    "muted_fg": ("#6b7280", "#7d8590"),
    "destructive": ("#ef4444", "#f85149"),
    "destructive_fg": ("#ffffff", "#ffffff"),
    # A "muted" chip lightly tinted toward destructive -- rest-state
    # background for IconButton's "danger" variant, so a destructive
    # button (e.g. Clear) reads as different from a neutral one before
    # hover, not just on it.
    "destructive_muted": ("#e9cccf", "#4a2f34"),
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

SUPPORTED_FILETYPES: list[tuple[str, str]] = [
    (
        "Supported documents",
        " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS)),
    ),
    ("All files", "*.*"),
]

# ----------------------------------------------------------------------
# Type scale
# ----------------------------------------------------------------------

FONT_MICRO = 11
FONT_SMALL = 12
FONT_BODY = 13
FONT_LABEL = 14
FONT_TITLE = 15
FONT_HEADING = 20
FONT_DISPLAY = 26

# ----------------------------------------------------------------------
# Spacing — single 4px grid
# ----------------------------------------------------------------------

SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
SPACE_7 = 32
CARD_PAD_X = 20
CARD_PAD_Y = 16
PAGE_GUTTER = 24

# ----------------------------------------------------------------------
# Controls
# ----------------------------------------------------------------------

CONTROL_SM = 30
CONTROL_MD = 36
CONTROL_LG = 42

# ----------------------------------------------------------------------
# Radius
# ----------------------------------------------------------------------

RADIUS_CARD = 6

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


def font(size: int = FONT_BODY, weight: str = "normal") -> tuple[str, int, str]:
    """UI text font tuple, e.g. for CTkLabel(font=font(FONT_LABEL, "bold"))."""
    return (_ui_family_name(), size, weight)


def mono_font(size: int = FONT_BODY, weight: str = "normal") -> tuple[str, int, str]:
    """Monospace font tuple for numbers, paths, and log output."""
    return (_mono_family_name(), size, weight)


def tk_font(
    size: int = FONT_BODY, weight: str = "normal", scaling: float = 1.0
) -> tuple[str, int, str]:
    """Like font(), but for plain tkinter widgets (tk.Label/tk.Frame, not
    CTkLabel) that don't run font tuples through CTk's own point->pixel
    scaling. A *positive* Tk font size means points; CTkLabel always
    converts to a *negative* (pixel) size before handing it to the
    underlying Tk widget, so the exact same nominal size renders visibly
    larger on a plain tk widget than on a CTkLabel. This applies the same
    conversion CTk uses internally, so plain-tk text matches CTk text at
    the same nominal size. `scaling` should be
    `ctk.ScalingTracker.get_widget_scaling(widget)`.
    """
    return (_ui_family_name(), -abs(round(size * scaling)), weight)


def resolve(token: str, dark: bool) -> str:
    """Resolve a COLORS token to a single hex string for non-CTk widgets
    (e.g. raw tkinter.Text tag colors) that don't auto-switch on appearance mode."""
    light_hex, dark_hex = COLORS[token]
    return dark_hex if dark else light_hex


def provider_color(provider: str) -> str:
    return PROVIDER_COLORS.get(provider, _DEFAULT_PROVIDER_COLOR)


_PROVIDER_SLUGS: dict[str, str] = {
    "OpenAI": "openai",
    "Anthropic": "anthropic",
    "Google": "google",
    "DeepSeek": "deepseek",
    "Meta": "meta",
    "Mistral": "mistral",
}


def provider_icon(provider: str, size: int = 16) -> ctk.CTkImage | None:
    """The provider's brand mark (assets/icons/providers/<slug>.png), tinted
    to its accent color. None if `provider` has no bundled mark, so callers
    can fall back to a plain status dot."""
    slug = _PROVIDER_SLUGS.get(provider)
    if slug is None:
        return None
    hex_color = provider_color(provider)
    return icon_image(f"providers/{slug}", size=size, color=(hex_color, hex_color))


_dot_icon_cache: dict[tuple[int, str, int], ctk.CTkImage] = {}


def _dot_icon(hex_color: str, size: int) -> ctk.CTkImage:
    root_id = id(tk._default_root)
    key = (root_id, hex_color, size)
    cached = _dot_icon_cache.get(key)
    if cached is not None:
        return cached
    diameter = max(4, size - 4)
    offset = (size - diameter) // 2
    dot = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(dot).ellipse(
        (offset, offset, offset + diameter, offset + diameter), fill=hex_color
    )
    image = ctk.CTkImage(light_image=dot, dark_image=dot, size=(size, size))
    _dot_icon_cache[key] = image
    return image


def provider_icon_or_dot(provider: str, size: int = 16) -> ctk.CTkImage:
    """Like `provider_icon()`, but never returns None: a provider with no
    bundled brand mark (e.g. Qwen) gets a solid dot in its accent color
    instead, matching `provider_mark()`'s widget-based fallback elsewhere.

    Use this (not `provider_icon()`) for a list of DropdownItems that mixes
    providers with and without a bundled logo -- every row then gets a
    leading icon, so they stay aligned with each other.
    """
    icon = provider_icon(provider, size=size)
    if icon is not None:
        return icon
    return _dot_icon(provider_color(provider), size=size)


# ----------------------------------------------------------------------
# Icons — monochrome PNGs (src/norefund/assets/icons), alpha-tinted at
# load time to any COLORS token so one source file covers every theme
# color in both light and dark mode. Replaces the old mixed emoji/glyph
# ICONS dict; icon *names* below are the source-of-truth vocabulary used
# across the GUI (each must have a matching assets/icons/<name>.png).
# ----------------------------------------------------------------------

_icon_source_cache: dict[str, Image.Image] = {}
_icon_image_cache: dict[tuple[int, str, int, tuple[str, str]], ctk.CTkImage] = {}


def _icon_source(name: str) -> Image.Image:
    source = _icon_source_cache.get(name)
    if source is None:
        path = bundled_resource(f"assets/icons/{name}.png")
        source = Image.open(path).convert("RGBA")
        _icon_source_cache[name] = source
    return source


def _tint(name: str, hex_color: str) -> Image.Image:
    source = _icon_source(name)
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    solid = Image.new("RGBA", source.size, (r, g, b, 255))
    solid.putalpha(source.getchannel("A"))
    return solid


def icon_image(
    name: str, size: int = 16, color: tuple[str, str] = COLORS["fg"]
) -> ctk.CTkImage:
    """A CTkImage for icon `name`, tinted to `color` (light_hex, dark_hex).

    Cached per (Tk interpreter, name, size, color) — callers can call this
    freely on every build/reconfigure without re-reading or re-tinting the
    source PNG. Keying on the current default root's id (not just the icon
    params) matters because a CTkImage's underlying PhotoImage is bound to
    the Tk interpreter that created it: reusing one across interpreters
    (e.g. a fresh `ctk.CTk()` per test) raises "image ... doesn't exist"
    once the original interpreter is destroyed.
    """
    root_id = id(tk._default_root)
    key = (root_id, name, size, color)
    cached = _icon_image_cache.get(key)
    if cached is not None:
        return cached
    image = ctk.CTkImage(
        light_image=_tint(name, color[0]),
        dark_image=_tint(name, color[1]),
        size=(size, size),
    )
    _icon_image_cache[key] = image
    return image


_icon_source_cache["__blank__"] = Image.new("RGBA", (8, 8), (0, 0, 0, 0))


def blank_icon(size: int = 16) -> ctk.CTkImage:
    """A fully transparent CTkImage, for *clearing* a widget's icon.

    `widget.configure(image=None)` is a no-op on CTkButton/CTkLabel once an
    image has been set: `_update_image()` only overwrites the underlying Tk
    image when the new value is a CTkImage (or another non-None image), so
    the previous icon stays on screen. Configuring with a real (blank)
    CTkImage instead actually replaces it.
    """
    return icon_image("__blank__", size=size, color=("#000000", "#000000"))
