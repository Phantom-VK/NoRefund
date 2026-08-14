"""Reusable CTk widgets shared across views."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from tkinter import TclError
from typing import ClassVar

import customtkinter as ctk

from norefund.core.models_registry import ModelInfo
from norefund.gui import formatting, motion, native_dialog, theme
from norefund.gui.theme import COLORS


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

    def __init__(self, parent, height: int = theme.SPACE_2, **kwargs) -> None:
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
            font=theme.font(theme.FONT_SMALL),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x")
        self._value_label = ctk.CTkLabel(
            self,
            text=value,
            font=value_font or theme.mono_font(theme.FONT_HEADING, "bold"),
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
        "danger": ("muted", "fg", "destructive")
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
        image = (
            theme.icon_image(icon, size=16, color=COLORS[text_key]) if icon else None
        )
        super().__init__(
            parent,
            text=text,
            image=image,
            compound="left" if image else "none",
            font=theme.font(theme.FONT_LABEL),
            fg_color=COLORS[fg_key],
            text_color=COLORS[text_key],
            # Without this, a disabled button falls back to CTk's generic
            # grey text color while the icon (a static image tinted once at
            # construction time) keeps its real color -- so text and icon
            # visibly mismatch whenever the button is disabled.
            text_color_disabled=COLORS[text_key],
            hover_color=COLORS[hover_key],
            corner_radius=theme.RADIUS_CARD,
            height=theme.CONTROL_MD,
            command=command,
            **kwargs,
        )
        motion.press_feedback(self)


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
            font=theme.font(theme.FONT_MICRO, "bold"),
            fg_color=bg_tint,
            text_color=accent,
            corner_radius=8,
            width=1,
            height=22,
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
        self._icon_name = icon
        super().__init__(
            parent,
            text=text,
            image=theme.icon_image(icon, size=18, color=COLORS["muted_fg"]),
            compound="left",
            font=theme.font(theme.FONT_TITLE),
            anchor="w",
            corner_radius=theme.RADIUS_CARD,
            height=theme.CONTROL_LG,
            fg_color="transparent",
            text_color=COLORS["muted_fg"],
            hover_color=COLORS["sidebar_accent"],
            command=command,
            **kwargs,
        )
        self._active = False
        motion.press_feedback(self)

    def set_active(self, active: bool) -> None:
        self._active = active
        color_key = "sidebar_accent_fg" if active else "muted_fg"
        self.configure(
            fg_color=COLORS["sidebar_accent"] if active else "transparent",
            text_color=COLORS[color_key],
            image=theme.icon_image(self._icon_name, size=18, color=COLORS[color_key]),
        )


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
            corner_radius=theme.RADIUS_CARD,
            cursor="hand2",
            **kwargs,
        )
        self._models = models
        self._selected = selected
        self._on_select = on_select
        self._popover: ModelDropdownPopover | None = None

        self._dot = provider_mark(self, selected.provider)
        self._dot.pack(side="left", padx=(10, theme.SPACE_2), pady=theme.SPACE_2)
        self._label = ctk.CTkLabel(
            self,
            text=formatting.model_label(selected),
            font=theme.font(theme.FONT_LABEL),
            anchor="w",
        )
        self._label.pack(side="left", fill="x", expand=True, pady=theme.SPACE_2)
        self._chevron = ctk.CTkLabel(
            self,
            text="",
            image=theme.icon_image("chevron_down", size=12, color=COLORS["muted_fg"]),
        )
        self._chevron.pack(side="right", padx=(theme.SPACE_2, 10), pady=theme.SPACE_2)

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
        set_provider_mark(self._dot, model.provider)
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

    _ROW_HEIGHT = theme.CONTROL_LG
    _click_watch_installed: ClassVar[bool] = False

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
        self.geometry(f"{width}x{min(self._ROW_HEIGHT * len(models), 320)}+{x}+{y}")

        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["popover"])
        scroll.pack(fill="both", expand=True, padx=1, pady=1)
        bind_mousewheel(scroll)

        for model in models:
            row = ctk.CTkFrame(scroll, fg_color="transparent", cursor="hand2")
            row.pack(fill="x", pady=1)
            dot = provider_mark(row, model.provider)
            dot.pack(side="left", padx=(8, theme.SPACE_2), pady=theme.SPACE_2)
            label = ctk.CTkLabel(
                row,
                text=formatting.model_label(model),
                font=theme.font(theme.FONT_LABEL),
                anchor="w",
            )
            label.pack(side="left", fill="x", expand=True, pady=theme.SPACE_2)
            for widget in (row, dot, label):
                widget.bind("<Button-1>", lambda _e, m=model: self._pick(m))

        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(10, self._grab_focus)
        ModelDropdownPopover._ensure_click_watch(self)

    def _grab_focus(self) -> None:
        if self.winfo_exists():
            self.focus_set()

    @classmethod
    def _ensure_click_watch(cls, widget) -> None:
        """Install (once, app-wide) a click-outside-closes watcher.

        Popovers are borderless overrideredirect(True) Toplevels, which many
        window managers never hand real focus to -- so the previous approach
        of closing on <FocusOut> was unreliable (it could simply never fire).
        A global <Button-1> watch that checks the click's actual target
        against the open popover's widget tree works regardless of the WM's
        focus-routing behavior. Installed once, like bind_mousewheel(), since
        unbind_all() can't remove a single handler once added.
        """
        if cls._click_watch_installed:
            return
        cls._click_watch_installed = True

        def _on_global_click(event) -> None:
            target = event.widget
            if isinstance(target, str):
                return
            for button in list(ModelDropdownButton._open):
                popover = button._popover
                if popover is None or not popover.winfo_exists():
                    continue
                if cls._within(target, popover) or cls._within(target, button):
                    continue
                popover.destroy()

        widget.bind_all("<Button-1>", _on_global_click, add="+")

    @staticmethod
    def _within(widget, ancestor) -> bool:
        while widget is not None:
            if widget is ancestor:
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


@dataclass(frozen=True)
class DropdownItem:
    """One selectable row: a stable `value`, its display `label`, and an
    optional leading icon."""

    value: str
    label: str
    icon: ctk.CTkImage | None = None


class DropdownButton(ctk.CTkFrame):
    """The one dropdown component used everywhere a value is picked from a
    list: trigger button (optional icon + label + chevron) that opens a
    non-modal, width-matched, scrollable popover on click, with hover and
    selected-row highlighting.

    Generic over `DropdownItem.value` (a plain string) -- `ModelDropdownButton`
    above is a thin ModelInfo-specific wrapper around this same popover.
    """

    _open: ClassVar[set[DropdownButton]] = set()

    def __init__(
        self,
        parent,
        items: list[DropdownItem],
        selected_value: str,
        on_select: Callable[[str], None],
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            fg_color=COLORS["input_bg"],
            corner_radius=theme.RADIUS_CARD,
            cursor="hand2",
            **kwargs,
        )
        self._items = items
        self._selected_value = selected_value
        self._on_select = on_select
        self._popover: DropdownPopover | None = None

        self._icon_label = ctk.CTkLabel(self, text="")
        self._text_label = ctk.CTkLabel(
            self, text="", font=theme.font(theme.FONT_LABEL), anchor="w"
        )
        self._text_label.pack(
            side="left", fill="x", expand=True, padx=(10, theme.SPACE_2),
            pady=theme.SPACE_2,
        )
        self._chevron = ctk.CTkLabel(
            self,
            text="",
            image=theme.icon_image("chevron_down", size=12, color=COLORS["muted_fg"]),
        )
        self._chevron.pack(side="right", padx=(theme.SPACE_2, 10), pady=theme.SPACE_2)
        self._sync_display()

        for widget in (self, self._text_label, self._chevron):
            widget.bind("<Button-1>", self._toggle)

    def _item_for(self, value: str) -> DropdownItem | None:
        return next((item for item in self._items if item.value == value), None)

    def _sync_display(self) -> None:
        item = self._item_for(self._selected_value)
        self._text_label.configure(text=item.label if item is not None else "")
        if item is not None and item.icon is not None:
            self._icon_label.configure(image=item.icon)
            self._icon_label.pack(
                side="left", padx=(10, theme.SPACE_2), pady=theme.SPACE_2,
                before=self._text_label,
            )
        else:
            self._icon_label.pack_forget()

    def selected_value(self) -> str:
        return self._selected_value

    def select(self, value: str) -> None:
        """Change the selection without firing `on_select` (external sync)."""
        self._selected_value = value
        self._sync_display()

    def _toggle(self, _event=None) -> None:
        if self._popover is not None and self._popover.winfo_exists():
            self._popover.destroy()
            return
        self._popover = DropdownPopover(
            self, self._items, self._selected_value, self._pick
        )
        DropdownButton._open.add(self)

    def _pick(self, value: str) -> None:
        self.select(value)
        self._on_select(value)

    def _clear_popover(self) -> None:
        self._popover = None
        DropdownButton._open.discard(self)

    def close_popover(self) -> None:
        if self._popover is not None and self._popover.winfo_exists():
            self._popover.destroy()

    @classmethod
    def close_all(cls) -> None:
        """Close every open popover, regardless of which screen opened it."""
        for button in list(cls._open):
            button.close_popover()


class DropdownPopover(ctk.CTkToplevel):
    """Borderless, non-modal, scrollable popover for `DropdownButton`.

    Width matches the trigger (never narrower than 220px); the currently
    selected row is tinted and check-marked at rest, and every row
    highlights on hover. Mirrors ModelDropdownPopover's proven
    click-outside-closes / focus / escape behavior.
    """

    _ROW_HEIGHT = theme.CONTROL_LG
    _click_watch_installed: ClassVar[bool] = False

    def __init__(
        self,
        anchor: DropdownButton,
        items: list[DropdownItem],
        selected_value: str,
        on_pick: Callable[[str], None],
    ) -> None:
        super().__init__(anchor)
        self._anchor = anchor
        self._on_pick = on_pick
        self.overrideredirect(True)
        self.configure(fg_color=COLORS["popover"])
        self.attributes("-topmost", True)

        anchor.update_idletasks()
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height() + 2
        width = max(anchor.winfo_width(), 220)
        self.geometry(f"{width}x{min(self._ROW_HEIGHT * len(items), 320)}+{x}+{y}")

        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["popover"])
        scroll.pack(fill="both", expand=True, padx=1, pady=1)
        bind_mousewheel(scroll)

        for item in items:
            self._build_row(scroll, item, is_selected=item.value == selected_value)

        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(10, self._grab_focus)
        DropdownPopover._ensure_click_watch(self)

    def _build_row(self, scroll, item: DropdownItem, *, is_selected: bool) -> None:
        resting_color = COLORS["sidebar_accent"] if is_selected else "transparent"
        text_color = (
            COLORS["sidebar_accent_fg"] if is_selected else COLORS["popover_fg"]
        )

        row = ctk.CTkFrame(scroll, fg_color=resting_color, cursor="hand2")
        row.pack(fill="x", pady=1)
        widgets = [row]

        if item.icon is not None:
            icon_label = ctk.CTkLabel(row, text="", image=item.icon)
            icon_label.pack(side="left", padx=(8, theme.SPACE_2), pady=theme.SPACE_2)
            widgets.append(icon_label)

        label = ctk.CTkLabel(
            row,
            text=item.label,
            font=theme.font(theme.FONT_LABEL),
            text_color=text_color,
            anchor="w",
        )
        label.pack(
            side="left", fill="x", expand=True, padx=(0, theme.SPACE_2),
            pady=theme.SPACE_2,
        )
        widgets.append(label)

        if is_selected:
            check_icon = theme.icon_image("check", size=14, color=COLORS["primary"])
            check = ctk.CTkLabel(row, text="", image=check_icon)
            check.pack(side="right", padx=(theme.SPACE_2, 8))
            widgets.append(check)

        for widget in widgets:
            widget.bind("<Button-1>", lambda _e, v=item.value: self._pick(v))
            widget.bind(
                "<Enter>", lambda _e, r=row: r.configure(fg_color=COLORS["muted"])
            )
            widget.bind(
                "<Leave>", lambda _e, r=row, rc=resting_color: r.configure(fg_color=rc)
            )

    def _grab_focus(self) -> None:
        if self.winfo_exists():
            self.focus_set()

    @classmethod
    def _ensure_click_watch(cls, widget) -> None:
        if cls._click_watch_installed:
            return
        cls._click_watch_installed = True

        def _on_global_click(event) -> None:
            target = event.widget
            if isinstance(target, str):
                return
            for button in list(DropdownButton._open):
                popover = button._popover
                if popover is None or not popover.winfo_exists():
                    continue
                if cls._within(target, popover) or cls._within(target, button):
                    continue
                popover.destroy()

        widget.bind_all("<Button-1>", _on_global_click, add="+")

    @staticmethod
    def _within(widget, ancestor) -> bool:
        while widget is not None:
            if widget is ancestor:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _pick(self, value: str) -> None:
        self._on_pick(value)
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
        inner.pack(fill="x", padx=theme.SPACE_4, pady=theme.SPACE_2)
        ctk.CTkLabel(
            inner,
            text=text,
            image=theme.icon_image("warning", size=14, color=COLORS["warning_fg"]),
            compound="left",
            font=theme.font(theme.FONT_BODY),
            text_color=COLORS["warning_fg"],
            anchor="w",
        ).pack(side="left")

        if action_text and on_action is not None:
            action = ctk.CTkLabel(
                inner,
                text=action_text,
                font=theme.font(theme.FONT_BODY, "bold"),
                text_color=COLORS["warning_fg"],
                cursor="hand2",
            )
            action.pack(side="left", padx=(theme.SPACE_3, 0))
            action.bind("<Button-1>", lambda _e: on_action())

        close = ctk.CTkLabel(
            inner,
            text="",
            image=theme.icon_image("x", size=12, color=COLORS["warning_fg"]),
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
            ).pack(side="left", padx=(theme.SPACE_1, theme.SPACE_1))
            dot = provider_mark(row, model.provider)
            dot.pack(side="left", padx=(0, theme.SPACE_2))
            ctk.CTkLabel(
                row,
                text=formatting.model_label(model),
                font=theme.font(theme.FONT_LABEL),
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


_wheel_scroll_installed = False


def bind_mousewheel(frame: ctk.CTkScrollableFrame) -> None:
    """Enable Linux (X11) mouse-wheel scrolling for a CTkScrollableFrame.

    CustomTkinter only binds <MouseWheel> internally, which fires on
    Windows/macOS. X11 sends <Button-4>/<Button-5> instead, so without this,
    wheel scrolling silently does nothing on Linux.

    The handler is installed once for the whole app, not once per frame: it
    walks up from whatever widget is under the pointer to find the nearest
    CTkScrollableFrame and scrolls that. Re-registering a fresh bind_all() on
    every call -- e.g. every time a ModelDropdownPopover opens -- would leak
    one global handler per open with no way to remove just that one
    afterwards (Tkinter's unbind_all() clears *all* handlers for the
    sequence, not a single one), so callers can call this on every
    scrollable frame they build without worrying about leaks.
    """
    global _wheel_scroll_installed
    if _wheel_scroll_installed:
        return
    _wheel_scroll_installed = True

    def _on_wheel(event) -> None:
        widget = event.widget
        # A widget from outside this app's own tree (e.g. Tk's built-in file
        # dialog, whose internals have no Python-side wrapper) comes through
        # as a raw path string rather than a widget object.
        if isinstance(widget, str):
            return
        canvas = None
        while widget is not None:
            if isinstance(widget, ctk.CTkScrollableFrame):
                canvas = widget._parent_canvas
                break
            widget = getattr(widget, "master", None)
        if canvas is None:
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
    path = native_dialog.ask_save_file(
        defaultextension=f".{extension}",
        filetypes=[(filetype_label, f"*.{extension}")],
    )
    if path:
        Path(path).write_text(content_fn(), encoding="utf-8")


def card(parent, **kwargs) -> ctk.CTkFrame:
    """Standard card container: `COLORS['card']` background, RADIUS_CARD.

    Unpacked — the caller still calls `.pack(...)`/`.grid(...)` themselves,
    since callers vary in their own spacing (padx/pady).
    """
    return ctk.CTkFrame(
        parent, fg_color=COLORS["card"], corner_radius=theme.RADIUS_CARD, **kwargs
    )


def status_dot(
    parent, color: str | tuple = COLORS["muted"], **kwargs
) -> ctk.CTkLabel:
    """Small colored circle used for generic (non-provider) status indicators."""
    return ctk.CTkLabel(
        parent,
        text="",
        width=12,
        height=12,
        corner_radius=6,
        fg_color=color,
        **kwargs,
    )


def provider_mark(parent, provider: str, *, size: int = 14, **kwargs) -> ctk.CTkLabel:
    """The provider's brand mark, tinted to its accent color.

    Falls back to a plain status_dot() for a provider with no bundled logo
    (defensive only -- every provider in default_models.yaml has one).
    """
    icon = theme.provider_icon(provider, size=size)
    if icon is not None:
        return ctk.CTkLabel(parent, text="", image=icon, **kwargs)
    return status_dot(parent, color=theme.provider_color(provider), **kwargs)


def set_provider_mark(label: ctk.CTkLabel, provider: str, *, size: int = 14) -> None:
    """Update a provider_mark() label in place after the selection changes."""
    icon = theme.provider_icon(provider, size=size)
    if icon is not None:
        label.configure(image=icon, fg_color="transparent")
    else:
        label.configure(
            image=theme.blank_icon(size=size), fg_color=theme.provider_color(provider)
        )


def section_label(
    parent, text: str, *, size: int = theme.FONT_MICRO, anchor: str = "w", **kwargs
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
            font=theme.font(theme.FONT_LABEL),
            text_color=COLORS["muted_fg"],
        )
        self._bg = scrollable_frame.cget("fg_color")

    def show(self) -> None:
        self._label.configure(text_color=COLORS["muted_fg"])
        self._label.place(relx=0.5, rely=0.5, anchor="center")

    def hide(self) -> None:
        motion.fade_text_color(
            self._label,
            COLORS["muted_fg"],
            self._bg,
            duration=150,
            on_done=self._label.place_forget,
        )


class EmptyState(ctk.CTkLabel):
    """Centered muted icon+message shown where results would otherwise go."""

    def __init__(self, parent, icon: str, text: str, **kwargs) -> None:
        super().__init__(
            parent,
            text=text,
            image=theme.icon_image(icon, size=32, color=COLORS["muted_fg"]),
            compound="top",
            font=theme.font(theme.FONT_TITLE),
            text_color=COLORS["muted_fg"],
            justify="center",
            **kwargs,
        )
