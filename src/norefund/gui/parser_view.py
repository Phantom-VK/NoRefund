"""File parser and analysis screen."""

from __future__ import annotations

import json
import logging
import threading
import traceback
from pathlib import Path
from tkinter import TclError, filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from norefund.core.costing import output_cost
from norefund.core.models_registry import ModelInfo
from norefund.core.service import AnalysisResult, analyze_file, analyze_folder
from norefund.gui.formatting import (
    context_color,
    fmt_cost,
    fmt_float,
    fmt_num,
    parse_int,
)
from norefund.gui.theme import COLORS, ICONS, SUPPORTED_FILETYPES, mono_font
from norefund.gui.theme import font as themed_font
from norefund.gui.widgets import ContextBar, IconButton, ModelDropdown, StatPill
from norefund.logging_config import latest_log_file

_LOG = logging.getLogger(__name__)


def _tail_lines(path: Path, n: int = 200, max_bytes: int = 32_000) -> list[str]:
    """Read the last `n` lines from `path` without loading the whole file."""
    with path.open("rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - max_bytes))
        return f.read().decode("utf-8", errors="ignore").splitlines()[-n:]


class ResultsTable(ctk.CTkScrollableFrame):
    HEADERS = ["File", "Tokens", "Context %", "Fits?", "Chunks", "Input Cost", "Words", "Chars"]
    WIDTHS   = [230, 90, 130, 70, 70, 100, 90, 90]

    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self._draw_header()

    def _draw_header(self) -> None:
        for col, (header, width) in enumerate(zip(self.HEADERS, self.WIDTHS)):
            ctk.CTkLabel(
                self,
                text=header.upper(),
                width=width,
                fg_color=COLORS["muted"],
                text_color=COLORS["muted_text"],
                font=themed_font(10, "bold"),
                anchor="w",
                corner_radius=0,
            ).grid(row=0, column=col, sticky="ew", padx=(0, 1), pady=(0, 1))

    def clear(self) -> None:
        for child in self.winfo_children():
            info = child.grid_info()
            if info and int(info["row"]) > 0:
                child.destroy()

    def set_results(self, results: list[AnalysisResult]) -> None:
        self.clear()
        for idx, result in enumerate(results, start=1):
            self._add_row(idx, result)

    def _add_row(self, row: int, result: AnalysisResult) -> None:
        bg  = COLORS["card"] if row % 2 else COLORS["bg"]
        pct = result.context_usage_pct

        pct_str    = f"{fmt_float(pct)}%" if pct is not None else "—"
        pct_color  = context_color(pct) if pct is not None else COLORS["muted_text"]
        fits_color = COLORS["primary"] if result.fits_in_context else COLORS["danger"]

        name = Path(result.file_path).name
        if result.error:
            name = f"⚠ {name}"

        text_values = {
            0: name,
            1: fmt_num(result.token_count),
            4: str(result.min_chunks_needed),
            5: fmt_cost(result.estimated_input_cost),
            6: fmt_num(result.word_count),
            7: fmt_num(result.char_count),
        }

        for col, width in enumerate(self.WIDTHS):
            if col == 2:
                cell = ctk.CTkFrame(
                    self, fg_color=bg, corner_radius=0, width=width, height=28
                )
                cell.grid_propagate(False)
                bar_wrap = ctk.CTkFrame(
                    cell, fg_color="transparent", width=44, height=5
                )
                bar_wrap.place(relx=0, rely=0.5, x=6, anchor="w")
                bar_wrap.pack_propagate(False)
                bar = ContextBar(bar_wrap, height=5)
                bar.pack(fill="x", expand=True)
                bar.set_value(pct)
                ctk.CTkLabel(
                    cell,
                    text=pct_str,
                    text_color=pct_color,
                    font=mono_font(12, "bold"),
                    anchor="w",
                ).place(relx=0, rely=0.5, x=56, anchor="w")
                cell.grid(row=row, column=col, sticky="ew", padx=(0, 1), pady=(0, 1))
                continue
            if col == 3:
                glyph = ICONS["check"] if result.fits_in_context else ICONS["x_circle"]
                ctk.CTkLabel(
                    self,
                    text=glyph,
                    width=width,
                    fg_color=bg,
                    text_color=fits_color,
                    font=themed_font(13, "bold"),
                    anchor="center",
                    corner_radius=0,
                ).grid(row=row, column=col, sticky="ew", padx=(0, 1), pady=(0, 1))
                continue
            ctk.CTkLabel(
                self,
                text=text_values[col],
                width=width,
                fg_color=bg,
                text_color=COLORS["text"],
                font=themed_font(12, "bold" if col in {0, 1, 5} else "normal"),
                anchor="w",
                corner_radius=0,
            ).grid(row=row, column=col, sticky="ew", padx=(0, 1), pady=(0, 1))


_LEVEL_TAGS = {
    "INFO": "info",
    "WARN": "warn",
    "WARNING": "warn",
    "OK": "ok",
    "DONE": "done",
    "ERROR": "err",
    "CRITICAL": "err",
}


class LogsPanel(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.text = ctk.CTkTextbox(
            self,
            fg_color=COLORS["bg"],
            text_color=COLORS["muted_text"],
            font=mono_font(12),
            wrap="none",
        )
        self.text.pack(fill="both", expand=True, padx=18, pady=16)
        self._configure_tags()
        self.refresh()

    def _configure_tags(self) -> None:
        """Colour-code log levels. Resolved once at construction against the
        appearance mode active at that time; won't re-resolve on a later
        theme toggle while this cached view stays alive (cosmetic-only).
        """
        self.text.tag_config("prefix", foreground=COLORS["primary"][1])
        self.text.tag_config("dim", foreground=COLORS["muted_text"][1])
        self.text.tag_config("info", foreground=COLORS["muted_text"][1])
        self.text.tag_config("warn", foreground=COLORS["warning"][1])
        self.text.tag_config("ok", foreground=COLORS["primary"][1])
        self.text.tag_config("done", foreground=COLORS["primary"][1])
        self.text.tag_config("err", foreground=COLORS["danger"][1])

    def refresh(self) -> None:
        """Reload the current run log.

        Reads only the last 32 KB / 200 lines. Each parsed line is inserted
        with a level-specific colour tag; still bounded to <=200 lines so
        the per-line insert cost stays negligible.
        """
        self.text.delete("1.0", "end")
        path = latest_log_file()
        if not path:
            self.text.insert("end", "No logs yet. Run an analysis to see output here.\n")
            return
        try:
            for line in _tail_lines(path):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj     = json.loads(line)
                    ctx     = obj.get("ctx") or {}
                    message = obj.get("message", "log")
                    level   = obj.get("level", "INFO")
                    tag     = _LEVEL_TAGS.get(level, "info")
                    self.text.insert("end", "› ", "prefix")
                    self.text.insert("end", f"[{level}] ", "dim")
                    self.text.insert("end", f"{message} {ctx}\n", tag)
                except json.JSONDecodeError:
                    self.text.insert("end", f"{line}\n")
        except OSError as exc:
            self.text.insert("end", f"Error reading log file: {exc}\n")


class ParserView(ctk.CTkFrame):
    _ANALYZE_LABEL = f"{ICONS['zap']} Analyze"

    def __init__(
        self,
        parent,
        shell,
        models: list[ModelInfo],
        default_output: ctk.StringVar,
    ) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.shell          = shell
        self.models         = models
        self.default_output = default_output
        self.output_tokens  = ctk.StringVar(value=default_output.get())
        self.paths:   list[Path]           = []
        self.results: list[AnalysisResult] = []
        self.active_tab = "results"
        self.status     = ctk.StringVar(value="Ready - add a file or folder to begin.")
        self.analyzing  = False
        self.cancel_event: Optional[threading.Event] = None
        self._files_processed = 0
        self.last_model: Optional[ModelInfo] = None
        self.has_run = False

        self._build()
        self._render_files()
        self._render_results()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0)
        toolbar.grid(row=0, column=0, sticky="ew")
        IconButton(
            toolbar, f"{ICONS['plus']} Add File", width=104, command=self._pick_file
        ).pack(side="left", padx=(18, 6), pady=10)
        IconButton(
            toolbar,
            f"{ICONS['folder_plus']} Add Folder",
            width=114,
            command=self._pick_folder,
        ).pack(side="left", padx=6, pady=10)
        IconButton(
            toolbar,
            f"{ICONS['x']} Clear",
            variant="danger",
            width=82,
            command=self._clear,
        ).pack(side="left", padx=6, pady=10)
        ctk.CTkFrame(toolbar, width=1, fg_color=COLORS["border"]).pack(
            side="left", fill="y", padx=8, pady=14
        )
        self.model_select = ModelDropdown(toolbar, self.models, width=230)
        self.model_select.pack(side="left", padx=(0, 10), pady=10)
        ctk.CTkLabel(
            toolbar,
            text="Est. output:",
            text_color=COLORS["muted_text"],
            font=themed_font(12),
        ).pack(side="left")
        ctk.CTkEntry(
            toolbar,
            textvariable=self.output_tokens,
            width=76,
            fg_color=COLORS["input"],
            border_width=0,
            font=mono_font(12),
        ).pack(side="left", padx=(6, 3), pady=10)
        ctk.CTkLabel(
            toolbar,
            text="tokens",
            text_color=COLORS["muted_text"],
            font=themed_font(12),
        ).pack(side="left")
        self.analyze_btn = IconButton(
            toolbar,
            f"{ICONS['zap']} Analyze",
            variant="primary",
            width=120,
            command=self._run_analysis,
        )
        self.analyze_btn.pack(side="right", padx=18, pady=10)

        self.files_frame = ctk.CTkScrollableFrame(
            self, height=94, fg_color=COLORS["bg"], corner_radius=0
        )
        self.files_frame.grid(row=1, column=0, sticky="ew")

        tabs = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0)
        tabs.grid(row=2, column=0, sticky="ew")
        self.results_tab = IconButton(
            tabs, "Results", width=84, command=lambda: self._set_tab("results")
        )
        self.logs_tab = IconButton(
            tabs, "Logs", width=70, command=lambda: self._set_tab("logs")
        )
        self.results_tab.pack(side="left", padx=(18, 0), pady=8)
        self.logs_tab.pack(side="left",    padx=(4, 0),  pady=8)

        self.content = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.content.grid(row=3, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.results_panel = ctk.CTkFrame(
            self.content, fg_color=COLORS["bg"], corner_radius=0
        )
        # Grid immediately (before children are built) so the whole subtree
        # — including CTkScrollableFrame's internal canvas in ResultsTable —
        # grows up already mapped. Building it fully offscreen and mapping it
        # only later left canvas-backed widgets (CTkLabel, CTkScrollableFrame)
        # with stale/zero geometry that a later grid() didn't fix.
        self.results_panel.grid(row=0, column=0, sticky="nsew")
        self.results_panel.grid_columnconfigure(0, weight=1)
        self.results_panel.grid_rowconfigure(1, weight=1)

        self.summary = ctk.CTkFrame(
            self.results_panel, fg_color=COLORS["card"], corner_radius=0
        )
        self.summary.grid(row=0, column=0, sticky="ew")
        self.summary.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="summary")
        self.stat_files       = StatPill(self.summary, "Files")
        self.stat_tokens      = StatPill(self.summary, "Total tokens")
        self.stat_cost        = StatPill(self.summary, "Input cost")
        self.stat_output_cost = StatPill(self.summary, "Est. output cost")
        self.stat_context     = StatPill(self.summary, "Avg context")
        for idx, stat in enumerate(
            [
                self.stat_files,
                self.stat_tokens,
                self.stat_cost,
                self.stat_output_cost,
                self.stat_context,
            ]
        ):
            stat.grid(row=0, column=idx, sticky="ew", padx=18, pady=12)

        self.table = ResultsTable(self.results_panel)
        self.table.grid(row=1, column=0, sticky="nsew")

        self.empty_state = ctk.CTkFrame(
            self.content, fg_color=COLORS["bg"], corner_radius=0
        )
        ctk.CTkLabel(
            self.empty_state,
            text=ICONS["bar_chart"],
            font=themed_font(32),
            text_color=COLORS["muted_text"],
        ).pack(pady=(80, 8))
        ctk.CTkLabel(
            self.empty_state,
            text="Add files and click Analyze to see results",
            font=themed_font(13),
            text_color=COLORS["muted_text"],
        ).pack()
        self.logs_panel = LogsPanel(self.content)

        footer = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0)
        footer.grid(row=4, column=0, sticky="ew")
        ctk.CTkLabel(
            footer,
            textvariable=self.status,
            text_color=COLORS["muted_text"],
            font=mono_font(11),
            anchor="w",
        ).pack(side="left", padx=18, pady=8)

        # Packed unconditionally here (not lazily inside _render_results) so
        # the footer's layout is stable from the very first render.
        self.footer_stats = ctk.CTkFrame(footer, fg_color="transparent")
        self.footer_stats.pack(side="right", padx=18, pady=8)
        self.footer_tokens_val = self._footer_stat(self.footer_stats, "Total tokens:")
        self.footer_cost_val = self._footer_stat(self.footer_stats, "Est. input cost:")

        # Text-only (no embedded ContextBar/CTkProgressBar): a CTkProgressBar
        # nested in a narrow pack_propagate(False) wrapper here reproducibly
        # left sibling canvas widgets (StatPills, ResultsTable rows) unpainted
        # under Xvfb once this view was embedded in MainView's tkraise'd
        # container — isolated via bisection. The results-table's own
        # per-row ContextBar (a wider cell inside a CTkScrollableFrame) does
        # not exhibit this, so only the footer usage is avoided.
        ctx_block = ctk.CTkFrame(self.footer_stats, fg_color="transparent")
        ctx_block.pack(side="left")
        ctk.CTkLabel(
            ctx_block,
            text="Avg context:",
            text_color=COLORS["muted_text"],
            font=mono_font(11),
        ).pack(side="left", padx=(0, 6))
        self.footer_context_val = ctk.CTkLabel(
            ctx_block,
            text="-",
            text_color=COLORS["primary"],
            font=mono_font(11, "bold"),
        )
        self.footer_context_val.pack(side="left")

        self._set_tab("results")

    def _footer_stat(self, parent, label: str) -> ctk.CTkLabel:
        """Build a footer label/value pair; returns the value label to update later."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(
            frame, text=label, text_color=COLORS["muted_text"], font=mono_font(11)
        ).pack(side="left", padx=(0, 4))
        value = ctk.CTkLabel(
            frame, text="-", text_color=COLORS["text"], font=mono_font(11, "bold")
        )
        value.pack(side="left")
        return value

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def _pick_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a document", filetypes=SUPPORTED_FILETYPES
        )
        if path:
            self._add_path(Path(path))

    def _pick_folder(self) -> None:
        path = filedialog.askdirectory(title="Select a folder")
        if path:
            self._add_path(Path(path))

    def _add_path(self, path: Path) -> None:
        if path not in self.paths:
            self.paths.append(path)
            self.status.set(f"Added {path.name}")
            self._render_files()
            self.shell.update_header_count(len(self.paths))

    def _remove_path(self, path: Path) -> None:
        self.paths = [item for item in self.paths if item != path]
        self.status.set(f"Removed {path.name}")
        self._render_files()
        self.shell.update_header_count(len(self.paths))

    def _clear(self) -> None:
        self.paths.clear()
        self.results.clear()
        self.last_model = None
        self.has_run = False
        # Force-reset stuck analyzing state so Clear always unblocks the UI.
        if self.cancel_event is not None:
            self.cancel_event.set()
        self.cancel_event = None
        self.analyzing = False
        self.analyze_btn.configure(
            state="normal", text=self._ANALYZE_LABEL, command=self._run_analysis
        )
        self.status.set("Cleared. Add a file or folder to begin.")
        self._render_files()
        self._render_results()
        self.shell.update_header_count(0)

    def _render_files(self) -> None:
        for child in self.files_frame.winfo_children():
            child.destroy()
        if not self.paths:
            row = ctk.CTkFrame(self.files_frame, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=14)
            ctk.CTkLabel(
                row,
                text='No files selected. Click "Add File" or "Add Folder" to get started.',
                text_color=COLORS["muted_text"],
                anchor="w",
            ).pack(fill="x")
            return
        for path in self.paths:
            row = ctk.CTkFrame(
                self.files_frame, fg_color=COLORS["muted"], corner_radius=5
            )
            row.pack(fill="x", padx=18, pady=3)
            prefix = "[folder]" if path.is_dir() else "[file]"
            ctk.CTkLabel(
                row,
                text=f"{prefix} {path}",
                text_color=COLORS["muted_text"],
                font=mono_font(11),
                anchor="w",
            ).pack(side="left", fill="x", expand=True, padx=10, pady=5)
            IconButton(
                row,
                ICONS["x"],
                variant="danger",
                width=28,
                command=lambda p=path: self._remove_path(p),
            ).pack(side="right", padx=5, pady=4)

    # ------------------------------------------------------------------
    # Tab switching
    # ------------------------------------------------------------------

    def _set_tab(self, tab: str) -> None:
        self.active_tab = tab
        self.results_tab.configure(
            fg_color=COLORS["primary"] if tab == "results" else COLORS["muted"]
        )
        self.logs_tab.configure(
            fg_color=COLORS["primary"] if tab == "logs" else COLORS["muted"]
        )
        if tab == "results":
            self.logs_panel.grid_remove()
            self._update_results_visibility()
        else:
            self.logs_panel.refresh()
            self.results_panel.grid_remove()
            self.empty_state.grid_remove()
            self.logs_panel.grid(row=0, column=0, sticky="nsew")

    def _update_results_visibility(self) -> None:
        """Show the empty-state placeholder until the first analysis run completes."""
        if self.has_run:
            self.empty_state.grid_remove()
            self.results_panel.grid(row=0, column=0, sticky="nsew")
        else:
            self.results_panel.grid_remove()
            self.empty_state.grid(row=0, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _run_analysis(self) -> None:
        if self.analyzing:
            return
        if not self.paths:
            self.status.set("No files selected. Use Add File or Add Folder first.")
            return
        self.analyzing = True
        self._files_processed = 0
        self.cancel_event = threading.Event()
        self.analyze_btn.configure(text="Cancel", command=self._cancel_analysis)
        self.status.set("Analyzing - please wait...")
        threading.Thread(target=self._analysis_worker, daemon=True).start()

    def _cancel_analysis(self) -> None:
        """Signal the worker to stop after the file it's currently on."""
        if self.cancel_event is not None:
            self.cancel_event.set()
        self.analyze_btn.configure(state="disabled", text="Cancelling...")
        self.status.set("Cancelling - finishing current file...")

    def _schedule(self, callback, *args) -> None:
        """Schedule *callback* on the main thread; no-op if the window is gone.

        Called from the background analysis thread, which may finish after
        the user has already closed the window/app. self.after() itself can
        raise TclError once the underlying Tk interpreter is torn down.
        """
        try:
            if self.winfo_exists():
                self.after(0, callback, *args)
        except (TclError, RuntimeError):
            pass

    def _on_file_progress(self, result: AnalysisResult) -> None:
        """Called on the main thread after each file finishes analysing."""
        if not self.winfo_exists():
            return
        self._files_processed += 1
        self.status.set(f"Analyzing... {self._files_processed} file(s) processed")

    def _analysis_worker(self) -> None:
        """Run in a background thread.

        MUST always schedule either _analysis_complete or _analysis_error
        back on the main thread — even on unexpected exceptions — so the
        button is never permanently stuck on 'Analyzing...'.
        """
        cancel_event = self.cancel_event
        try:
            model   = self.model_select.selected_model()
            results: list[AnalysisResult] = []
            errors:  list[str]            = []
            for path in list(self.paths):
                if cancel_event.is_set():
                    break
                try:
                    if path.is_dir():
                        results.extend(
                            analyze_folder(
                                path,
                                model.id,
                                on_progress=lambda r: self._schedule(
                                    self._on_file_progress, r
                                ),
                                cancel_event=cancel_event,
                            )
                        )
                    else:
                        result = analyze_file(path, model.id)
                        results.append(result)
                        self._schedule(self._on_file_progress, result)
                except Exception as exc:
                    errors.append(f"{path.name}: {exc}")
            self._schedule(
                self._analysis_complete, results, model, errors, cancel_event.is_set()
            )
        except Exception as exc:
            tb = traceback.format_exc()
            _LOG.error(
                "analysis_worker_crashed",
                extra={"ctx": {"error": str(exc), "traceback": tb}},
            )
            self._schedule(self._analysis_error, str(exc))

    def _analysis_error(self, message: str) -> None:
        """Called on the main thread when the worker crashes unexpectedly."""
        if not self.winfo_exists():
            return
        self.analyzing = False
        self.cancel_event = None
        self.analyze_btn.configure(
            state="normal", text=self._ANALYZE_LABEL, command=self._run_analysis
        )
        self.status.set(f"Error: {message}")
        messagebox.showerror(
            "Analysis failed",
            f"An unexpected error stopped the analysis:\n\n{message}\n\n"
            "Check the Logs tab for the full traceback.",
        )

    def _analysis_complete(
        self,
        results: list[AnalysisResult],
        model: ModelInfo,
        errors: list[str],
        cancelled: bool = False,
    ) -> None:
        if not self.winfo_exists():
            return
        self.analyzing = False
        self.cancel_event = None
        self.analyze_btn.configure(
            state="normal", text=self._ANALYZE_LABEL, command=self._run_analysis
        )
        self.results = results
        self.last_model = model
        self.has_run = True
        self._render_results()
        self._set_tab("results")
        if errors:
            messagebox.showwarning(
                "Analysis completed with errors", "\n".join(errors[:8])
            )
        if cancelled:
            self.status.set(
                f"Cancelled - {len(results)} file(s) analysed before stopping."
            )
            return
        self.status.set(
            f"Done - {len(results)} file(s) analysed with {model.display_name}."
        )

    def _render_results(self) -> None:
        """Populate summary pills and results table.

        Guards against None context_usage_pct returned when a model has no
        context window defined or when a file failed to parse. Visibility is
        updated first so widgets are mapped before their text is set — CTk's
        canvas-based labels can end up with stale (unmapped-time) geometry
        if text changes while still hidden behind grid_remove().
        """
        if self.active_tab == "results":
            self._update_results_visibility()
        self.table.set_results(self.results)
        count        = len(self.results)
        total_tokens = sum(item.token_count for item in self.results)
        total_cost   = sum(item.estimated_input_cost for item in self.results)
        valid_pcts   = [
            item.context_usage_pct
            for item in self.results
            if item.context_usage_pct is not None
        ]
        avg_context  = sum(valid_pcts) / len(valid_pcts) if valid_pcts else 0.0

        # Est. output cost = (per-file output-token estimate) x file count,
        # priced against the model actually used for the last analysis run.
        if self.last_model is not None and count > 0:
            est_output_tokens = parse_int(self.output_tokens.get())
            total_output_cost = count * output_cost(est_output_tokens, self.last_model)
            output_cost_str = fmt_cost(total_output_cost)
        else:
            output_cost_str = "—"

        self.stat_files.set_text(str(count))
        self.stat_tokens.set_text(fmt_num(total_tokens))
        self.stat_cost.set_text(fmt_cost(total_cost))
        self.stat_output_cost.set_text(output_cost_str)
        self.stat_context.set_text(f"{fmt_float(avg_context)}%")

        if self.has_run:
            self.footer_tokens_val.configure(text=fmt_num(total_tokens))
            self.footer_cost_val.configure(text=fmt_cost(total_cost))
            self.footer_context_val.configure(text=f"{fmt_float(avg_context)}%")
        else:
            self.footer_tokens_val.configure(text="-")
            self.footer_cost_val.configure(text="-")
            self.footer_context_val.configure(text="-")
