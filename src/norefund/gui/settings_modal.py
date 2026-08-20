"""Settings modal (needs grab_set). See widgets.ProcessingModal for the
other modal in the app, shown while a tokenization job is running."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from norefund.core import secrets
from norefund.core.settings import Settings
from norefund.gui import formatting, motion, theme
from norefund.gui.theme import COLORS

_CURRENCIES = ["USD", "EUR", "GBP", "INR"]
_GRAB_RETRY_MS = 30
_MAX_GRAB_ATTEMPTS = 10


class SettingsModal(ctk.CTkToplevel):
    def __init__(
        self, parent, settings: Settings, on_save: Callable[[Settings], None]
    ) -> None:
        super().__init__(parent)
        self._parent_shell = parent
        self._settings = settings
        self._on_save = on_save

        self.title("Settings")
        # Clamp against the actual screen so the footer (Save/Cancel) can't
        # be pushed off-screen -- the fixed 480x620 overflowed at 150% HiDPI
        # scaling and on small/laptop screens. Height stays resizable as a
        # safety net for anything smaller than this clamp still allows.
        width = min(480, self.winfo_screenwidth() - 80)
        height = min(620, self.winfo_screenheight() - 120)
        self.geometry(f"{width}x{height}")
        self.resizable(False, True)
        self.configure(fg_color=COLORS["card"])
        self.transient(parent.winfo_toplevel())

        self._build_ui()
        self._grab_attempts = 0
        self.after(_GRAB_RETRY_MS, self._try_grab)

    def _try_grab(self) -> None:
        if not self.winfo_exists():
            return
        try:
            self.grab_set()
        except Exception:  # noqa: BLE001 — TclError if window not yet viewable
            self._grab_attempts += 1
            if self._grab_attempts < _MAX_GRAB_ATTEMPTS:
                self.after(_GRAB_RETRY_MS, self._try_grab)

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=theme.SPACE_5, pady=(theme.SPACE_4, theme.SPACE_1))
        ctk.CTkLabel(
            header,
            text="Settings",
            font=theme.font(theme.FONT_TITLE, "bold"),
            text_color=COLORS["fg"],
        ).pack(side="left")
        close_btn = ctk.CTkLabel(
            header,
            text="",
            image=theme.icon_image("x", size=14, color=COLORS["muted_fg"]),
            cursor="hand2",
        )
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda _e: self._cancel())

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=theme.SPACE_5, pady=theme.SPACE_2)

        ctk.CTkLabel(
            body,
            text="Default currency",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(theme.SPACE_2, theme.SPACE_2))
        self._currency_var = ctk.StringVar(value=self._settings.currency)
        ctk.CTkOptionMenu(
            body,
            values=_CURRENCIES,
            variable=self._currency_var,
            height=theme.CONTROL_MD,
            font=theme.font(theme.FONT_LABEL),
            fg_color=COLORS["input_bg"],
            button_color=COLORS["muted"],
        ).pack(fill="x")

        ctk.CTkLabel(
            body,
            text="Default output tokens estimate",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(theme.SPACE_4, theme.SPACE_2))
        self._output_tokens_var = ctk.StringVar(
            value=str(self._settings.default_output_tokens)
        )
        self._output_tokens_entry = ctk.CTkEntry(
            body,
            textvariable=self._output_tokens_var,
            height=theme.CONTROL_MD,
            font=theme.mono_font(theme.FONT_LABEL),
            fg_color=COLORS["input_bg"],
            border_width=1,
            border_color=COLORS["input_bg"],
        )
        self._output_tokens_entry.pack(fill="x")
        self._output_tokens_entry.bind(
            "<KeyRelease>", lambda _e: self._on_output_tokens_edited()
        )

        ctk.CTkLabel(
            body,
            text="API tokens & secrets",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(theme.SPACE_5, theme.SPACE_1))

        self._keyring_ok = secrets.keyring_available()
        has_token = self._keyring_ok and secrets.get_hf_token() is not None

        if self._keyring_ok:
            note_text = (
                "Stored in your OS keychain, never written to disk in plaintext. "
                "Used only for HuggingFace tokenizer downloads."
            )
        else:
            note_text = (
                "No system keychain found — secure token storage is unavailable "
                "here."
            )
        ctk.CTkLabel(
            body,
            text=note_text,
            font=theme.font(theme.FONT_SMALL),
            text_color=COLORS["muted_fg"],
            anchor="w",
            justify="left",
            wraplength=420,
        ).pack(fill="x", pady=(0, theme.SPACE_2))

        token_row = ctk.CTkFrame(body, fg_color="transparent")
        token_row.pack(fill="x")
        self._hf_token_var = ctk.StringVar(value="")
        self._hf_token_entry = ctk.CTkEntry(
            token_row,
            textvariable=self._hf_token_var,
            show="•",
            placeholder_text=(
                "Token saved — leave blank to keep"
                if has_token
                else "hf_xxx (optional)"
            ),
            height=theme.CONTROL_MD,
            font=theme.mono_font(theme.FONT_LABEL),
            fg_color=COLORS["input_bg"],
            border_width=0,
            state="normal" if self._keyring_ok else "disabled",
        )
        self._hf_token_entry.pack(side="left", fill="x", expand=True)
        self._clear_token_btn = ctk.CTkButton(
            token_row,
            text="Clear",
            width=64,
            height=theme.CONTROL_MD,
            font=theme.font(theme.FONT_BODY),
            fg_color=COLORS["muted"],
            text_color=COLORS["fg"],
            hover_color=COLORS["border"],
            state="normal" if has_token else "disabled",
            command=self._clear_hf_token,
        )
        self._clear_token_btn.pack(side="left", padx=(theme.SPACE_2, 0))

        toggle_row = ctk.CTkFrame(body, fg_color="transparent")
        toggle_row.pack(fill="x", pady=(theme.SPACE_5, 0))
        self._chunk_warnings_var = ctk.BooleanVar(
            value=self._settings.show_chunk_warnings
        )
        text_col = ctk.CTkFrame(toggle_row, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            text_col,
            text="Show chunk warnings",
            font=theme.font(theme.FONT_LABEL),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            text_col,
            text="Alert when files exceed the context window",
            font=theme.font(theme.FONT_SMALL),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x")
        ctk.CTkSwitch(
            toggle_row,
            text="",
            variable=self._chunk_warnings_var,
            progress_color=COLORS["primary"],
        ).pack(side="right")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(
            fill="x",
            padx=theme.SPACE_5,
            pady=(theme.SPACE_2, theme.SPACE_4),
            side="bottom",
        )
        save_btn = ctk.CTkButton(
            footer,
            text="Save",
            height=theme.CONTROL_MD,
            corner_radius=theme.RADIUS_CARD,
            font=theme.font(theme.FONT_LABEL, "bold"),
            fg_color=COLORS["primary"],
            text_color=COLORS["primary_fg"],
            hover_color=COLORS["primary_hover"],
            command=self._save,
        )
        save_btn.pack(side="right")
        motion.press_feedback(save_btn)
        cancel_btn = ctk.CTkButton(
            footer,
            text="Cancel",
            height=theme.CONTROL_MD,
            corner_radius=theme.RADIUS_CARD,
            font=theme.font(theme.FONT_LABEL),
            fg_color=COLORS["muted"],
            text_color=COLORS["fg"],
            hover_color=COLORS["border"],
            command=self._cancel,
        )
        cancel_btn.pack(side="right", padx=(0, theme.SPACE_2))
        motion.press_feedback(cancel_btn)

    # ------------------------------------------------------------------

    def _on_output_tokens_edited(self) -> None:
        self._output_tokens_entry.configure(
            border_color=(
                COLORS["input_bg"]
                if formatting.is_valid_int(self._output_tokens_var.get())
                else COLORS["destructive"]
            )
        )

    def _clear_hf_token(self) -> None:
        secrets.delete_hf_token()
        self._hf_token_var.set("")
        self._hf_token_entry.configure(placeholder_text="hf_xxx (optional)")
        self._clear_token_btn.configure(state="disabled")

    def _save(self) -> None:
        if self._keyring_ok:
            new_token = self._hf_token_var.get().strip()
            if new_token:
                secrets.set_hf_token(new_token)

        new_settings = Settings(
            default_output_tokens=formatting.parse_int(
                self._output_tokens_var.get(), self._settings.default_output_tokens
            ),
            theme=self._settings.theme,
            currency=self._currency_var.get(),
            show_chunk_warnings=self._chunk_warnings_var.get(),
            onboarding_dismissed=self._settings.onboarding_dismissed,
        )
        self._parent_shell.settings_store.save(new_settings)
        self._on_save(new_settings)
        self._close()

    def _cancel(self) -> None:
        self._close()

    def _close(self) -> None:
        if self.winfo_exists():
            try:
                self.grab_release()
            except Exception:  # noqa: BLE001
                pass
            self.destroy()
