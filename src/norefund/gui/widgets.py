"""Reusable CTk widgets shared across views."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import TclError, filedialog
from typing import ClassVar

import customtkinter as ctk

from norefund.core.models_registry import ModelInfo
from norefund.gui import formatting, theme
from norefund.gui.theme import COLORS, ICONS


class ThreadSafeSchedulerMixin:
    """Adds `_schedule()` for safely posting callbacks from worker threads.

    Mix into any CTk widget that starts background threads (downloads,
    scans, tokenization) and needs to update the UI from them. Swallows the
    Tcl/RuntimeError that `winfo_exists()`/`after()` can raise when the
    widget (or the whole app) has been destroyed while the thread was still
    running, so a callback firing during shutdown doesn't crash the app.
    """

    def _schedule(self, callback, *args) -> None:
        try:
            if not self.winfo_exists():
                return
            self.after(0, callback, *args)
        except (TclError, RuntimeError):
            pass


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

    Tracks every instance with an open popover in a class-level registry so
    callers that switch screens (e.g. MainView.show_view) can force-close
    any dropdown left open on the screen being navigated away from — the
    popover is a separate CTkToplevel, so raising a different view frame on
    top of it does nothing to make it go away on its own.
    """

    _open: ClassVar[set[ModelDropdownButton]] = set()

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
            return
        self._popover = ModelDropdownPopover(self, self._models, self._select)
        ModelDropdownButton._open.add(self)

    def _select(self, model: ModelInfo) -> None:
        self._selected = model
        self._dot.configure(fg_color=theme.provider_color(model.provider))
        self._label.configure(text=formatting.model_label(model))
        self._on_select(model)

    def _clear_popover(self) -> None:
        self._popover = None
        ModelDropdownButton._open.discard(self)

    def close_popover(self) -> None:
        if self._popover is not None and self._popover.winfo_exists():
            self._popover.destroy()

    @classmethod
    def close_all(cls) -> None:
        """Close every open dropdown popover, regardless of which screen opened it."""
        for button in list(cls._open):
            button.close_popover()


class ModelDropdownPopover(ctk.CTkToplevel):
    """Borderless, non-modal popover listing every model with a colored dot."""

    def __init__(
        self,
        anchor: ModelDropdownButton,
        models: list[ModelInfo],
        on_select: Callable[[ModelInfo], None],
    ) -> None:
        super().__init__(anchor)
        self._anchor = anchor
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
        if not self.winfo_exists():
            return
        # Close whenever focus has moved outside this popover -- including
        # to another widget in the *same* window (e.g. a sidebar nav item),
        # not just when focus leaves the whole application. Checking only
        # for `is None` here was the bug: clicking anything else in this
        # app moves focus to that widget rather than clearing it, so the
        # popover never noticed it should close.
        if not self._contains(self.focus_displayof()):
            self.destroy()

    def _contains(self, widget) -> bool:
        while widget is not None:
            if widget is self:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _pick(self, model: ModelInfo) -> None:
        self._on_select(model)
        if self.winfo_exists():
            self.destroy()

    def destroy(self) -> None:
        if self._anchor._popover is self:
            self._anchor._clear_popover()
        super().destroy()


class NoticeBanner(ctk.CTkFrame):
    """Dismissible, non-modal notice bar with an optional action link."""

    def __init__(
        self,
        parent,
        text: str,
        *,
        action_text: str | None = None,
        on_action: Callable[[], None] | None = None,
        on_dismiss: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, fg_color=COLORS["warning"], corner_radius=0, **kwargs)
        self._on_dismiss = on_dismiss

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(
            inner,
            text=f"{ICONS['warning']}  {text}",
            font=theme.font(11),
            text_color=COLORS["warning_fg"],
            anchor="w",
        ).pack(side="left")

        if action_text and on_action is not None:
            action = ctk.CTkLabel(
                inner,
                text=action_text,
                font=theme.font(11, "bold"),
                text_color=COLORS["warning_fg"],
                cursor="hand2",
            )
            action.pack(side="left", padx=(12, 0))
            action.bind("<Button-1>", lambda _e: on_action())

        close = ctk.CTkLabel(
            inner,
            text=ICONS["x"],
            font=theme.font(11),
            text_color=COLORS["warning_fg"],
            cursor="hand2",
        )
        close.pack(side="right")
        close.bind("<Button-1>", lambda _e: self._dismiss())

    def _dismiss(self) -> None:
        self.pack_forget()
        if self._on_dismiss is not None:
            self._on_dismiss()


