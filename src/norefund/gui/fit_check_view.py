"""Fit Check — does an open-weight model fit on a given hardware target?

All computation is synchronous, pure `core/selfhost.py` math (no I/O, no
thread) so every control recalculates on the spot, the moment it changes.
"""

from __future__ import annotations

import customtkinter as ctk

from norefund.core.architectures import ModelArchitecture, list_architectures
from norefund.core.hardware_registry import HardwareTarget, list_hardware
from norefund.core.quantization import (
    kv_cache_dtype_display_name,
    list_kv_cache_dtypes,
    list_quantization_levels,
    quantization_display_name,
)
from norefund.core.selfhost import FitResult, evaluate_fit
from norefund.gui import formatting, theme
from norefund.gui.theme import COLORS
from norefund.gui.widgets import ContextBar, StatPill, bind_mousewheel, card

_DEFAULT_CONTEXT = "8192"
_DEFAULT_QUANTIZATION = "q4_k_m"
_DEFAULT_KV_CACHE_DTYPE = "fp16"


class FitCheckView(ctk.CTkFrame):
    def __init__(self, parent, shell) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.shell = shell
        self._context_edited = False

        self._architectures = list_architectures()
        self._hardware = list_hardware()
        self._arch_by_label: dict[str, ModelArchitecture] = {
            a.display_name: a for a in self._architectures
        }
        self._hw_by_label: dict[str, HardwareTarget] = {
            h.display_name: h for h in self._hardware
        }
        self._quant_by_label: dict[str, str] = {
            quantization_display_name(level): level
            for level in list_quantization_levels()
        }
        self._kv_by_label: dict[str, str] = {
            kv_cache_dtype_display_name(dtype): dtype
            for dtype in list_kv_cache_dtypes()
        }

        self._build_layout()
        self._recalculate()

    def _option_menu(self, parent, values: list[str], variable: ctk.StringVar):
        return ctk.CTkOptionMenu(
            parent,
            values=values,
            variable=variable,
            height=theme.CONTROL_MD,
            font=theme.font(theme.FONT_LABEL),
            fg_color=COLORS["input_bg"],
            text_color=COLORS["fg"],
            button_color=COLORS["muted"],
            button_hover_color=COLORS["border"],
            dropdown_fg_color=COLORS["popover"],
            dropdown_text_color=COLORS["popover_fg"],
            dropdown_hover_color=COLORS["muted"],
            command=lambda _v: self._recalculate(),
        )

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        body = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=360)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(body, fg_color=COLORS["bg"], width=360)
        left.grid(
            row=0, column=0, sticky="ns", padx=(theme.SPACE_4, theme.SPACE_2),
            pady=theme.SPACE_4,
        )
        bind_mousewheel(left)
        self._build_model_card(left)
        self._build_precision_card(left)
        self._build_context_card(left)
        self._build_hardware_card(left)

        right = ctk.CTkScrollableFrame(body, fg_color=COLORS["bg"])
        right.grid(
            row=0, column=1, sticky="nsew", padx=(theme.SPACE_2, theme.SPACE_4),
            pady=theme.SPACE_4,
        )
        bind_mousewheel(right)
        self._build_results_area(right)

    def _build_model_card(self, parent) -> None:
        card_frame = card(parent)
        card_frame.pack(fill="x", pady=(0, theme.SPACE_3))
        inner = ctk.CTkFrame(card_frame, fg_color="transparent")
        inner.pack(fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)

        ctk.CTkLabel(
            inner,
            text="Model",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["fg"],
        ).pack(anchor="w", pady=(0, theme.SPACE_2))

        self._model_var = ctk.StringVar(value=self._architectures[0].display_name)
        self._option_menu(
            inner, list(self._arch_by_label.keys()), self._model_var
        ).pack(fill="x")

    def _build_precision_card(self, parent) -> None:
        card_frame = card(parent)
        card_frame.pack(fill="x", pady=(0, theme.SPACE_3))
        inner = ctk.CTkFrame(card_frame, fg_color="transparent")
        inner.pack(fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)

        ctk.CTkLabel(
            inner,
            text="Precision",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["fg"],
        ).pack(anchor="w", pady=(0, theme.SPACE_2))

        quant_labels = list(self._quant_by_label.keys())
        default_quant_label = next(
            (lbl for lbl, key in self._quant_by_label.items()
             if key == _DEFAULT_QUANTIZATION),
            quant_labels[0],
        )
        ctk.CTkLabel(
            inner,
            text="Weight quantization",
            font=theme.font(theme.FONT_SMALL),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x")
        self._quant_var = ctk.StringVar(value=default_quant_label)
        self._option_menu(inner, quant_labels, self._quant_var).pack(
            fill="x", pady=(0, theme.SPACE_3)
        )

        kv_labels = list(self._kv_by_label.keys())
        default_kv_label = next(
            (lbl for lbl, key in self._kv_by_label.items()
             if key == _DEFAULT_KV_CACHE_DTYPE),
            kv_labels[0],
        )
        ctk.CTkLabel(
            inner,
            text="KV cache precision",
            font=theme.font(theme.FONT_SMALL),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x")
        self._kv_var = ctk.StringVar(value=default_kv_label)
        self._option_menu(inner, kv_labels, self._kv_var).pack(fill="x")

    def _build_context_card(self, parent) -> None:
        card_frame = card(parent)
        card_frame.pack(fill="x", pady=(0, theme.SPACE_3))
        inner = ctk.CTkFrame(card_frame, fg_color="transparent")
        inner.pack(fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)

        ctk.CTkLabel(
            inner,
            text="Context needed",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["fg"],
        ).pack(anchor="w", pady=(0, theme.SPACE_2))

        self._context_var = ctk.StringVar(value=_DEFAULT_CONTEXT)
        entry = ctk.CTkEntry(
            inner,
            textvariable=self._context_var,
            height=theme.CONTROL_MD,
            font=theme.mono_font(theme.FONT_TITLE),
            fg_color=COLORS["input_bg"],
            border_width=0,
        )
        entry.pack(fill="x")
        entry.bind("<KeyRelease>", self._on_context_edited)

    def _build_hardware_card(self, parent) -> None:
        card_frame = card(parent)
        card_frame.pack(fill="x", pady=(0, theme.SPACE_3))
        inner = ctk.CTkFrame(card_frame, fg_color="transparent")
        inner.pack(fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)

        ctk.CTkLabel(
            inner,
            text="Hardware",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["fg"],
        ).pack(anchor="w", pady=(0, theme.SPACE_2))

        self._hw_var = ctk.StringVar(value=self._hardware[0].display_name)
        self._option_menu(
            inner, list(self._hw_by_label.keys()), self._hw_var
        ).pack(fill="x")

    def _build_results_area(self, parent) -> None:
        self._verdict_row = ctk.CTkFrame(parent, fg_color="transparent")
        self._verdict_row.pack(fill="x", pady=(0, theme.SPACE_1))
        self._verdict_icon = ctk.CTkLabel(self._verdict_row, text="")
        self._verdict_icon.pack(side="left", padx=(0, theme.SPACE_2))
        self._verdict_text = ctk.CTkLabel(
            self._verdict_row,
            text="",
            font=theme.font(theme.FONT_HEADING, "bold"),
            anchor="w",
        )
        self._verdict_text.pack(side="left")

        self._error_label = ctk.CTkLabel(
            parent,
            text="",
            image=theme.icon_image("x_circle", size=14, color=COLORS["destructive"]),
            compound="left",
            font=theme.font(theme.FONT_BODY),
            text_color=COLORS["destructive"],
            anchor="w",
            wraplength=800,
            justify="left",
        )

        util_card = card(parent)
        util_card.pack(fill="x", pady=(theme.SPACE_2, theme.SPACE_3))
        util_inner = ctk.CTkFrame(util_card, fg_color="transparent")
        util_inner.pack(fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)
        util_header = ctk.CTkFrame(util_inner, fg_color="transparent")
        util_header.pack(fill="x", pady=(0, theme.SPACE_2))
        ctk.CTkLabel(
            util_header,
            text="VRAM utilization",
            font=theme.font(theme.FONT_LABEL, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(side="left")
        self._util_pct_label = ctk.CTkLabel(
            util_header, text="—", font=theme.mono_font(theme.FONT_LABEL, "bold")
        )
        self._util_pct_label.pack(side="right")
        self._util_bar = ContextBar(util_inner)
        self._util_bar.pack(fill="x")

        breakdown_card = card(parent)
        breakdown_card.pack(fill="x", pady=(0, theme.SPACE_3))
        self._breakdown_grid = ctk.CTkFrame(breakdown_card, fg_color="transparent")
        self._breakdown_grid.pack(
            fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y
        )
        self._breakdown_grid.columnconfigure((0, 1, 2), weight=1)
        self._weights_pill = StatPill(self._breakdown_grid, "Weights")
        self._weights_pill.grid(row=0, column=0, sticky="w", pady=(0, theme.SPACE_3))
        self._kv_pill = StatPill(self._breakdown_grid, "KV cache")
        self._kv_pill.grid(row=0, column=1, sticky="w", pady=(0, theme.SPACE_3))
        self._activation_pill = StatPill(self._breakdown_grid, "Activations")
        self._activation_pill.grid(row=0, column=2, sticky="w", pady=(0, theme.SPACE_3))
        self._overhead_pill = StatPill(self._breakdown_grid, "Framework overhead")
        self._overhead_pill.grid(row=1, column=0, sticky="w")
        self._total_pill = StatPill(self._breakdown_grid, "Total needed")
        self._total_pill.grid(row=1, column=1, sticky="w")
        self._headroom_pill = StatPill(self._breakdown_grid, "Headroom")
        self._headroom_pill.grid(row=1, column=2, sticky="w")

        concurrency_card = card(parent)
        concurrency_card.pack(fill="x", pady=(0, theme.SPACE_3))
        concurrency_inner = ctk.CTkFrame(concurrency_card, fg_color="transparent")
        concurrency_inner.pack(fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)
        self._concurrency_pill = StatPill(
            concurrency_inner, "Max concurrent requests"
        )
        self._concurrency_pill.pack(anchor="w")

        self._warnings_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._warnings_frame.pack(fill="x")

    # ------------------------------------------------------------------
    # Auto-fill from the last analysis
    # ------------------------------------------------------------------

    def _on_context_edited(self, _event=None) -> None:
        self._context_edited = True
        self._recalculate()

    def on_show(self) -> None:
        """Called by MainView whenever this view is navigated to."""
        if not self._context_edited:
            last = getattr(self.shell, "last_analysis_tokens", None)
            if last:
                self._context_var.set(str(last))
        self._recalculate()

    # ------------------------------------------------------------------
    # Compute + render
    # ------------------------------------------------------------------

    def _recalculate(self) -> None:
        architecture = self._arch_by_label[self._model_var.get()]
        hardware = self._hw_by_label[self._hw_var.get()]
        quantization = self._quant_by_label[self._quant_var.get()]
        kv_cache_dtype = self._kv_by_label[self._kv_var.get()]
        context_length = formatting.parse_int(self._context_var.get())

        result = evaluate_fit(
            architecture,
            hardware,
            quantization,
            context_length,
            kv_cache_dtype=kv_cache_dtype,
        )
        self._render_result(result)

    def _render_result(self, result: FitResult) -> None:
        if result.error is not None:
            self._verdict_icon.configure(
                image=theme.icon_image("x_circle", size=20, color=COLORS["destructive"])
            )
            self._verdict_text.configure(
                text="Can't estimate", text_color=COLORS["destructive"]
            )
            self._error_label.configure(text=result.error)
            self._error_label.pack(fill="x", pady=(0, theme.SPACE_3))
            self._util_bar.set_value(None)
            self._util_pct_label.configure(text="—")
            for pill in (
                self._weights_pill, self._kv_pill, self._activation_pill,
                self._overhead_pill, self._total_pill, self._headroom_pill,
            ):
                pill.set_text("—")
            self._concurrency_pill.set_text("—")
            self._render_warnings(())
            return

        self._error_label.pack_forget()

        assert result.estimate is not None
        verdict_icon = "check_circle" if result.fits else "x_circle"
        verdict_color = COLORS["primary"] if result.fits else COLORS["destructive"]
        verdict_text = "Fits on this hardware" if result.fits else "Does not fit"
        self._verdict_icon.configure(
            image=theme.icon_image(verdict_icon, size=20, color=verdict_color)
        )
        self._verdict_text.configure(text=verdict_text, text_color=verdict_color)

        self._util_bar.set_value(result.utilization_pct)
        self._util_pct_label.configure(
            text=formatting.fmt_context_pct(result.utilization_pct),
            text_color=formatting.context_color(result.utilization_pct),
        )

        self._weights_pill.set_text(formatting.fmt_bytes(result.estimate.weights_bytes))
        self._kv_pill.set_text(formatting.fmt_bytes(result.estimate.kv_cache_bytes))
        self._activation_pill.set_text(
            formatting.fmt_bytes(result.estimate.activation_bytes)
        )
        self._overhead_pill.set_text(
            formatting.fmt_bytes(result.estimate.framework_overhead_bytes)
        )
        self._total_pill.set_text(formatting.fmt_bytes(result.estimate.total_bytes))
        self._headroom_pill.set_text(self._fmt_headroom(result.headroom_bytes))

        self._concurrency_pill.set_text(
            formatting.fmt_num(result.max_concurrent_requests)
            if result.max_concurrent_requests is not None
            else "—"
        )

        self._render_warnings(result.warnings)

    @staticmethod
    def _fmt_headroom(headroom_bytes: int | None) -> str:
        if headroom_bytes is None:
            return "—"
        if headroom_bytes < 0:
            return f"-{formatting.fmt_bytes(-headroom_bytes)} over"
        return formatting.fmt_bytes(headroom_bytes)

    def _render_warnings(self, warnings: tuple[str, ...]) -> None:
        for child in self._warnings_frame.winfo_children():
            child.destroy()
        for message in warnings:
            ctk.CTkLabel(
                self._warnings_frame,
                text=message,
                image=theme.icon_image("warning", size=14, color=COLORS["warning"]),
                compound="left",
                font=theme.font(theme.FONT_BODY),
                text_color=COLORS["muted_fg"],
                anchor="w",
                wraplength=800,
                justify="left",
            ).pack(fill="x", pady=(0, theme.SPACE_2))
