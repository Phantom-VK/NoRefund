"""Token calculator screen."""

from __future__ import annotations

import customtkinter as ctk

from norefund.core.costing import context_usage_pct, fits_in_context, min_chunks
from norefund.core.models_registry import ModelInfo
from norefund.gui.formatting import (
    context_color,
    fmt_cost,
    fmt_float,
    fmt_num,
    parse_int,
)
from norefund.gui.theme import COLORS
from norefund.gui.widgets import ContextBar, ModelDropdown, StatPill


class CalculatorView(ctk.CTkFrame):
    def __init__(
        self, parent, models: list[ModelInfo], default_output: ctk.StringVar
    ) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.models = models
        self.default_output = default_output
        self.input_tokens = ctk.StringVar(value="10000")
        self.output_tokens = ctk.StringVar(value=default_output.get())

        self._build()
        self._recalculate()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        shell = ctk.CTkScrollableFrame(self, fg_color="transparent")
        shell.grid(row=0, column=0, sticky="nsew", padx=24, pady=20)
        shell.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            shell,
            text="Token Calculator",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=COLORS["text"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            shell,
            text="Manually estimate token cost for any LLM before making an API call.",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(2, 18))

        config = self._card(shell)
        config.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        ctk.CTkLabel(
            config,
            text="CONFIGURATION",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["muted_text"],
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 10))
        self.model_select = ModelDropdown(
            config, self.models, command=lambda _: self._recalculate()
        )
        self.model_select.pack(fill="x", padx=18, pady=(0, 14))

        inputs = ctk.CTkFrame(config, fg_color="transparent")
        inputs.pack(fill="x", padx=18, pady=(0, 18))
        inputs.grid_columnconfigure((0, 1), weight=1, uniform="calc")
        self._input_block(inputs, "Input tokens", self.input_tokens, 0)
        self._input_block(inputs, "Est. output tokens", self.output_tokens, 1)

        context = self._card(shell)
        context.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        top = ctk.CTkFrame(context, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 8))
        ctk.CTkLabel(
            top,
            text="CONTEXT WINDOW",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["muted_text"],
        ).pack(side="left")
        self.context_pct_label = ctk.CTkLabel(
            top,
            text="-",
            font=ctk.CTkFont(size=12, weight="bold", family="monospace"),
        )
        self.context_pct_label.pack(side="right")
        self.context_bar = ContextBar(context)
        self.context_bar.pack(fill="x", padx=18, pady=(0, 8))
        self.context_detail = ctk.CTkLabel(
            context,
            text="-",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=12, family="monospace"),
            anchor="w",
        )
        self.context_detail.pack(fill="x", padx=18)
        self.fit_label = ctk.CTkLabel(
            context,
            text="-",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.fit_label.pack(fill="x", padx=18, pady=(8, 16))

        cost = self._card(shell)
        cost.grid(row=4, column=0, sticky="ew")
        ctk.CTkLabel(
            cost,
            text="COST ESTIMATE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["muted_text"],
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 10))
        row = ctk.CTkFrame(cost, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 16))
        row.grid_columnconfigure((0, 1, 2), weight=1, uniform="cost")
        self.input_cost = StatPill(row, "Input")
        self.output_cost = StatPill(row, "Output")
        self.total_cost = StatPill(row, "Total")
        self.input_cost.grid(row=0, column=0, sticky="ew")
        self.output_cost.grid(row=0, column=1, sticky="ew", padx=12)
        self.total_cost.grid(row=0, column=2, sticky="ew")
        ctk.CTkLabel(
            cost,
            text="Prices are estimates. Check each provider's pricing page for exact rates.",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 16))

    def _card(self, parent) -> ctk.CTkFrame:
        return ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=6)

    def _input_block(
        self, parent, label: str, variable: ctk.StringVar, column: int
    ) -> None:
        block = ctk.CTkFrame(parent, fg_color="transparent")
        block.grid(
            row=0, column=column, sticky="ew", padx=(0, 8) if column == 0 else (8, 0)
        )
        ctk.CTkLabel(
            block, text=label, text_color=COLORS["muted_text"], anchor="w"
        ).pack(fill="x")
        entry = ctk.CTkEntry(
            block, textvariable=variable, fg_color=COLORS["input"], border_width=0
        )
        entry.pack(fill="x", pady=(4, 0))
        variable.trace_add("write", lambda *_: self._recalculate())

    def _recalculate(self) -> None:
        model = self.model_select.selected_model()
        in_tok = parse_int(self.input_tokens.get())
        out_tok = parse_int(self.output_tokens.get())
        in_cost = (in_tok / 1_000_000) * model.input_price_per_million
        out_cost = (out_tok / 1_000_000) * model.output_price_per_million
        pct = context_usage_pct(in_tok, model.context_window)
        color = context_color(pct)

        self.context_bar.set_value(pct)
        self.context_pct_label.configure(text=f"{fmt_float(pct)}%", text_color=color)
        self.context_detail.configure(
            text=f"{fmt_num(in_tok)} input tokens of {fmt_num(model.context_window)} max"
        )
        if fits_in_context(in_tok, model.context_window):
            self.fit_label.configure(
                text="OK  Fits in one context window", text_color=COLORS["primary"]
            )
        else:
            overage = in_tok - model.context_window
            self.fit_label.configure(
                text=(
                    f"Exceeds by {fmt_num(overage)} tokens - "
                    f"{min_chunks(in_tok, model.context_window)} chunks required"
                ),
                text_color=COLORS["danger"],
            )
        self.input_cost.set_text(f"{fmt_cost(in_cost)}  @ ${model.input_price_per_million:g}/M")
        self.output_cost.set_text(f"{fmt_cost(out_cost)}  @ ${model.output_price_per_million:g}/M")
        self.total_cost.set_text(fmt_cost(in_cost + out_cost))
