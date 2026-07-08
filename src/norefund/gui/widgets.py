"""Reusable CTk widgets shared across views."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from norefund.core.models_registry import ModelInfo
from norefund.gui import formatting, theme
from norefund.gui.theme import COLORS, ICONS


class ContextBar(ctk.CTkFrame):
    """Thin, color-coded horizontal progress bar for context-window usage."""

    def __init__(self, parent, height: int = 6, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._bar = ctk.CTkProgressBar(
            self,
            height=height,
            corner_radius=height // 2,
            progress_color=COLORS["primary"],
            fg_color=COLORS["muted"],
        )
        self._bar.pack(fill="x", expand=True)
        self.set_value(None)

    def set_value(
        self, pct: float | None, color: tuple[str, str] | None = None
    ) -> None:
        fraction = 0.0 if pct is None else max(0.0, min(pct / 100, 1.0))
        self._bar.set(fraction)
        self._bar.configure(progress_color=color or formatting.context_color(pct))


class StatPill(ctk.CTkFrame):
    """Uppercase muted label stacked over a bold (usually mono) value."""

    def __init__(
        self,
        parent,
        label: str,
        value: str = "—",
        *,
        value_font: tuple | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        ctk.CTkLabel(
            self,
            text=label.upper(),
            font=theme.font(10),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x")
        self._value_label = ctk.CTkLabel(
            self,
            text=value,
            font=value_font or theme.mono_font(16, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        )
        self._value_label.pack(fill="x")

    def set_text(self, value: str) -> None:
        self._value_label.configure(text=value)


class IconButton(ctk.CTkButton):
    """Small button with an optional icon glyph, styled by variant."""

    _VARIANTS = {
        "primary": ("primary", "primary_fg", "primary_hover"),
        "muted": ("muted", "fg", "border"),
        "danger": ("muted", "fg", "destructive"),
    }

    def __init__(
        self,
        parent,
        text: str = "",
        icon: str | None = None,
        variant: str = "muted",
        command: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        fg_key, text_key, hover_key = self._VARIANTS.get(
            variant, self._VARIANTS["muted"]
        )
        label = f"{ICONS.get(icon, '')} {text}".strip() if icon else text
        super().__init__(
            parent,
            text=label,
            font=theme.font(12),
            fg_color=COLORS[fg_key],
            text_color=COLORS[text_key],
            hover_color=COLORS[hover_key],
            corner_radius=6,
            height=28,
            command=command,
            **kwargs,
        )


class ProviderBadge(ctk.CTkLabel):
    """Small uppercase pill tinted with the provider's brand color."""

    def __init__(self, parent, provider: str, **kwargs) -> None:
        accent = theme.provider_color(provider)
        bg_tint = (
            formatting.tint(accent, COLORS["card"][0], 0.13),
            formatting.tint(accent, COLORS["card"][1], 0.18),
        )
        super().__init__(
            parent,
            text=provider.upper(),
            font=theme.font(9, "bold"),
            fg_color=bg_tint,
            text_color=accent,
            corner_radius=8,
            width=1,
            height=18,
            padx=8,
            **kwargs,
        )


class SidebarItem(ctk.CTkButton):
    """Full-width sidebar nav row with an active/inactive visual state."""

    def __init__(
        self,
        parent,
        text: str,
        icon: str,
        command: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            text=f"{ICONS.get(icon, '')}  {text}",
            font=theme.font(13),
            anchor="w",
            corner_radius=6,
            height=34,
            fg_color="transparent",
            text_color=COLORS["muted_fg"],
            hover_color=COLORS["sidebar_accent"],
            command=command,
            **kwargs,
        )
        self._active = False

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            self.configure(
                fg_color=COLORS["sidebar_accent"],
                text_color=COLORS["sidebar_accent_fg"],
            )
        else:
            self.configure(fg_color="transparent", text_color=COLORS["muted_fg"])


