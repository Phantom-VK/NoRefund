"""Settings dialog."""

from __future__ import annotations

import customtkinter as ctk

from norefund.gui.theme import COLORS
from norefund.gui.widgets import IconButton


class SettingsModal(ctk.CTkToplevel):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.title("Settings")
        self.geometry("430x330")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=8)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            header,
            text="Settings",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(side="left")
        IconButton(header, "x", width=30, command=self.destroy).pack(side="right")

        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=8)

        ctk.CTkLabel(
            body, text="Default currency", text_color=COLORS["muted_text"], anchor="w"
        ).pack(fill="x")
        ctk.CTkOptionMenu(
            body,
            values=["USD", "EUR", "GBP", "INR"],
            fg_color=COLORS["input"],
            button_color=COLORS["input"],
            state="disabled",
        ).pack(fill="x", pady=(4, 14))

        ctk.CTkLabel(
            body,
            text="Default output tokens estimate",
            text_color=COLORS["muted_text"],
            anchor="w",
        ).pack(fill="x")
        ctk.CTkEntry(
            body,
            textvariable=parent.default_output_tokens,
            fg_color=COLORS["input"],
            border_width=0,
        ).pack(fill="x", pady=(4, 14))

        parent.chunk_warnings = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            body,
            text="Show chunk warnings",
            variable=parent.chunk_warnings,
            progress_color=COLORS["primary"],
        ).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(
            body,
            text="Currency conversion and preference persistence are placeholders.",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(8, 0))

        footer = ctk.CTkFrame(frame, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(4, 16))
        IconButton(footer, "Cancel", width=88, command=self.destroy).pack(
            side="right", padx=(8, 0)
        )
        IconButton(
            footer, "Save changes", variant="primary", width=120, command=self.destroy
        ).pack(side="right")
