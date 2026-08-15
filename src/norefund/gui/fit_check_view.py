"""Fit Check — does an open-weight model fit on a given hardware target?

All computation is synchronous, pure `core/selfhost.py` math (no I/O, no
thread) so every control recalculates on the spot, the moment it changes.
"""

from __future__ import annotations

from datetime import datetime

import customtkinter as ctk

from norefund.core.architectures import ModelArchitecture, list_architectures
from norefund.core.hardware_registry import HardwareTarget, list_hardware
from norefund.core.quantization import (
    kv_cache_dtype_display_name,
    list_kv_cache_dtypes,
    list_quantization_levels,
    quantization_display_name,
)
from norefund.core.report.html import render_html
from norefund.core.report.model import ReportModel
from norefund.core.report.pdf import render_pdf
from norefund.core.selfhost import FitResult, evaluate_fit
from norefund.gui import formatting, theme
from norefund.gui.theme import COLORS
from norefund.gui.widgets import (
    ContextBar,
    DropdownButton,
    DropdownItem,
    IconButton,
    StatPill,
    bind_mousewheel,
    card,
    export_via_dialog,
    export_via_dialog_bytes,
    section_label,
)

_DEFAULT_CONTEXT = "8192"
_DEFAULT_QUANTIZATION = "q4_k_m"
_DEFAULT_KV_CACHE_DTYPE = "fp16"


def _vendor_icon(vendor: str) -> ctk.CTkImage:
    """A small brand-color icon for a model's vendor. Vendors with no
    bundled brand mark (e.g. Qwen) get a solid accent-color dot instead --
    every row needs a leading icon of some kind so the model list stays
    aligned (a mix of icon/no-icon rows in the same popover looks broken)."""
    return theme.provider_icon_or_dot(vendor, size=14)