class ModelDropdownButton(ctk.CTkFrame):
    """Trigger button showing a colored provider dot + model label + chevron.

    Opens a non-modal ModelDropdownPopover on click (no grab_set — avoids the
    grab-race bug class the old Settings modal used to hit).
    """

    def __init__(
        self,
        parent,
        models: list[ModelInfo],
        selected: ModelInfo,
        on_select: Callable[[ModelInfo], None],
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            fg_color=COLORS["input_bg"],
            corner_radius=6,
            cursor="hand2",
            **kwargs,
        )
        self._models = models
        self._selected = selected
        self._on_select = on_select
        self._popover: ModelDropdownPopover | None = None

        self._dot = ctk.CTkLabel(
            self,
            text="",
            width=10,
            height=10,
            corner_radius=5,
            fg_color=theme.provider_color(selected.provider),
        )
        self._dot.pack(side="left", padx=(10, 6), pady=8)
        self._label = ctk.CTkLabel(
            self,
            text=formatting.model_label(selected),
            font=theme.font(12),
            anchor="w",
        )
        self._label.pack(side="left", fill="x", expand=True, pady=8)
        self._chevron = ctk.CTkLabel(
            self,
            text=ICONS["chevron_down"],
            font=theme.font(11),
            text_color=COLORS["muted_fg"],
        )
        self._chevron.pack(side="right", padx=(6, 10), pady=8)

        for widget in (self, self._dot, self._label, self._chevron):
            widget.bind("<Button-1>", self._toggle)

    def selected_model(self) -> ModelInfo:
        return self._selected

    def _toggle(self, _event=None) -> None:
        if self._popover is not None and self._popover.winfo_exists():
            self._popover.destroy()
            self._popover = None
            return
        self._popover = ModelDropdownPopover(self, self._models, self._select)

    def _select(self, model: ModelInfo) -> None:
        self._selected = model
        self._dot.configure(fg_color=theme.provider_color(model.provider))
        self._label.configure(text=formatting.model_label(model))
        self._popover = None
        self._on_select(model)


class ModelDropdownPopover(ctk.CTkToplevel):
    """Borderless, non-modal popover listing every model with a colored dot."""

    def __init__(
        self,
        anchor: ctk.CTkFrame,
        models: list[ModelInfo],
        on_select: Callable[[ModelInfo], None],
    ) -> None:
        super().__init__(anchor)
        self._on_select = on_select
        self.overrideredirect(True)
        self.configure(fg_color=COLORS["popover"])
        self.attributes("-topmost", True)

        anchor.update_idletasks()
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height() + 2
        width = max(anchor.winfo_width(), 220)
        self.geometry(f"{width}x{min(36 * len(models), 320)}+{x}+{y}")

        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["popover"])
        scroll.pack(fill="both", expand=True, padx=1, pady=1)
        bind_mousewheel(scroll)

        for model in models:
            row = ctk.CTkFrame(scroll, fg_color="transparent", cursor="hand2")
            row.pack(fill="x", pady=1)
            dot = ctk.CTkLabel(
                row,
                text="",
                width=10,
                height=10,
                corner_radius=5,
                fg_color=theme.provider_color(model.provider),
            )
            dot.pack(side="left", padx=(8, 6), pady=6)
            label = ctk.CTkLabel(
                row,
                text=formatting.model_label(model),
                font=theme.font(12),
                anchor="w",
            )
            label.pack(side="left", fill="x", expand=True, pady=6)
            for widget in (row, dot, label):
                widget.bind("<Button-1>", lambda _e, m=model: self._pick(m))

        self.bind("<FocusOut>", self._maybe_close)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(10, self._grab_focus)

    def _grab_focus(self) -> None:
        if self.winfo_exists():
            self.focus_set()

    def _maybe_close(self, _event=None) -> None:
        self.after(100, self._close_if_unfocused)

    def _close_if_unfocused(self) -> None:
        if self.winfo_exists() and self.focus_displayof() is None:
            self.destroy()

    def _pick(self, model: ModelInfo) -> None:
        self._on_select(model)
        if self.winfo_exists():
            self.destroy()


def bind_mousewheel(frame: ctk.CTkScrollableFrame) -> None:
    """Wire up Linux (X11) mouse-wheel scrolling for a CTkScrollableFrame.

    CustomTkinter only binds <MouseWheel> internally, which fires on
    Windows/macOS. X11 sends <Button-4>/<Button-5> instead, so without this,
    wheel scrolling silently does nothing on Linux.
    """
    canvas = frame._parent_canvas

    def _on_wheel(event) -> None:
        if not frame.check_if_master_is_canvas(event.widget):
            return
        top, bottom = canvas.yview()
        scrolling_up = event.num == 4
        if scrolling_up and top <= 0.0:
            return  # already at the top - don't scroll into blank canvas
        if not scrolling_up and bottom >= 1.0:
            return  # already at the bottom
        canvas.yview_scroll(-1 if scrolling_up else 1, "units")

    frame.bind_all("<Button-4>", _on_wheel, add="+")
    frame.bind_all("<Button-5>", _on_wheel, add="+")