class ModelCheckList(ctk.CTkScrollableFrame):
    """Scrollable list of model checkboxes, all checked by default."""

    def __init__(
        self,
        parent,
        models: list[ModelInfo],
        on_change: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, fg_color=COLORS["card"], **kwargs)
        self._models = models
        self._on_change = on_change
        self._vars: dict[str, ctk.BooleanVar] = {}

        for model in models:
            var = ctk.BooleanVar(value=True)
            self._vars[model.id] = var
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkCheckBox(
                row,
                text="",
                variable=var,
                width=20,
                command=self._notify_change,
                fg_color=COLORS["primary"],
            ).pack(side="left", padx=(4, 4))
            dot = ctk.CTkLabel(
                row,
                text="",
                width=10,
                height=10,
                corner_radius=5,
                fg_color=theme.provider_color(model.provider),
            )
            dot.pack(side="left", padx=(0, 6))
            ctk.CTkLabel(
                row,
                text=formatting.model_label(model),
                font=theme.font(12),
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

        bind_mousewheel(self)

    def _notify_change(self) -> None:
        if self._on_change is not None:
            self._on_change()

    def selected_models(self) -> list[ModelInfo]:
        return [m for m in self._models if self._vars[m.id].get()]

    def select_all(self) -> None:
        for var in self._vars.values():
            var.set(True)
        self._notify_change()

    def select_none(self) -> None:
        for var in self._vars.values():
            var.set(False)
        self._notify_change()


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


def export_via_dialog(
    *,
    has_data: bool,
    extension: str,
    filetype_label: str,
    content_fn: Callable[[], str],
) -> None:
    """Prompt a save-file dialog and write `content_fn()`'s result to it.

    No-op if `has_data` is False (nothing to export yet) or the dialog is
    cancelled.
    """
    if not has_data:
        return
    path = filedialog.asksaveasfilename(
        defaultextension=f".{extension}",
        filetypes=[(filetype_label, f"*.{extension}")],
    )
    if path:
        Path(path).write_text(content_fn(), encoding="utf-8")


def card(parent, **kwargs) -> ctk.CTkFrame:
    """Standard card container: `COLORS['card']` background, corner_radius=6.

    Unpacked — the caller still calls `.pack(...)`/`.grid(...)` themselves,
    since callers vary in their own spacing (padx/pady).
    """
    return ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=6, **kwargs)


def status_dot(parent, color: str | tuple = COLORS["muted"], **kwargs) -> ctk.CTkLabel:
    """Small colored circle used for status/provider-identity indicators."""
    return ctk.CTkLabel(
        parent,
        text="",
        width=10,
        height=10,
        corner_radius=5,
        fg_color=color,
        **kwargs,
    )


def section_label(
    parent, text: str, *, size: int = 9, anchor: str = "w", **kwargs
) -> ctk.CTkLabel:
    """Uppercase, bold, muted header label for a section heading."""
    return ctk.CTkLabel(
        parent,
        text=text.upper(),
        font=theme.font(size, "bold"),
        text_color=COLORS["muted_fg"],
        anchor=anchor,
        **kwargs,
    )


class LoadingOverlay:
    """Centered muted label placed over a `CTkScrollableFrame`'s canvas.

    Parented on `_parent_canvas` (the scroll area's actual visible viewport,
    not the inner content frame that grows/shrinks with content) so
    relx/rely=0.5 centers it on the screen the user sees, regardless of
    scroll position or how much content ends up being built. Owns the one
    place that reaches into CTkScrollableFrame's private `_parent_canvas`
    attribute, so callers don't each have to.
    """

    def __init__(self, scrollable_frame: ctk.CTkScrollableFrame, text: str) -> None:
        self._label = ctk.CTkLabel(
            scrollable_frame._parent_canvas,
            text=text,
            font=theme.font(12),
            text_color=COLORS["muted_fg"],
        )

    def show(self) -> None:
        self._label.place(relx=0.5, rely=0.5, anchor="center")

    def hide(self) -> None:
        self._label.place_forget()


class EmptyState(ctk.CTkLabel):
    """Centered muted icon+message shown where results would otherwise go."""

    def __init__(self, parent, icon: str, text: str, **kwargs) -> None:
        super().__init__(
            parent,
            text=f"{icon}\n\n{text}",
            font=theme.font(13),
            text_color=COLORS["muted_fg"],
            justify="center",
            **kwargs,
        )
