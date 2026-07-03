"""Reusable CustomTkinter widgets used across GUI screens."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from norefund.core.models_registry import ModelInfo
from norefund.gui.formatting import context_color, model_label, provider_color, tint
from norefund.gui.theme import COLORS, mono_font
from norefund.gui.theme import font as themed_font


class ContextBar(ctk.CTkFrame):
    def __init__(self, parent, height: int = 7, **kw) -> None:
        super().__init__(parent, fg_color="transparent", **kw)
        self._bar = ctk.CTkProgressBar(
            self,
            height=height,
            fg_color=COLORS["muted"],
            progress_color=COLORS["primary"],
        )
        self._bar.set(0)
        self._bar.pack(fill="x", expand=True)

    def set_value(self, pct: Optional[float]) -> None:
        """Update bar fill and colour. None (no context window) renders empty/muted."""
        if pct is None:
            self._bar.set(0)
            self._bar.configure(progress_color=context_color(None))
            return
        self._bar.set(min(max(pct, 0), 100) / 100)
        self._bar.configure(progress_color=context_color(pct))


class StatPill(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        label: str,
        value: str = "-",
        subtext: str = "",
        value_size: int = 14,
        value_color=None,
        value_weight: str = "bold",
        **kw,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kw)
        ctk.CTkLabel(
            self,
            text=label.upper(),
            font=themed_font(10, "bold"),
            text_color=COLORS["muted_text"],
            anchor="w",
        ).pack(anchor="w")
        self._value = ctk.CTkLabel(
            self,
            text=value,
            font=mono_font(value_size, value_weight),
            text_color=value_color if value_color is not None else COLORS["text"],
            anchor="w",
        )
        self._value.pack(anchor="w", pady=(2, 0))
        self._subtext = None
        if subtext:
            self._subtext = ctk.CTkLabel(
                self,
                text=subtext,
                font=themed_font(11),
                text_color=COLORS["muted_text"],
                anchor="w",
            )
            self._subtext.pack(anchor="w")

    def set_text(self, value: str) -> None:
        self._value.configure(text=value)

    def set_subtext(self, text: str) -> None:
        if self._subtext is None:
            self._subtext = ctk.CTkLabel(
                self,
                text=text,
                font=themed_font(11),
                text_color=COLORS["muted_text"],
                anchor="w",
            )
            self._subtext.pack(anchor="w")
        else:
            self._subtext.configure(text=text)


class IconButton(ctk.CTkButton):
    def __init__(self, parent, text: str, variant: str = "muted", **kw) -> None:
        if variant == "primary":
            colors = {
                "fg_color": COLORS["primary"],
                "hover_color": COLORS["primary_hover"],
                "text_color": COLORS["primary_text"],
            }
        elif variant == "danger":
            colors = {
                "fg_color": COLORS["muted"],
                "hover_color": ("#fee2e2", "#3a2428"),
                "text_color": COLORS["danger"],
            }
        else:
            colors = {
                "fg_color": COLORS["muted"],
                "hover_color": ("#dde2e8", "#303640"),
                "text_color": COLORS["text"],
            }
        base = {
            "corner_radius": 5,
            "height": 30,
            "font": themed_font(12, "bold"),
        }
        base.update(colors)
        base.update(kw)
        super().__init__(parent, text=text, **base)


class ProviderBadge(ctk.CTkLabel):
    """Tinted pill showing a provider name, mirroring the reference's ProviderBadge."""

    def __init__(self, parent, provider: str, **kw) -> None:
        accent = provider_color(provider)
        super().__init__(
            parent,
            text=provider.upper(),
            fg_color=tint(accent, 0.18),
            text_color=accent,
            corner_radius=6,
            font=themed_font(10, "bold"),
            **kw,
        )


class ModelDropdown(ctk.CTkFrame):
    """Compound widget: a provider-color dot next to a CTkOptionMenu.

    CTk's dropdown menu (raw tkinter.Menu under the hood) renders every row
    with one uniform color, so only the trigger's dot can reflect the
    selected model's provider color — the open dropdown's rows stay plain.
    """

    def __init__(
        self, parent, models: list[ModelInfo], command=None, width: int = 200, **kw
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kw)
        self.models = models
        self.model_by_label = {model_label(model): model for model in models}
        values = list(self.model_by_label)
        self.var = ctk.StringVar(value=values[0] if values else "")
        self._external_command = command

        self.dot = ctk.CTkLabel(
            self,
            text="",
            width=10,
            height=10,
            corner_radius=5,
            fg_color=self._dot_color(),
        )
        self.dot.pack(side="left", padx=(0, 6))

        self.menu = ctk.CTkOptionMenu(
            self,
            values=values,
            variable=self.var,
            command=self._on_select,
            fg_color=COLORS["muted"],
            button_color=COLORS["muted"],
            button_hover_color=("gray75", "gray25"),
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["card"],
            dropdown_hover_color=COLORS["muted"],
            dropdown_text_color=COLORS["text"],
            corner_radius=5,
            height=30,
            width=width,
            font=themed_font(12, "bold"),
        )
        self.menu.pack(side="left", fill="x", expand=True)

    def _dot_color(self) -> str:
        model = self.model_by_label.get(self.var.get())
        return provider_color(model.provider) if model else COLORS["muted_text"][1]

    def _on_select(self, value: str) -> None:
        self.dot.configure(fg_color=self._dot_color())
        if self._external_command is not None:
            self._external_command(value)

    def selected_model(self) -> ModelInfo:
        return self.model_by_label[self.var.get()]


class SidebarItem(ctk.CTkButton):
    def __init__(self, parent, label: str, icon: str, command) -> None:
        super().__init__(
            parent,
            text=f"{icon}  {label}",
            command=command,
            anchor="w",
            height=36,
            corner_radius=5,
            fg_color="transparent",
            hover_color=COLORS["muted"],
            text_color=COLORS["muted_text"],
            font=themed_font(13, "bold"),
        )

    def set_active(self, active: bool) -> None:
        self.configure(
            fg_color=COLORS["sidebar_accent"] if active else "transparent",
            text_color=COLORS["primary"] if active else COLORS["muted_text"],
        )
