"""Compare — tokenize one input against many models at once, sorted by cost."""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from norefund.core.compare import (
    CompareReport,
    ModelComparison,
    compare_paths,
    compare_text,
)
from norefund.core.export import comparison_to_csv, comparison_to_markdown
from norefund.core.parsing import SUPPORTED_EXTENSIONS
from norefund.core.portfolio import (
    PortfolioProjection,
    cheapest_that_fits,
    project_costs,
)
from norefund.core.report.html import render_html
from norefund.core.report.model import ReportModel
from norefund.core.report.pdf import render_pdf
from norefund.gui import formatting, motion, native_dialog, theme
from norefund.gui.dnd import enable_file_drop
from norefund.gui.theme import COLORS, SUPPORTED_FILETYPES
from norefund.gui.widgets import (
    ContextBar,
    DropdownButton,
    DropdownItem,
    EmptyState,
    IconButton,
    ModelCheckList,
    StatPill,
    ThreadSafeSchedulerMixin,
    bind_mousewheel,
    card,
    export_via_dialog,
    export_via_dialog_bytes,
)

_FREQUENCY_ITEMS = [
    DropdownItem(value="daily", label="Per day"),
    DropdownItem(value="weekly", label="Per week"),
    DropdownItem(value="monthly", label="Per month"),
]
_DEFAULT_RUNS_PER_PERIOD = "100"
_FREQUENCY_LABELS = {item.value: item.label for item in _FREQUENCY_ITEMS}

_ROW_CONTEXT_BAR_HEIGHT = theme.SPACE_1 + 2  # 6px, denser than the default 8px bar


