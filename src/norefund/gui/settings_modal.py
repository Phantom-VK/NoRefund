"""Settings dialog."""

from __future__ import annotations

import customtkinter as ctk

from norefund.core.settings import Settings
from norefund.gui.formatting import parse_int
from norefund.gui.theme import COLORS
from norefund.gui.widgets import IconButton


class SettingsModal(ctk.CTkToplevel):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self._parent = parent
        self.title("Settings")
        self.geometry("430x330")
        self.resizable(False, False)
        self.transient(parent)
        # Defer grab_set until the window is fully mapped and viewable.
        # Calling grab_set() synchronously in __init__ races against Tk's
        # window-map event on some Linux compositors and raises:
        #   TclError: grab failed: window not viewable
        self.after(50, self._safe_grab)

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
            variable=parent.currency,
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
            text="Currency conversion isn't implemented yet — prices remain in the "
            "model's native currency (USD).",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=11),
            anchor="w",
            wraplength=360,
            justify="left",
        ).pack(fill="x", pady=(8, 0))

        footer = ctk.CTkFrame(frame, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(4, 16))
        IconButton(footer, "Cancel", width=88, command=self.destroy).pack(
            side="right", padx=(8, 0)
        )
        IconButton(
            footer, "Save changes", variant="primary", width=120, command=self._save
        ).pack(side="right")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _save(self) -> None:
        parent = self._parent
        parent.settings = Settings(
            default_output_tokens=parse_int(parent.default_output_tokens.get()),
            theme="dark" if parent.theme_dark else "light",
            currency=parent.currency.get(),
        )
        parent.settings_store.save(parent.settings)
        self.destroy()

    def _safe_grab(self) -> None:
        """Attempt grab_set only when the window is actually viewable.

        The 50 ms delay scheduled in __init__ is enough on virtually all
        platforms, but we guard with winfo_viewable() as a belt-and-braces
        check.  If somehow still not viewable we retry once after another
        100 ms before giving up (modal still works, just without grab).
        """
        if self.winfo_exists() and self.winfo_viewable():
            self.grab_set()
        else:
            self.after(100, self._grab_final_attempt)

    def _grab_final_attempt(self) -> None:
        """Last-chance grab attempt; silently skip if window is gone."""
        if self.winfo_exists() and self.winfo_viewable():
            try:
                self.grab_set()
            except Exception:  # noqa: BLE001
                pass  # Non-fatal — modal is visible, just not input-locked
