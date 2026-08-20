"""Compare — tokenize one input against many models at once, sorted by cost."""

from __future__ import annotations

import threading
from collections.abc import Callable
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
from norefund.gui import formatting, native_dialog, theme
from norefund.gui.dnd import enable_file_drop
from norefund.gui.theme import COLORS, SUPPORTED_FILETYPES
from norefund.gui.widgets import (
    ContextBar,
    DropdownButton,
    DropdownItem,
    EmptyState,
    IconButton,
    ModelCheckList,
    ProcessingModal,
    StatPill,
    TabBar,
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
        self._processing_modal: ProcessingModal | None = None
        self._active_tab = "results"

        self._build_layout()
        self._sync_run_button_state()

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
        self._text_box.bind(
            "<KeyRelease>", lambda _e: self._sync_input_exclusivity()
        )
        enable_file_drop(inner, self._on_files_dropped, suffixes=SUPPORTED_EXTENSIONS)

        picker_row = ctk.CTkFrame(inner, fg_color="transparent")
        picker_row.pack(fill="x", pady=(0, theme.SPACE_2))
        self._pick_file_btn = IconButton(
            picker_row, "Pick File", icon="file_text", command=self._pick_file
        )
        self._pick_file_btn.pack(side="left", padx=(0, theme.SPACE_2))
        self._pick_folder_btn = IconButton(
            picker_row, "Pick Folder", icon="folder_open", command=self._pick_folder
        )
        self._pick_folder_btn.pack(side="left")

        self._paths_header = ctk.CTkFrame(inner, fg_color="transparent")
        ctk.CTkLabel(
            self._paths_header,
            text="Selected",
            font=theme.font(theme.FONT_SMALL),
            text_color=COLORS["muted_fg"],
        ).pack(side="left")
        IconButton(
            self._paths_header,
            "Clear",
            icon="x_circle",
            variant="muted",
            command=self._clear_paths,
        ).pack(side="right")
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
        self._output_entry = ctk.CTkEntry(
            out_row,
            textvariable=self._output_var,
            width=90,
            font=theme.mono_font(theme.FONT_BODY),
            fg_color=COLORS["input_bg"],
            border_width=1,
            border_color=COLORS["input_bg"],
        )
        self._output_entry.pack(side="left")
        self._output_entry.bind(
            "<KeyRelease>", lambda _e: self._on_output_tokens_change()
        )

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

        self._check_list = ModelCheckList(
            inner, self.shell.models, on_change=self._sync_run_button_state, height=260
        )
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
        tab_bar = TabBar(
            parent,
            [("results", "Results"), ("projection", "Projection")],
            self._active_tab,
            on_change=self._switch_tab,
        )
        tab_bar.pack(fill="x", pady=(0, theme.SPACE_2))

    def _switch_tab(self, tab_id: str) -> None:
        self._active_tab = tab_id
        if tab_id == "projection":
            self._projection_frame.tkraise()
        else:
            self._results_frame.tkraise()

    def _build_results_tab(self, parent) -> None:
        self._stats_row = ctk.CTkFrame(parent, fg_color="transparent")
        self._stats_row.pack(fill="x", pady=(0, theme.SPACE_2))

        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, theme.SPACE_2))
        for label, command in (
            ("Export CSV", self._export_csv),
            ("Export MD", self._export_md),
            ("Export PDF", self._export_pdf),
            ("Export HTML", self._export_html),
        ):
            IconButton(toolbar, label, icon="file_text", command=command).pack(
                side="left", padx=(0, theme.SPACE_2)
            )

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

    def _text_has_content(self) -> bool:
        return bool(self._text_box.get("1.0", "end").strip())

    def _pick_file(self) -> None:
        # Buttons are disabled while text is present, but a drop bypasses
        # button state entirely -- guard here too so text and files can
        # never both end up populated at once.
        if self._text_has_content():
            return
        paths = native_dialog.ask_open_files(SUPPORTED_FILETYPES)
        if paths:
            self._set_selected_paths([Path(p) for p in paths])

    def _pick_folder(self) -> None:
        if self._text_has_content():
            return
        folder = native_dialog.ask_directory()
        if folder:
            self._set_selected_paths([Path(folder)])

    def _on_files_dropped(self, paths: list[Path]) -> None:
        if self._text_has_content():
            return
        self._set_selected_paths(paths)

    def _clear_paths(self) -> None:
        self._set_selected_paths([])

    def _sync_input_exclusivity(self) -> None:
        """Only one input source at a time: files disable the text box,
        typed text disables file picking. Clearing whichever is active
        hands control back to the other."""
        has_files = bool(self._paths)
        self._text_box.configure(state="disabled" if has_files else "normal")
        pick_state = "disabled" if self._text_has_content() else "normal"
        self._pick_file_btn.configure(state=pick_state)
        self._pick_folder_btn.configure(state=pick_state)

    def _set_selected_paths(self, paths: list[Path]) -> None:
        self._paths = paths
        for child in self._paths_container.winfo_children():
            child.destroy()
        if paths:
            self._paths_header.pack(
                fill="x", pady=(0, theme.SPACE_1), before=self._paths_container
            )
        else:
            self._paths_header.pack_forget()
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
        self._sync_input_exclusivity()

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
        self._processing_modal = ProcessingModal(
            self.winfo_toplevel(), "Comparing models…", on_cancel=self._cancel_compare
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
        # compare_text has no cancel_event support at all -- it's one
        # blocking call with no polling point -- so Cancel can't actually
        # interrupt a text-only compare. ProcessingModal.close() (called
        # by the modal itself when its own Cancel is clicked) releases the
        # grab regardless; this just keeps the view's own reference in
        # sync so _reset_busy_state doesn't try to close it again.
        self._processing_modal = None

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

    def destroy(self) -> None:
        # ProcessingModal is a separate CTkToplevel (parented on the app's
        # root window, not this frame), so it would otherwise outlive this
        # view if destroyed mid-run -- the background worker's completion
        # callback would never fire to close it (ThreadSafeSchedulerMixin's
        # _schedule no-ops once winfo_exists() is False).
        if self._processing_modal is not None:
            self._processing_modal.close()
            self._processing_modal = None
        super().destroy()

    def _reset_busy_state(self) -> None:
        self._running = False
        self.cancel_event = None
        if self._processing_modal is not None:
            self._processing_modal.close()
            self._processing_modal = None
        if not self.winfo_exists():
            return
        self._run_btn.configure(
            text="Compare",
            image=theme.icon_image("zap", size=16, color=COLORS["primary_fg"]),
            command=self._run_compare,
        )
        self._sync_run_button_state()

    def _sync_run_button_state(self) -> None:
        """Keep the Run/Compare button's enabled state in sync with model
        selection, instead of only silently no-oping on click with nothing
        selected. Never overrides the busy Cancel/Cancelling state."""
        if self._running:
            return
        has_selection = bool(self._check_list.selected_models())
        self._run_btn.configure(state="normal" if has_selection else "disabled")

    # ------------------------------------------------------------------
    # What-if: recompute cost only, no re-tokenization
    # ------------------------------------------------------------------

    def _on_output_tokens_change(self) -> None:
        self._output_entry.configure(
            border_color=(
                COLORS["input_bg"]
                if formatting.is_valid_int(self._output_var.get())
                else COLORS["destructive"]
            )
        )
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
        # The cheapest row used to recolor the whole card COLORS["primary"],
        # which then made every child that also defaulted to a primary-ish
        # color (the context bar, the "muted" text, a fits-icon tinted
        # "muted") blend into the background it was sitting on -- most
        # visibly, primary_fg-on-primary text is ~2.5:1 contrast, well under
        # WCAG AA. A left accent strip signals "cheapest" without touching
        # the card surface, so every child keeps its own normal semantic
        # color regardless of is_cheapest.
        row_card = ctk.CTkFrame(
            self._results_scroll,
            fg_color=COLORS["card"],
            corner_radius=theme.RADIUS_CARD,
        )
        row_card.pack(fill="x", pady=theme.SPACE_1)
        if is_cheapest:
            ctk.CTkFrame(
                row_card, fg_color=COLORS["primary"], corner_radius=0, width=4
            ).pack(side="left", fill="y")
        inner = ctk.CTkFrame(row_card, fg_color="transparent")
        inner.pack(fill="x", padx=theme.SPACE_4, pady=theme.SPACE_3)

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(
            top_row,
            text=result.model.display_name,
            font=theme.font(theme.FONT_TITLE, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(side="left")
        if is_cheapest:
            ctk.CTkLabel(
                top_row,
                text="cheapest",
                image=theme.icon_image("check", size=12, color=COLORS["fg"]),
                compound="left",
                font=theme.font(theme.FONT_SMALL, "bold"),
                text_color=COLORS["fg"],
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
            text_color=COLORS["muted_fg"],
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
            text_color=COLORS["muted_fg"],
        ).pack(side="left", padx=(0, theme.SPACE_4))

        fits_icon = "check_circle" if result.fits_in_context else "x_circle"
        fits_color = (
            COLORS["primary"] if result.fits_in_context else COLORS["destructive"]
        )
        ctk.CTkLabel(
            stats, text="", image=theme.icon_image(fits_icon, size=14, color=fits_color)
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
            text_color=COLORS["fg"],
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
        # Same left-accent-strip treatment as _build_result_row, and for
        # the same reason: a whole-card COLORS["primary"] fill collided
        # with primary_fg text/icons sitting on it (~2.5:1 contrast).
        row_card = ctk.CTkFrame(
            self._projection_scroll,
            fg_color=COLORS["card"],
            corner_radius=theme.RADIUS_CARD,
        )
        row_card.pack(fill="x", pady=theme.SPACE_1)
        if is_cheapest:
            ctk.CTkFrame(
                row_card, fg_color=COLORS["primary"], corner_radius=0, width=4
            ).pack(side="left", fill="y")
        inner = ctk.CTkFrame(row_card, fg_color="transparent")
        inner.pack(fill="x", padx=theme.SPACE_4, pady=theme.SPACE_3)

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(
            top_row,
            text=projection.model.display_name,
            font=theme.font(theme.FONT_TITLE, "bold"),
            text_color=COLORS["fg"],
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
                image=theme.icon_image("check", size=12, color=COLORS["fg"]),
                compound="left",
                font=theme.font(theme.FONT_SMALL, "bold"),
                text_color=COLORS["fg"],
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
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _do_export(
        self,
        *,
        extension: str,
        filetype_label: str,
        content_fn: Callable[[], str | bytes],
        as_bytes: bool = False,
    ) -> None:
        exporter = export_via_dialog_bytes if as_bytes else export_via_dialog
        exporter(
            has_data=self._report is not None,
            extension=extension,
            filetype_label=filetype_label,
            content_fn=content_fn,
        )

    def _export_csv(self) -> None:
        self._do_export(
            extension="csv",
            filetype_label="CSV",
            content_fn=lambda: comparison_to_csv(self._report),
        )

    def _export_md(self) -> None:
        self._do_export(
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
        self._do_export(
            extension="pdf",
            filetype_label="PDF",
            content_fn=lambda: render_pdf(self._build_report()),
            as_bytes=True,
        )

    def _export_html(self) -> None:
        self._do_export(
            extension="html",
            filetype_label="HTML",
            content_fn=lambda: render_html(self._build_report()),
        )
