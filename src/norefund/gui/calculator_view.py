"""Manual token/cost calculator — no file I/O, pure recompute on input change."""

from __future__ import annotations

import customtkinter as ctk

from norefund.core import costing
from norefund.gui import formatting, theme
from norefund.gui.theme import COLORS
from norefund.gui.widgets import (
    ContextBar,
    ModelDropdownButton,
    bind_mousewheel,
    card,
    section_label,
)


class CalculatorView(ctk.CTkFrame):
    def __init__(self, parent, shell) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.shell = shell

        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"])
        scroll.pack(
            fill="both", expand=True, padx=theme.PAGE_GUTTER, pady=theme.SPACE_5
        )
        bind_mousewheel(scroll)

        ctk.CTkLabel(
            scroll,
            text="Manually estimate token cost for any LLM before making an API call.",
            font=theme.font(theme.FONT_LABEL),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(0, theme.SPACE_4))

        self._build_config_card(scroll)
        self._build_context_card(scroll)
        self._build_cost_card(scroll)

        self._recalculate()

    # ------------------------------------------------------------------

    def _build_config_card(self, parent) -> None:
        card_frame = card(parent)
        card_frame.pack(fill="x", pady=(0, theme.SPACE_4))
        inner = ctk.CTkFrame(card_frame, fg_color="transparent")
        inner.pack(fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)

        ctk.CTkLabel(
            inner,
            text="Model",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(0, theme.SPACE_2))
        self._model_dropdown = ModelDropdownButton(
            inner,
            self.shell.models,
            self.shell.models[0],
            on_select=self._on_model_change,
        )
        self._model_dropdown.pack(fill="x", pady=(0, theme.SPACE_4))

        grid = ctk.CTkFrame(inner, fg_color="transparent")
        grid.pack(fill="x")
        grid.columnconfigure((0, 1), weight=1)

        in_col = ctk.CTkFrame(grid, fg_color="transparent")
        in_col.grid(row=0, column=0, sticky="ew", padx=(0, theme.SPACE_2))
        ctk.CTkLabel(
            in_col,
            text="Input tokens",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(0, theme.SPACE_2))
        self._input_var = ctk.StringVar(value="0")
        input_entry = ctk.CTkEntry(
            in_col,
            textvariable=self._input_var,
            height=theme.CONTROL_MD,
            font=theme.mono_font(theme.FONT_TITLE),
            fg_color=COLORS["input_bg"],
            border_width=0,
        )
        input_entry.pack(fill="x")
        input_entry.bind("<KeyRelease>", lambda _e: self._recalculate())

        out_col = ctk.CTkFrame(grid, fg_color="transparent")
        out_col.grid(row=0, column=1, sticky="ew", padx=(theme.SPACE_2, 0))
        ctk.CTkLabel(
            out_col,
            text="Est. output tokens",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(0, theme.SPACE_2))
        self._output_var = ctk.StringVar(
            value=str(self.shell.settings.default_output_tokens)
        )
        output_entry = ctk.CTkEntry(
            out_col,
            textvariable=self._output_var,
            height=theme.CONTROL_MD,
            font=theme.mono_font(theme.FONT_TITLE),
            fg_color=COLORS["input_bg"],
            border_width=0,
        )
        output_entry.pack(fill="x")
        output_entry.bind("<KeyRelease>", lambda _e: self._recalculate())

    def _build_context_card(self, parent) -> None:
        card_frame = card(parent)
        card_frame.pack(fill="x", pady=(0, theme.SPACE_4))
        inner = ctk.CTkFrame(card_frame, fg_color="transparent")
        inner.pack(fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)

        header_row = ctk.CTkFrame(inner, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, theme.SPACE_2))
        ctk.CTkLabel(
            header_row,
            text="Context window usage",
            font=theme.font(theme.FONT_LABEL, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(side="left")
        self._pct_label = ctk.CTkLabel(
            header_row, text="—", font=theme.mono_font(theme.FONT_LABEL, "bold")
        )
        self._pct_label.pack(side="right")

        self._context_bar = ContextBar(inner)
        self._context_bar.pack(fill="x", pady=(0, theme.SPACE_2))

        self._stat_label = ctk.CTkLabel(
            inner,
            text="",
            font=theme.mono_font(theme.FONT_BODY),
            text_color=COLORS["muted_fg"],
            anchor="w",
        )
        self._stat_label.pack(fill="x", pady=(0, theme.SPACE_2))

        self._status_row = ctk.CTkFrame(inner, fg_color="transparent")
        self._status_row.pack(fill="x")
        self._status_icon = ctk.CTkLabel(self._status_row, text="")
        self._status_icon.pack(side="left", padx=(0, theme.SPACE_2))
        self._status_text = ctk.CTkLabel(
            self._status_row,
            text="",
            font=theme.font(theme.FONT_LABEL),
            anchor="w",
        )
        self._status_text.pack(side="left")

    def _build_cost_card(self, parent) -> None:
        card_frame = card(parent)
        card_frame.pack(fill="x", pady=(0, theme.SPACE_4))
        inner = ctk.CTkFrame(card_frame, fg_color="transparent")
        inner.pack(fill="both", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)

        grid = ctk.CTkFrame(inner, fg_color="transparent")
        grid.pack(fill="x")
        grid.columnconfigure((0, 1, 2), weight=1)

        self._input_cost_label, self._input_rate_label = self._cost_column(
            grid, 0, "Input cost", border=False
        )
        self._output_cost_label, self._output_rate_label = self._cost_column(
            grid, 1, "Output cost", border=True
        )
        self._total_cost_label, self._total_rate_label = self._cost_column(
            grid, 2, "Total cost", border=True
        )

        ctk.CTkFrame(inner, fg_color=COLORS["border"], height=1).pack(
            fill="x", pady=(theme.SPACE_4, theme.SPACE_2)
        )
        ctk.CTkLabel(
            inner,
            text=(
                " Prices are estimates based on locally stored "
                "pricing data and may not reflect current provider rates."
            ),
            image=theme.icon_image("warning", size=14, color=COLORS["primary"]),
            compound="left",
            font=theme.font(theme.FONT_SMALL),
            text_color=COLORS["muted_fg"],
            anchor="w",
            wraplength=800,
            justify="left",
        ).pack(fill="x")

    def _cost_column(self, grid, col: int, label: str, border: bool):
        col_frame = ctk.CTkFrame(
            grid,
            fg_color="transparent",
            border_width=1 if border else 0,
            border_color=COLORS["border"],
        )
        col_frame.grid(
            row=0,
            column=col,
            sticky="nsew",
            padx=(theme.SPACE_4 if border else 0, 0),
        )
        pad_frame = ctk.CTkFrame(col_frame, fg_color="transparent")
        pad_frame.pack(padx=(theme.SPACE_3, 0) if border else 0, fill="x")
        section_label(pad_frame, label).pack(fill="x")
        value_label = ctk.CTkLabel(
            pad_frame,
            text="$0.00",
            font=theme.mono_font(theme.FONT_DISPLAY, "bold"),
            text_color=COLORS["primary"],
            anchor="w",
        )
        value_label.pack(fill="x")
        rate_label = ctk.CTkLabel(
            pad_frame,
            text="",
            font=theme.font(theme.FONT_SMALL),
            text_color=COLORS["muted_fg"],
            anchor="w",
        )
        rate_label.pack(fill="x")
        return value_label, rate_label

    # ------------------------------------------------------------------

    def _on_model_change(self, _model) -> None:
        self._output_var.set(str(self.shell.settings.default_output_tokens))
        self._recalculate()

    def _recalculate(self) -> None:
        model = self._model_dropdown.selected_model()
        input_tokens = formatting.parse_int(self._input_var.get())
        output_tokens = formatting.parse_int(self._output_var.get())

        pct = costing.context_usage_pct(input_tokens, model.context_window)
        fits = costing.fits_in_context(input_tokens, model.context_window)
        in_cost = costing.input_cost(input_tokens, model)
        out_cost = costing.output_cost(output_tokens, model)
        total = in_cost + out_cost

        color = (
            formatting.context_color(pct)
            if self.shell.settings.show_chunk_warnings
            else COLORS["primary"]
        )
        self._pct_label.configure(
            text=formatting.fmt_context_pct(pct), text_color=color
        )
        self._context_bar.set_value(pct, color=color)
        input_str = formatting.fmt_num(input_tokens)
        max_tokens = formatting.fmt_num(model.context_window)
        self._stat_label.configure(
            text=f"{input_str} input tokens · of {max_tokens} max"
        )

        if fits:
            self._status_icon.configure(
                image=theme.icon_image("check_circle", size=16, color=COLORS["primary"])
            )
            self._status_text.configure(
                text="Fits in one context window", text_color=COLORS["muted_fg"]
            )
        else:
            exceed_by = max(0, input_tokens - model.context_window)
            icon_color = (
                COLORS["destructive"]
                if self.shell.settings.show_chunk_warnings
                else COLORS["muted_fg"]
            )
            self._status_icon.configure(
                image=theme.icon_image("x_circle", size=16, color=icon_color)
            )
            exceed_str = formatting.fmt_num(exceed_by)
            self._status_text.configure(
                text=f"Exceeds by {exceed_str} tokens — chunking required",
                text_color=COLORS["muted_fg"],
            )

        self._input_cost_label.configure(text=formatting.fmt_cost(in_cost))
        self._input_rate_label.configure(
            text=f"${model.input_price_per_million:,.2f} / 1M tokens"
        )
        self._output_cost_label.configure(text=formatting.fmt_cost(out_cost))
        self._output_rate_label.configure(
            text=f"${model.output_price_per_million:,.2f} / 1M tokens"
        )
        self._total_cost_label.configure(text=formatting.fmt_cost(total))
        self._total_rate_label.configure(text=f"{model.currency}")