class FitCheckView(ctk.CTkFrame):
    def __init__(self, parent, shell) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.shell = shell
        self._context_edited = False
        self._fit_result: FitResult | None = None
        self._fit_architecture_name = ""
        self._fit_hardware_name = ""
        self._fit_quantization_name = ""
        self._fit_kv_cache_name = ""

        self._architectures = list_architectures()
        self._hardware = list_hardware()
        self._arch_by_id: dict[str, ModelArchitecture] = {
            a.id: a for a in self._architectures
        }
        self._hw_by_id: dict[str, HardwareTarget] = {h.id: h for h in self._hardware}

        self._model_items = [
            DropdownItem(value=a.id, label=a.display_name, icon=_vendor_icon(a.vendor))
            for a in self._architectures
        ]
        self._hw_items = [
            DropdownItem(value=h.id, label=h.display_name) for h in self._hardware
        ]
        self._quant_items = [
            DropdownItem(value=level, label=quantization_display_name(level))
            for level in list_quantization_levels()
        ]
        self._kv_items = [
            DropdownItem(value=dtype, label=kv_cache_dtype_display_name(dtype))
            for dtype in list_kv_cache_dtypes()
        ]

        self._build_layout()
        self._recalculate()

    # ------------------------------------------------------------------
    # Layout -- single pane: results on top, configuration at the bottom.
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"])
        scroll.pack(
            fill="both", expand=True, padx=theme.PAGE_GUTTER, pady=theme.SPACE_5
        )
        bind_mousewheel(scroll)

        self._build_verdict(scroll)
        self._build_utilization_card(scroll)
        self._build_breakdown_card(scroll)
        self._build_concurrency_card(scroll)
        self._build_config_card(scroll)
        self._warnings_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._warnings_frame.pack(fill="x")

    def _build_verdict(self, parent) -> None:
        verdict_row = ctk.CTkFrame(parent, fg_color="transparent")
        verdict_row.pack(fill="x", pady=(0, theme.SPACE_1))
        self._verdict_icon = ctk.CTkLabel(verdict_row, text="")
        self._verdict_icon.pack(side="left", padx=(0, theme.SPACE_2))
        self._verdict_text = ctk.CTkLabel(
            verdict_row,
            text="",
            font=theme.font(theme.FONT_HEADING, "bold"),
            anchor="w",
        )
        self._verdict_text.pack(side="left")

        IconButton(
            verdict_row, "Export PDF", icon="file_text", command=self._export_pdf
        ).pack(side="right", padx=(theme.SPACE_2, 0))
        IconButton(
            verdict_row, "Export HTML", icon="file_text", command=self._export_html
        ).pack(side="right")

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

    def _build_utilization_card(self, parent) -> None:
        util_card = card(parent)
        self._util_card = util_card
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

    def _build_breakdown_card(self, parent) -> None:
        breakdown_card = card(parent)
        breakdown_card.pack(fill="x", pady=(0, theme.SPACE_3))
        grid = ctk.CTkFrame(breakdown_card, fg_color="transparent")
        grid.pack(fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)
        grid.columnconfigure((0, 1, 2), weight=1)
        self._weights_pill = StatPill(grid, "Weights")
        self._weights_pill.grid(row=0, column=0, sticky="w", pady=(0, theme.SPACE_3))
        self._kv_pill = StatPill(grid, "KV cache")
        self._kv_pill.grid(row=0, column=1, sticky="w", pady=(0, theme.SPACE_3))
        self._activation_pill = StatPill(grid, "Activations")
        self._activation_pill.grid(row=0, column=2, sticky="w", pady=(0, theme.SPACE_3))
        self._overhead_pill = StatPill(grid, "Framework overhead")
        self._overhead_pill.grid(row=1, column=0, sticky="w")
        self._total_pill = StatPill(grid, "Total needed")
        self._total_pill.grid(row=1, column=1, sticky="w")
        self._headroom_pill = StatPill(grid, "Headroom")
        self._headroom_pill.grid(row=1, column=2, sticky="w")

    def _build_concurrency_card(self, parent) -> None:
        concurrency_card = card(parent)
        concurrency_card.pack(fill="x", pady=(0, theme.SPACE_4))
        inner = ctk.CTkFrame(concurrency_card, fg_color="transparent")
        inner.pack(fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)
        self._concurrency_pill = StatPill(inner, "Max concurrent requests")
        self._concurrency_pill.pack(anchor="w")

    def _build_config_card(self, parent) -> None:
        config_card = card(parent)
        config_card.pack(fill="x", pady=(0, theme.SPACE_3))
        inner = ctk.CTkFrame(config_card, fg_color="transparent")
        inner.pack(fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)

        section_label(inner, "Configuration").pack(anchor="w", pady=(0, theme.SPACE_3))

        ctk.CTkLabel(
            inner,
            text="Model",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(0, theme.SPACE_2))
        self._model_dropdown = DropdownButton(
            inner, self._model_items, self._architectures[0].id,
            on_select=lambda _v: self._recalculate(),
        )
        self._model_dropdown.pack(fill="x", pady=(0, theme.SPACE_4))

        precision_grid = ctk.CTkFrame(inner, fg_color="transparent")
        precision_grid.pack(fill="x", pady=(0, theme.SPACE_4))
        precision_grid.columnconfigure((0, 1), weight=1)

        quant_col = ctk.CTkFrame(precision_grid, fg_color="transparent")
        quant_col.grid(row=0, column=0, sticky="ew", padx=(0, theme.SPACE_2))
        ctk.CTkLabel(
            quant_col,
            text="Weight quantization",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(0, theme.SPACE_2))
        self._quant_dropdown = DropdownButton(
            quant_col, self._quant_items, _DEFAULT_QUANTIZATION,
            on_select=lambda _v: self._recalculate(),
        )
        self._quant_dropdown.pack(fill="x")

        kv_col = ctk.CTkFrame(precision_grid, fg_color="transparent")
        kv_col.grid(row=0, column=1, sticky="ew", padx=(theme.SPACE_2, 0))
        ctk.CTkLabel(
            kv_col,
            text="KV cache precision",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(0, theme.SPACE_2))
        self._kv_dropdown = DropdownButton(
            kv_col, self._kv_items, _DEFAULT_KV_CACHE_DTYPE,
            on_select=lambda _v: self._recalculate(),
        )
        self._kv_dropdown.pack(fill="x")

        bottom_grid = ctk.CTkFrame(inner, fg_color="transparent")
        bottom_grid.pack(fill="x")
        bottom_grid.columnconfigure((0, 1), weight=1)

        context_col = ctk.CTkFrame(bottom_grid, fg_color="transparent")
        context_col.grid(row=0, column=0, sticky="ew", padx=(0, theme.SPACE_2))
        ctk.CTkLabel(
            context_col,
            text="Context needed",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(0, theme.SPACE_2))
        self._context_var = ctk.StringVar(value=_DEFAULT_CONTEXT)
        entry = ctk.CTkEntry(
            context_col,
            textvariable=self._context_var,
            height=theme.CONTROL_MD,
            font=theme.mono_font(theme.FONT_TITLE),
            fg_color=COLORS["input_bg"],
            border_width=0,
        )
        entry.pack(fill="x")
        self._last_autofilled_context = _DEFAULT_CONTEXT
        entry.bind("<KeyRelease>", self._on_context_edited)

        hw_col = ctk.CTkFrame(bottom_grid, fg_color="transparent")
        hw_col.grid(row=0, column=1, sticky="ew", padx=(theme.SPACE_2, 0))
        ctk.CTkLabel(
            hw_col,
            text="Hardware",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(0, theme.SPACE_2))
        self._hw_dropdown = DropdownButton(
            hw_col, self._hw_items, self._hardware[0].id,
            on_select=lambda _v: self._recalculate(),
        )
        self._hw_dropdown.pack(fill="x")

    # ------------------------------------------------------------------
    # Auto-fill from the last analysis
    # ------------------------------------------------------------------

    def _on_context_edited(self, _event=None) -> None:
        # Gate on the value actually changing, not on any keystroke -- Tab,
        # arrow keys, or a Ctrl+C copy also fire <KeyRelease> without
        # editing the field, and would otherwise permanently disable the
        # on_show() auto-fill for a field the user never actually touched.
        if self._context_var.get() != self._last_autofilled_context:
            self._context_edited = True
        self._recalculate()

    def on_show(self) -> None:
        """Called by MainView whenever this view is navigated to."""
        if not self._context_edited:
            last = getattr(self.shell, "last_analysis_tokens", None)
            if last:
                value = str(last)
                self._context_var.set(value)
                self._last_autofilled_context = value
        self._recalculate()

    # ------------------------------------------------------------------
    # Compute + render
    # ------------------------------------------------------------------

    def _recalculate(self) -> None:
        architecture = self._arch_by_id[self._model_dropdown.selected_value()]
        hardware = self._hw_by_id[self._hw_dropdown.selected_value()]
        quantization = self._quant_dropdown.selected_value()
        kv_cache_dtype = self._kv_dropdown.selected_value()
        context_length = formatting.parse_int(self._context_var.get())

        result = evaluate_fit(
            architecture,
            hardware,
            quantization,
            context_length,
            kv_cache_dtype=kv_cache_dtype,
        )
        self._fit_result = result
        self._fit_architecture_name = architecture.display_name
        self._fit_hardware_name = hardware.display_name
        self._fit_quantization_name = quantization_display_name(quantization)
        self._fit_kv_cache_name = kv_cache_dtype_display_name(kv_cache_dtype)
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
            # Explicit `before=` keeps this pinned right under the verdict row
            # regardless of pack/forget history -- pack() alone would append
            # it after every card currently pack()ed (util/breakdown/etc.).
            self._error_label.pack(
                fill="x", pady=(0, theme.SPACE_3), before=self._util_card
            )
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

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _build_report(self) -> ReportModel:
        return ReportModel(
            title="NoRefund Fit Check Report",
            generated_at=datetime.now(),
            fit=self._fit_result,
            fit_architecture_name=self._fit_architecture_name,
            fit_hardware_name=self._fit_hardware_name,
            fit_quantization_name=self._fit_quantization_name,
            fit_kv_cache_name=self._fit_kv_cache_name,
        )

    def _export_pdf(self) -> None:
        export_via_dialog_bytes(
            has_data=self._fit_result is not None,
            extension="pdf",
            filetype_label="PDF",
            content_fn=lambda: render_pdf(self._build_report()),
        )

    def _export_html(self) -> None:
        export_via_dialog(
            has_data=self._fit_result is not None,
            extension="html",
            filetype_label="HTML",
            content_fn=lambda: render_html(self._build_report()),
        )
