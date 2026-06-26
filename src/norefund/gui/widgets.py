"""Reusable CustomTkinter widgets used across GUI screens."""

from __future__ import annotations

import customtkinter as ctk

from norefund.core.models_registry import ModelInfo
from norefund.gui.formatting import context_color, model_label
from norefund.gui.theme import COLORS


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

    def set_value(self, pct: float) -> None:
        self._bar.set(min(max(pct, 0), 100) / 100)
        self._bar.configure(progress_color=context_color(pct))


class StatPill(ctk.CTkFrame):
    def __init__(self, parent, label: str, value: str = "-", **kw) -> None:
        super().__init__(parent, fg_color="transparent", **kw)
        ctk.CTkLabel(
            self,
            text=label.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["muted_text"],
            anchor="w",
        ).pack(anchor="w")
        self._value = ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont(size=14, weight="bold", family="monospace"),
            text_color=COLORS["text"],
            anchor="w",
        )
        self._value.pack(anchor="w", pady=(2, 0))

    def set_text(self, value: str) -> None:
        self._value.configure(text=value)


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
        colors.update(kw)
        super().__init__(
            parent,
            text=text,
            corner_radius=5,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            **colors,
        )


class ModelDropdown(ctk.CTkOptionMenu):
    def __init__(self, parent, models: list[ModelInfo], command=None, **kw) -> None:
        self.models = models
        self.model_by_label = {model_label(model): model for model in models}
        values = list(self.model_by_label)
        self.var = ctk.StringVar(value=values[0] if values else "")
        super().__init__(
            parent,
            values=values,
            variable=self.var,
            command=command,
            fg_color=COLORS["muted"],
            button_color=COLORS["muted"],
            button_hover_color=("gray75", "gray25"),
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["card"],
            dropdown_hover_color=COLORS["muted"],
            dropdown_text_color=COLORS["text"],
            corner_radius=5,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            **kw,
        )

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
            font=ctk.CTkFont(size=13, weight="bold"),
        )

    def set_active(self, active: bool) -> None:
        self.configure(
            fg_color=COLORS["sidebar_accent"] if active else "transparent",
            text_color=COLORS["primary"] if active else COLORS["muted_text"],
        )
