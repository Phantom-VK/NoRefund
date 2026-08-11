"""Compare — tokenize one input against many models at once, sorted by cost."""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import TclError, filedialog

import customtkinter as ctk

from norefund.core.compare import (
    CompareReport,
    ModelComparison,
    compare_paths,
    compare_text,
)
from norefund.core.export import comparison_to_csv, comparison_to_markdown
from norefund.core.parsing import SUPPORTED_EXTENSIONS
from norefund.gui import formatting, theme
from norefund.gui.dnd import enable_file_drop
from norefund.gui.theme import COLORS, ICONS, SUPPORTED_FILETYPES
from norefund.gui.widgets import ContextBar, IconButton, ModelCheckList, StatPill


class CompareView(ctk.CTkFrame):
    def __init__(self, parent, shell) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.shell = shell
        self._paths: list[Path] = []
        self._report: CompareReport | None = None
        self._running = False
        self.cancel_event: threading.Event | None = None

        self._build_layout()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        body = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=320)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(body, fg_color=COLORS["bg"], width=320)
        left.grid(row=0, column=0, sticky="ns", padx=(16, 8), pady=16)
        self._build_input_card(left)
        self._build_models_card(left)

        right = ctk.CTkFrame(body, fg_color=COLORS["bg"])
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)
        self._build_results_area(right)

    def _card(self, parent) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=6)
        card.pack(fill="x", pady=(0, 12))
        return card

    def _build_input_card(self, parent) -> None:
        card = self._card(parent)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=14)

        ctk.CTkLabel(
            inner, text="Input", font=theme.font(11, "bold"), text_color=COLORS["fg"]
        ).pack(anchor="w", pady=(0, 8))

        self._text_box = ctk.CTkTextbox(
            inner, height=140, fg_color=COLORS["input_bg"], font=theme.font(12)
        )
        self._text_box.pack(fill="x", pady=(0, 8))
        enable_file_drop(inner, self._on_files_dropped, suffixes=SUPPORTED_EXTENSIONS)

        picker_row = ctk.CTkFrame(inner, fg_color="transparent")
        picker_row.pack(fill="x", pady=(0, 8))
        IconButton(
            picker_row, "Pick File", icon="file_text", command=self._pick_file
        ).pack(side="left", padx=(0, 6))
        IconButton(
            picker_row, "Pick Folder", icon="folder_open", command=self._pick_folder
        ).pack(side="left")

        self._paths_label = ctk.CTkLabel(
            inner,
            text="",
            font=theme.font(10),
            text_color=COLORS["muted_fg"],
            anchor="w",
            wraplength=280,
            justify="left",
        )
        self._paths_label.pack(fill="x")

        out_row = ctk.CTkFrame(inner, fg_color="transparent")
        out_row.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(
            out_row,
            text="Est. output tokens:",
            font=theme.font(11),
            text_color=COLORS["muted_fg"],
        ).pack(side="left", padx=(0, 6))
        self._output_var = ctk.StringVar(
            value=str(self.shell.settings.default_output_tokens)
        )
        entry = ctk.CTkEntry(
            out_row,
            textvariable=self._output_var,
            width=90,
            font=theme.mono_font(11),
            fg_color=COLORS["input_bg"],
            border_width=0,
        )
        entry.pack(side="left")
        entry.bind("<KeyRelease>", lambda _e: self._on_output_tokens_change())

        self._run_btn = IconButton(
            inner, "Compare", icon="zap", variant="primary", command=self._run_compare
        )
        self._run_btn.pack(fill="x", pady=(10, 0))

    def _build_models_card(self, parent) -> None:
        card = self._card(parent)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", padx=14, pady=14)

        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            header, text="Models", font=theme.font(11, "bold"), text_color=COLORS["fg"]
        ).pack(side="left")

        self._check_list = ModelCheckList(inner, self.shell.models, height=220)
        self._check_list.pack(fill="both", expand=True)

    def _build_results_area(self, parent) -> None:
        self._stats_row = ctk.CTkFrame(parent, fg_color="transparent")
        self._stats_row.pack(fill="x", pady=(0, 8))

        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 8))
        IconButton(
            toolbar, "Export CSV", icon="file_text", command=self._export_csv
        ).pack(side="left", padx=(0, 6))
        IconButton(
            toolbar, "Export MD", icon="file_text", command=self._export_md
        ).pack(side="left")

        self._results_scroll = ctk.CTkScrollableFrame(parent, fg_color=COLORS["bg"])
        self._results_scroll.pack(fill="both", expand=True)
        self._show_empty_state()

    # ------------------------------------------------------------------
    # Input selection
    # ------------------------------------------------------------------

    def _pick_file(self) -> None:
        paths = filedialog.askopenfilenames(filetypes=SUPPORTED_FILETYPES)
        if paths:
            self._paths = [Path(p) for p in paths]
            self._paths_label.configure(text="\n".join(str(p) for p in self._paths))

    def _pick_folder(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self._paths = [Path(folder)]
            self._paths_label.configure(text=str(folder))

    def _on_files_dropped(self, paths: list[Path]) -> None:
        self._paths = paths
        self._paths_label.configure(text="\n".join(str(p) for p in paths))

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
            text=f"{ICONS['x']} Cancel", command=self._cancel_compare, state="normal"
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
        self._run_btn.configure(text="Cancelling…", state="disabled")

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

    def _on_compare_error(self, message: str) -> None:
        if not self.winfo_exists():
            return
        self._reset_busy_state()
        self._show_empty_state(message=f"{ICONS['x_circle']} {message}")

    def _reset_busy_state(self) -> None:
        self._running = False
        self.cancel_event = None
        if not self.winfo_exists():
            return
        self._run_btn.configure(
            text=f"{ICONS['zap']} Compare", command=self._run_compare, state="normal"
        )

    def _schedule(self, callback, *args) -> None:
        try:
            if not self.winfo_exists():
                return
            self.after(0, callback, *args)
        except (TclError, RuntimeError):
            pass

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

    # ------------------------------------------------------------------
    # Results rendering
    # ------------------------------------------------------------------

    def _show_empty_state(self, message: str | None = None) -> None:
        for child in self._results_scroll.winfo_children():
            child.destroy()
        for child in self._stats_row.winfo_children():
            child.destroy()
        text = message or (
            f"{ICONS['bar_chart']}\n\nEnter text or pick a file, choose models, "
            "and click Compare"
        )
        ctk.CTkLabel(
            self._results_scroll,
            text=text,
            font=theme.font(13),
            text_color=COLORS["muted_fg"],
            justify="center",
        ).pack(expand=True, pady=40)

    def _render_results(self, report: CompareReport) -> None:
        for child in self._results_scroll.winfo_children():
            child.destroy()
        for child in self._stats_row.winfo_children():
            child.destroy()

        successful = [r for r in report.results if r.error is None]
        StatPill(self._stats_row, "Source", report.source_label).pack(
            side="left", padx=(0, 24)
        )
        if successful:
            cheapest = min(successful, key=lambda r: r.total_cost)
            StatPill(
                self._stats_row, "Cheapest", cheapest.model.display_name
            ).pack(side="left", padx=24)

        sorted_results = sorted(
            report.results, key=lambda r: (r.error is not None, r.total_cost)
        )
        cheapest_id = cheapest.model.id if successful else None

        for result in sorted_results:
            self._build_result_row(result, is_cheapest=result.model.id == cheapest_id)

    def _build_result_row(self, result: ModelComparison, is_cheapest: bool) -> None:
        card = ctk.CTkFrame(
            self._results_scroll,
            fg_color=COLORS["primary"] if is_cheapest else COLORS["card"],
            corner_radius=6,
        )
        card.pack(fill="x", pady=4)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        fg = COLORS["primary_fg"] if is_cheapest else COLORS["fg"]
        muted = COLORS["primary_fg"] if is_cheapest else COLORS["muted_fg"]

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(
            top_row,
            text=result.model.display_name,
            font=theme.font(13, "bold"),
            text_color=fg,
            anchor="w",
        ).pack(side="left")
        if is_cheapest:
            ctk.CTkLabel(
                top_row,
                text=f"{ICONS['check']} cheapest",
                font=theme.font(10, "bold"),
                text_color=fg,
            ).pack(side="right")

        if result.error is not None:
            ctk.CTkLabel(
                inner,
                text=f"{ICONS['x_circle']} {result.error}",
                font=theme.font(11),
                text_color=COLORS["destructive"],
                anchor="w",
                wraplength=500,
                justify="left",
            ).pack(fill="x", pady=(4, 0))
            return

        stats = ctk.CTkFrame(inner, fg_color="transparent")
        stats.pack(fill="x", pady=(6, 0))
        tokens_str = formatting.fmt_num(result.token_count)
        if result.tokenizer_is_approximate:
            tokens_str += " (approx.)"
        ctk.CTkLabel(
            stats,
            text=f"Tokens: {tokens_str}",
            font=theme.mono_font(11),
            text_color=muted,
        ).pack(side="left", padx=(0, 16))

        bar_cell = ctk.CTkFrame(stats, fg_color="transparent")
        bar_cell.pack(side="left", padx=(0, 16))
        bar = ContextBar(bar_cell, height=5, width=100)
        bar.pack()
        bar.set_value(result.context_usage_pct)
        ctk.CTkLabel(
            stats,
            text=formatting.fmt_context_pct(result.context_usage_pct),
            font=theme.mono_font(11),
            text_color=muted,
        ).pack(side="left", padx=(0, 16))

        fits_icon = (
            ICONS["check_circle"] if result.fits_in_context else ICONS["x_circle"]
        )
        ctk.CTkLabel(
            stats, text=fits_icon, font=theme.font(11), text_color=muted
        ).pack(side="left", padx=(0, 16))

        cost_row = ctk.CTkFrame(inner, fg_color="transparent")
        cost_row.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(
            cost_row,
            text=(
                f"Input {formatting.fmt_cost(result.input_cost)}  ·  "
                f"Output {formatting.fmt_cost(result.output_cost)}  ·  "
                f"Total {formatting.fmt_cost(result.total_cost)}"
            ),
            font=theme.mono_font(12, "bold"),
            text_color=fg,
            anchor="w",
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_csv(self) -> None:
        if self._report is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")]
        )
        if path:
            csv_text = comparison_to_csv(self._report)
            Path(path).write_text(csv_text, encoding="utf-8")

    def _export_md(self) -> None:
        if self._report is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".md", filetypes=[("Markdown", "*.md")]
        )
        if path:
            md_text = comparison_to_markdown(self._report)
            Path(path).write_text(md_text, encoding="utf-8")