class CompareView(ThreadSafeSchedulerMixin, ctk.CTkFrame):
    def __init__(self, parent, shell) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.shell = shell
        self._paths: list[Path] = []
        self._report: CompareReport | None = None
        self._last_projections: list[PortfolioProjection] = []
        self._last_projection_frequency: str | None = None
        self._running = False
        self.cancel_event: threading.Event | None = None
        self._active_tab = "results"

        self._build_layout()

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
        self._build_input_card(left)
        self._build_models_card(left)

        right = ctk.CTkFrame(body, fg_color=COLORS["bg"])
        right.grid(
            row=0, column=1, sticky="nsew", padx=(theme.SPACE_2, theme.SPACE_4),
            pady=theme.SPACE_4,
        )
        self._build_results_area(right)

    def _build_input_card(self, parent) -> None:
        card_frame = card(parent)
        card_frame.pack(fill="x", pady=(0, theme.SPACE_3))
        inner = ctk.CTkFrame(card_frame, fg_color="transparent")
        inner.pack(fill="x", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)

        ctk.CTkLabel(
            inner,
            text="Input",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["fg"],
        ).pack(anchor="w", pady=(0, theme.SPACE_2))

        self._text_box = ctk.CTkTextbox(
            inner,
            height=150,
            fg_color=COLORS["input_bg"],
            font=theme.font(theme.FONT_LABEL),
        )
        self._text_box.pack(fill="x", pady=(0, theme.SPACE_2))
        enable_file_drop(inner, self._on_files_dropped, suffixes=SUPPORTED_EXTENSIONS)

        picker_row = ctk.CTkFrame(inner, fg_color="transparent")
        picker_row.pack(fill="x", pady=(0, theme.SPACE_2))
        IconButton(
            picker_row, "Pick File", icon="file_text", command=self._pick_file
        ).pack(side="left", padx=(0, theme.SPACE_2))
        IconButton(
            picker_row, "Pick Folder", icon="folder_open", command=self._pick_folder
        ).pack(side="left")

        self._paths_container = ctk.CTkFrame(inner, fg_color="transparent")
        self._paths_container.pack(fill="x")

        out_row = ctk.CTkFrame(inner, fg_color="transparent")
        out_row.pack(fill="x", pady=(theme.SPACE_3, 0))
        ctk.CTkLabel(
            out_row,
            text="Est. output tokens:",
            font=theme.font(theme.FONT_BODY),
            text_color=COLORS["muted_fg"],
        ).pack(side="left", padx=(0, theme.SPACE_2))
        self._output_var = ctk.StringVar(
            value=str(self.shell.settings.default_output_tokens)
        )
        entry = ctk.CTkEntry(
            out_row,
            textvariable=self._output_var,
            width=90,
            font=theme.mono_font(theme.FONT_BODY),
            fg_color=COLORS["input_bg"],
            border_width=0,
        )
        entry.pack(side="left")
        entry.bind("<KeyRelease>", lambda _e: self._on_output_tokens_change())

        self._run_btn = IconButton(
            inner, "Compare", icon="zap", variant="primary", command=self._run_compare
        )
        self._run_btn.pack(fill="x", pady=(theme.SPACE_3, 0))

    def _build_models_card(self, parent) -> None:
        card_frame = card(parent)
        card_frame.pack(fill="x", pady=(0, theme.SPACE_3))
        inner = ctk.CTkFrame(card_frame, fg_color="transparent")
        inner.pack(fill="both", padx=theme.CARD_PAD_X, pady=theme.CARD_PAD_Y)

        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x", pady=(0, theme.SPACE_2))
        ctk.CTkLabel(
            header,
            text="Models",
            font=theme.font(theme.FONT_BODY, "bold"),
            text_color=COLORS["fg"],
        ).pack(side="left")

        self._check_list = ModelCheckList(inner, self.shell.models, height=260)
        self._check_list.pack(fill="both", expand=True)

    def _build_results_area(self, parent) -> None:
        self._build_tabs(parent)

        content = ctk.CTkFrame(parent, fg_color=COLORS["bg"])
        content.pack(fill="both", expand=True)

        self._results_frame = ctk.CTkFrame(content, fg_color=COLORS["bg"])
        self._build_results_tab(self._results_frame)

        self._projection_frame = ctk.CTkFrame(content, fg_color=COLORS["bg"])
        self._build_projection_tab(self._projection_frame)

        for frame in (self._results_frame, self._projection_frame):
            frame.place(x=0, y=0, relwidth=1, relheight=1)
        self._results_frame.tkraise()

    def _build_tabs(self, parent) -> None:
        tabs = ctk.CTkFrame(parent, fg_color="transparent")
        tabs.pack(fill="x", pady=(0, theme.SPACE_2))
        self._tab_buttons: dict[str, ctk.CTkButton] = {}
        for tab_id, label in [("results", "Results"), ("projection", "Projection")]:
            btn = ctk.CTkButton(
                tabs,
                text=label,
                font=theme.font(theme.FONT_LABEL),
                corner_radius=theme.RADIUS_CARD,
                height=theme.CONTROL_MD,
                width=110,
                fg_color="transparent",
                hover_color=COLORS["muted"],
                text_color=COLORS["muted_fg"],
                command=lambda t=tab_id: self._switch_tab(t),
            )
            btn.pack(side="left", padx=(0, theme.SPACE_2))
            motion.press_feedback(btn)
            self._tab_buttons[tab_id] = btn
        self._sync_tab_styles()

    def _sync_tab_styles(self) -> None:
        for tab_id, btn in self._tab_buttons.items():
            active = tab_id == self._active_tab
            btn.configure(
                text_color=COLORS["primary"] if active else COLORS["muted_fg"]
            )

    def _switch_tab(self, tab_id: str) -> None:
        self._active_tab = tab_id
        self._sync_tab_styles()
        if tab_id == "projection":
            self._projection_frame.tkraise()
        else:
            self._results_frame.tkraise()

    def _build_results_tab(self, parent) -> None:
        self._stats_row = ctk.CTkFrame(parent, fg_color="transparent")
        self._stats_row.pack(fill="x", pady=(0, theme.SPACE_2))

        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, theme.SPACE_2))
        IconButton(
            toolbar, "Export CSV", icon="file_text", command=self._export_csv
        ).pack(side="left", padx=(0, theme.SPACE_2))
        IconButton(
            toolbar, "Export MD", icon="file_text", command=self._export_md
        ).pack(side="left", padx=(0, theme.SPACE_2))
        IconButton(
            toolbar, "Export PDF", icon="file_text", command=self._export_pdf
        ).pack(side="left", padx=(0, theme.SPACE_2))
        IconButton(
            toolbar, "Export HTML", icon="file_text", command=self._export_html
        ).pack(side="left")

        self._results_scroll = ctk.CTkScrollableFrame(parent, fg_color=COLORS["bg"])
        self._results_scroll.pack(fill="both", expand=True)
        bind_mousewheel(self._results_scroll)
        self._show_empty_state()

    def _build_projection_tab(self, parent) -> None:
        controls = ctk.CTkFrame(parent, fg_color="transparent")
        controls.pack(fill="x", pady=(0, theme.SPACE_2))
        ctk.CTkLabel(
            controls,
            text="Runs:",
            font=theme.font(theme.FONT_BODY),
            text_color=COLORS["muted_fg"],
        ).pack(side="left", padx=(0, theme.SPACE_2))
        self._runs_var = ctk.StringVar(value=_DEFAULT_RUNS_PER_PERIOD)
        runs_entry = ctk.CTkEntry(
            controls,
            textvariable=self._runs_var,
            width=70,
            font=theme.mono_font(theme.FONT_BODY),
            fg_color=COLORS["input_bg"],
            border_width=0,
        )
        runs_entry.pack(side="left", padx=(0, theme.SPACE_2))
        runs_entry.bind("<KeyRelease>", lambda _e: self._render_projection())
        self._frequency_dropdown = DropdownButton(
            controls,
            _FREQUENCY_ITEMS,
            "daily",
            on_select=lambda _v: self._render_projection(),
            width=140,
        )
        self._frequency_dropdown.pack(side="left")

        self._projection_stats_row = ctk.CTkFrame(parent, fg_color="transparent")
        self._projection_stats_row.pack(fill="x", pady=(0, theme.SPACE_2))

        self._projection_scroll = ctk.CTkScrollableFrame(parent, fg_color=COLORS["bg"])
        self._projection_scroll.pack(fill="both", expand=True)
        bind_mousewheel(self._projection_scroll)
        self._render_projection()

    # ------------------------------------------------------------------
    # Input selection
    # ------------------------------------------------------------------

    def _pick_file(self) -> None:
        paths = native_dialog.ask_open_files(SUPPORTED_FILETYPES)
        if paths:
            self._set_selected_paths([Path(p) for p in paths])

    def _pick_folder(self) -> None:
        folder = native_dialog.ask_directory()
        if folder:
            self._set_selected_paths([Path(folder)])

    def _on_files_dropped(self, paths: list[Path]) -> None:
        self._set_selected_paths(paths)

    def _set_selected_paths(self, paths: list[Path]) -> None:
        self._paths = paths
        for child in self._paths_container.winfo_children():
            child.destroy()
        for path in paths:
            row = ctk.CTkFrame(self._paths_container, fg_color="transparent")
            row.pack(fill="x", pady=(0, theme.SPACE_1))
            ctk.CTkLabel(
                row,
                text="",
                image=theme.icon_image("check", size=14, color=COLORS["primary"]),
            ).pack(side="left", padx=(0, theme.SPACE_2))
            ctk.CTkLabel(
                row,
                text=path.name,
                font=theme.font(theme.FONT_BODY, "bold"),
                text_color=COLORS["fg"],
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

    # ------------------------------------------------------------------
    # Run / cancel
    # ------------------------------------------------------------------

    def _run_compare(self) -> None:
        if self._running:
            return
        models = self._check_list.selected_models()
        if not models:
            return
        text = self._text_box.get("1.0", "end").strip()
        if not self._paths and not text:
            return

        self._running = True
        self.cancel_event = threading.Event()
        self._run_btn.configure(
            text="Cancel",
            image=theme.icon_image("x", size=16, color=COLORS["primary_fg"]),
            command=self._cancel_compare,
            state="normal",
        )
        output_tokens = formatting.parse_int(self._output_var.get())
        paths = list(self._paths)
        cancel_event = self.cancel_event

        threading.Thread(
            target=self._compare_worker,
            args=(text, paths, models, output_tokens, cancel_event),
            daemon=True,
        ).start()

    def _cancel_compare(self) -> None:
        if self.cancel_event is not None:
            self.cancel_event.set()
        self._run_btn.configure(
            text="Cancelling…", image=theme.blank_icon(size=16), state="disabled"
        )

    def _compare_worker(
        self, text, paths, models, output_tokens, cancel_event
    ) -> None:
        try:
            if paths:
                report = compare_paths(
                    paths, models, output_tokens, cancel_event=cancel_event
                )
            else:
                report = compare_text(text, models, output_tokens)
        except Exception as exc:  # noqa: BLE001
            self._schedule(self._on_compare_error, str(exc))
            return
        self._schedule(self._on_compare_complete, report)

    def _on_compare_complete(self, report: CompareReport) -> None:
        if not self.winfo_exists():
            return
        self._reset_busy_state()
        self._report = report
        self._render_results(report)
        self._render_projection()

    def _on_compare_error(self, message: str) -> None:
        if not self.winfo_exists():
            return
        self._reset_busy_state()
        self._show_empty_state(message=message)

    def _reset_busy_state(self) -> None:
        self._running = False
        self.cancel_event = None
        if not self.winfo_exists():
            return
        self._run_btn.configure(
            text="Compare",
            image=theme.icon_image("zap", size=16, color=COLORS["primary_fg"]),
            command=self._run_compare,
            state="normal",
        )

    # ------------------------------------------------------------------
    # What-if: recompute cost only, no re-tokenization
    # ------------------------------------------------------------------

    def _on_output_tokens_change(self) -> None:
        if self._report is None:
            return
        from norefund.core.compare import what_if

        output_tokens = formatting.parse_int(self._output_var.get())
        updated = [
            what_if(r, output_tokens, r.model) for r in self._report.results
        ]
        self._report = CompareReport(
            source_label=self._report.source_label, results=updated
        )
        self._render_results(self._report)
        self._render_projection()

    # ------------------------------------------------------------------
    # Results rendering
    # ------------------------------------------------------------------

    def _show_empty_state(self, message: str | None = None) -> None:
        for child in self._results_scroll.winfo_children():
            child.destroy()
        for child in self._stats_row.winfo_children():
            child.destroy()
        text = message or (
            "Enter text or pick a file, choose models, and click Compare"
        )
        icon = "x_circle" if message else "bar_chart"
        EmptyState(self._results_scroll, icon, text).pack(expand=True, pady=40)

    def _render_results(self, report: CompareReport) -> None:
        for child in self._results_scroll.winfo_children():
            child.destroy()
        for child in self._stats_row.winfo_children():
            child.destroy()

        successful = [r for r in report.results if r.error is None]
        StatPill(self._stats_row, "Source", report.source_label).pack(
            side="left", padx=(0, theme.SPACE_6)
        )
        if successful:
            cheapest = min(successful, key=lambda r: r.total_cost)
            StatPill(
                self._stats_row, "Cheapest", cheapest.model.display_name
            ).pack(side="left", padx=theme.SPACE_6)

        sorted_results = sorted(
            report.results, key=lambda r: (r.error is not None, r.total_cost)
        )
        cheapest_id = cheapest.model.id if successful else None

        for result in sorted_results:
            self._build_result_row(result, is_cheapest=result.model.id == cheapest_id)

    def _build_result_row(self, result: ModelComparison, is_cheapest: bool) -> None:
        row_card = ctk.CTkFrame(
            self._results_scroll,
            fg_color=COLORS["primary"] if is_cheapest else COLORS["card"],
            corner_radius=theme.RADIUS_CARD,
        )
        row_card.pack(fill="x", pady=theme.SPACE_1)
        inner = ctk.CTkFrame(row_card, fg_color="transparent")
        inner.pack(fill="x", padx=theme.SPACE_4, pady=theme.SPACE_3)

        fg = COLORS["primary_fg"] if is_cheapest else COLORS["fg"]
        muted = COLORS["primary_fg"] if is_cheapest else COLORS["muted_fg"]

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(
            top_row,
            text=result.model.display_name,
            font=theme.font(theme.FONT_TITLE, "bold"),
            text_color=fg,
            anchor="w",
        ).pack(side="left")
        if is_cheapest:
            ctk.CTkLabel(
                top_row,
                text="cheapest",
                image=theme.icon_image("check", size=12, color=fg),
                compound="left",
                font=theme.font(theme.FONT_SMALL, "bold"),
                text_color=fg,
            ).pack(side="right")

        if result.error is not None:
            ctk.CTkLabel(
                inner,
                text=result.error,
                image=theme.icon_image(
                    "x_circle", size=14, color=COLORS["destructive"]
                ),
                compound="left",
                font=theme.font(theme.FONT_BODY),
                text_color=COLORS["destructive"],
                anchor="w",
                wraplength=800,
                justify="left",
            ).pack(fill="x", pady=(theme.SPACE_1, 0))
            return

        stats = ctk.CTkFrame(inner, fg_color="transparent")
        stats.pack(fill="x", pady=(theme.SPACE_2, 0))
        tokens_str = formatting.fmt_num(result.token_count)
        if result.tokenizer_is_approximate:
            tokens_str += " (approx.)"
        ctk.CTkLabel(
            stats,
            text=f"Tokens: {tokens_str}",
            font=theme.mono_font(theme.FONT_BODY),
            text_color=muted,
        ).pack(side="left", padx=(0, theme.SPACE_4))

        bar_cell = ctk.CTkFrame(stats, fg_color="transparent")
        bar_cell.pack(side="left", padx=(0, theme.SPACE_4))
        bar = ContextBar(bar_cell, height=_ROW_CONTEXT_BAR_HEIGHT, width=100)
        bar.pack()
        bar.set_value(result.context_usage_pct)
        ctk.CTkLabel(
            stats,
            text=formatting.fmt_context_pct(result.context_usage_pct),
            font=theme.mono_font(theme.FONT_BODY),
            text_color=muted,
        ).pack(side="left", padx=(0, theme.SPACE_4))

        fits_icon = "check_circle" if result.fits_in_context else "x_circle"
        ctk.CTkLabel(
            stats, text="", image=theme.icon_image(fits_icon, size=14, color=muted)
        ).pack(side="left", padx=(0, theme.SPACE_4))

        cost_row = ctk.CTkFrame(inner, fg_color="transparent")
        cost_row.pack(fill="x", pady=(theme.SPACE_1, 0))
        ctk.CTkLabel(
            cost_row,
            text=(
                f"Input {formatting.fmt_cost(result.input_cost)}  ·  "
                f"Output {formatting.fmt_cost(result.output_cost)}  ·  "
                f"Total {formatting.fmt_cost(result.total_cost)}"
            ),
            font=theme.mono_font(theme.FONT_LABEL, "bold"),
            text_color=fg,
            anchor="w",
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Projection tab: extends the last Compare run's per-model token
    # counts across a run frequency. Depends on self._report, so it
    # re-renders whenever a Compare run completes or output tokens change.
    # ------------------------------------------------------------------

    def _render_projection(self) -> None:
        for child in self._projection_scroll.winfo_children():
            child.destroy()
        for child in self._projection_stats_row.winfo_children():
            child.destroy()

        corpus_tokens = (
            {r.model.id: r.token_count for r in self._report.results if r.error is None}
            if self._report is not None
            else {}
        )
        if not corpus_tokens:
            self._last_projections = []
            self._last_projection_frequency = None
            EmptyState(
                self._projection_scroll,
                "bar_chart",
                "Run Compare first to project volume costs",
            ).pack(expand=True, pady=40)
            return

        models = [
            r.model for r in self._report.results if r.model.id in corpus_tokens
        ]
        output_tokens = formatting.parse_int(self._output_var.get())
        runs_per_period = formatting.parse_int(self._runs_var.get())
        frequency = self._frequency_dropdown.selected_value()

        projections = project_costs(
            corpus_tokens, output_tokens, runs_per_period, frequency, models
        )
        self._last_projections = projections
        self._last_projection_frequency = (
            f"{runs_per_period:g} runs {_FREQUENCY_LABELS.get(frequency, frequency)}"
        )
        cheapest = cheapest_that_fits(projections)

        StatPill(
            self._projection_stats_row, "Source", self._report.source_label
        ).pack(side="left", padx=(0, theme.SPACE_6))
        if cheapest is not None:
            StatPill(
                self._projection_stats_row,
                "Cheapest monthly",
                cheapest.model.display_name,
            ).pack(side="left", padx=theme.SPACE_6)

        sorted_projections = sorted(
            projections, key=lambda p: (not p.fits_in_context, p.monthly_cost)
        )
        cheapest_id = cheapest.model.id if cheapest is not None else None
        for projection in sorted_projections:
            self._build_projection_row(
                projection, is_cheapest=projection.model.id == cheapest_id
            )

    def _build_projection_row(
        self, projection: PortfolioProjection, is_cheapest: bool
    ) -> None:
        row_card = ctk.CTkFrame(
            self._projection_scroll,
            fg_color=COLORS["primary"] if is_cheapest else COLORS["card"],
            corner_radius=theme.RADIUS_CARD,
        )
        row_card.pack(fill="x", pady=theme.SPACE_1)
        inner = ctk.CTkFrame(row_card, fg_color="transparent")
        inner.pack(fill="x", padx=theme.SPACE_4, pady=theme.SPACE_3)

        fg = COLORS["primary_fg"] if is_cheapest else COLORS["fg"]

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(
            top_row,
            text=projection.model.display_name,
            font=theme.font(theme.FONT_TITLE, "bold"),
            text_color=fg,
            anchor="w",
        ).pack(side="left")
        if not projection.fits_in_context:
            ctk.CTkLabel(
                top_row,
                text="corpus doesn't fit",
                image=theme.icon_image(
                    "x_circle", size=12, color=COLORS["destructive"]
                ),
                compound="left",
                font=theme.font(theme.FONT_SMALL, "bold"),
                text_color=COLORS["destructive"],
            ).pack(side="right")
        elif is_cheapest:
            ctk.CTkLabel(
                top_row,
                text="cheapest",
                image=theme.icon_image("check", size=12, color=fg),
                compound="left",
                font=theme.font(theme.FONT_SMALL, "bold"),
                text_color=fg,
            ).pack(side="right")

        cost_row = ctk.CTkFrame(inner, fg_color="transparent")
        cost_row.pack(fill="x", pady=(theme.SPACE_2, 0))
        ctk.CTkLabel(
            cost_row,
            text=(
                f"Per run {formatting.fmt_cost(projection.cost_per_run)}  ·  "
                f"Monthly {formatting.fmt_cost(projection.monthly_cost)}  ·  "
                f"Annual {formatting.fmt_cost(projection.annual_cost)}"
            ),
            font=theme.mono_font(theme.FONT_LABEL, "bold"),
            text_color=fg,
            anchor="w",
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_csv(self) -> None:
        export_via_dialog(
            has_data=self._report is not None,
            extension="csv",
            filetype_label="CSV",
            content_fn=lambda: comparison_to_csv(self._report),
        )

    def _export_md(self) -> None:
        export_via_dialog(
            has_data=self._report is not None,
            extension="md",
            filetype_label="Markdown",
            content_fn=lambda: comparison_to_markdown(self._report),
        )

    def _build_report(self) -> ReportModel:
        return ReportModel(
            title="NoRefund Comparison Report",
            generated_at=datetime.now(),
            comparison=self._report,
            portfolio=self._last_projections or None,
            portfolio_frequency_label=self._last_projection_frequency,
        )

    def _export_pdf(self) -> None:
        export_via_dialog_bytes(
            has_data=self._report is not None,
            extension="pdf",
            filetype_label="PDF",
            content_fn=lambda: render_pdf(self._build_report()),
        )

    def _export_html(self) -> None:
        export_via_dialog(
            has_data=self._report is not None,
            extension="html",
            filetype_label="HTML",
            content_fn=lambda: render_html(self._build_report()),
        )
