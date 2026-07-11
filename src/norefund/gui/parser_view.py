"""File Parser — pick files/folders, analyze against a model, view results/logs."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from tkinter import TclError, filedialog

import customtkinter as ctk

from norefund.core.export import analysis_results_to_csv, analysis_results_to_markdown
from norefund.core.models_registry import ModelInfo
from norefund.core.parsing import SUPPORTED_EXTENSIONS
from norefund.core.service import AnalysisResult, analyze_file, analyze_folder
from norefund.gui import formatting, theme
from norefund.gui.dnd import enable_file_drop
from norefund.gui.theme import COLORS, ICONS, SUPPORTED_FILETYPES
from norefund.gui.widgets import ContextBar, IconButton, ModelDropdownButton, StatPill
from norefund.logging_config import latest_log_file

_ANALYZE_LABEL = f"{ICONS['zap']} Analyze"
_ANALYZING_LABEL = f"{ICONS['refresh']} Analyzing…"


class ResultsTable(ctk.CTkScrollableFrame):
    _COLUMNS = [
        "File",
        "Tokens",
        "Context %",
        "Fits?",
        "Chunks",
        "Input Cost",
        "Words",
        "Chars",
    ]
    _WEIGHTS = [3, 1, 2, 1, 1, 1, 1, 1]

    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, fg_color=COLORS["bg"], **kwargs)
        for i, weight in enumerate(self._WEIGHTS):
            self.columnconfigure(i, weight=weight)
        self._build_header()
        self._row_frames: list[ctk.CTkFrame] = []

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=COLORS["muted"], corner_radius=0)
        header.grid(
            row=0, column=0, columnspan=len(self._COLUMNS), sticky="ew", pady=(0, 2)
        )
        for i, weight in enumerate(self._WEIGHTS):
            header.columnconfigure(i, weight=weight)
        for i, col in enumerate(self._COLUMNS):
            anchor = "w" if i == 0 else "e"
            ctk.CTkLabel(
                header,
                text=col.upper(),
                font=theme.font(9, "bold"),
                text_color=COLORS["muted_fg"],
                anchor=anchor,
            ).grid(row=0, column=i, sticky="ew", padx=6, pady=4)

    def clear(self) -> None:
        for frame in self._row_frames:
            frame.destroy()
        self._row_frames.clear()

    def set_results(self, results: list[AnalysisResult]) -> None:
        self.clear()
        for i, result in enumerate(results, start=1):
            self._add_row(i, result)

    def _add_row(self, row_index: int, result: AnalysisResult) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=row_index, column=0, columnspan=len(self._COLUMNS), sticky="ew")
        for i, weight in enumerate(self._WEIGHTS):
            row.columnconfigure(i, weight=weight)
        row.bind("<Enter>", lambda _e: row.configure(fg_color=COLORS["muted"]))
        row.bind("<Leave>", lambda _e: row.configure(fg_color="transparent"))
        self._row_frames.append(row)

        name = Path(result.file_path).name

        if result.error is not None:
            ctk.CTkLabel(
                row,
                text=name,
                font=theme.mono_font(11),
                anchor="w",
                text_color=COLORS["fg"],
            ).grid(row=0, column=0, sticky="ew", padx=6, pady=4)
            ctk.CTkLabel(
                row,
                text=f"{ICONS['x_circle']} {result.error}",
                font=theme.font(11),
                anchor="w",
                text_color=COLORS["destructive"],
            ).grid(
                row=0,
                column=1,
                columnspan=len(self._COLUMNS) - 1,
                sticky="ew",
                padx=6,
                pady=4,
            )
            return

        ctk.CTkLabel(
            row,
            text=name,
            font=theme.mono_font(11),
            anchor="w",
            text_color=COLORS["fg"],
        ).grid(row=0, column=0, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(
            row,
            text=formatting.fmt_num(result.token_count),
            font=theme.mono_font(11),
            anchor="e",
        ).grid(row=0, column=1, sticky="ew", padx=6, pady=4)

        ctx_cell = ctk.CTkFrame(row, fg_color="transparent")
        ctx_cell.grid(row=0, column=2, sticky="ew", padx=6, pady=4)
        bar = ContextBar(ctx_cell, height=5)
        bar.pack(side="left", fill="x", expand=True, padx=(0, 6))
        bar.set_value(result.context_usage_pct)
        ctk.CTkLabel(
            ctx_cell,
            text=formatting.fmt_context_pct(result.context_usage_pct),
            font=theme.mono_font(10),
            text_color=formatting.context_color(result.context_usage_pct),
        ).pack(side="left")

        fits_icon = (
            ICONS["check_circle"] if result.fits_in_context else ICONS["x_circle"]
        )
        fits_color = (
            COLORS["primary"] if result.fits_in_context else COLORS["destructive"]
        )
        ctk.CTkLabel(
            row,
            text=fits_icon,
            font=theme.font(11),
            text_color=fits_color,
            anchor="e",
        ).grid(row=0, column=3, sticky="ew", padx=6, pady=4)

        ctk.CTkLabel(
            row,
            text=str(result.min_chunks_needed),
            font=theme.mono_font(11),
            anchor="e",
        ).grid(row=0, column=4, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(
            row,
            text=formatting.fmt_cost(result.estimated_input_cost),
            font=theme.mono_font(11),
            anchor="e",
        ).grid(row=0, column=5, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(
            row,
            text=formatting.fmt_num(result.word_count),
            font=theme.mono_font(11),
            anchor="e",
        ).grid(row=0, column=6, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(
            row,
            text=formatting.fmt_num(result.char_count),
            font=theme.mono_font(11),
            anchor="e",
        ).grid(row=0, column=7, sticky="ew", padx=6, pady=4)


class LogsPanel(ctk.CTkFrame):
    _TAG_COLORS = {
        "INFO": "muted_fg",
        "WARNING": "warning",
        "ERROR": "destructive",
        "DEBUG": "muted_fg",
    }

    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, fg_color=COLORS["bg"], **kwargs)
        self._textbox = ctk.CTkTextbox(
            self,
            font=theme.mono_font(11),
            fg_color=COLORS["bg"],
            text_color=COLORS["muted_fg"],
            wrap="none",
            state="disabled",
        )
        self._textbox.pack(fill="both", expand=True)
        for level, token in self._TAG_COLORS.items():
            is_dark = ctk.get_appearance_mode() == "Dark"
            self._textbox.tag_config(level, foreground=theme.resolve(token, is_dark))

    def refresh(self) -> None:
        if not self.winfo_exists():
            return
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        log_path = latest_log_file()
        if log_path is None:
            self._textbox.insert(
                "end", "No logs yet — run an analysis to see activity here.\n"
            )
        else:
            try:
                lines = log_path.read_text(
                    encoding="utf-8", errors="ignore"
                ).splitlines()[-500:]
            except OSError as exc:
                lines = [
                    f'{{"level": "ERROR", "message": "Failed to read log file: {exc}"}}'
                ]
            for line in lines:
                self._insert_line(line)
        self._textbox.configure(state="disabled")

    def _insert_line(self, raw: str) -> None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._textbox.insert("end", raw + "\n")
            return
        level = data.get("level", "INFO")
        message = data.get("message", "")
        ctx = data.get("ctx") or {}
        ctx_str = "  " + " ".join(f"{k}={v}" for k, v in ctx.items()) if ctx else ""
        self._textbox.insert("end", f"›  [{level}]  {message}{ctx_str}\n", level)


class ParserView(ctk.CTkFrame):
    def __init__(self, parent, shell) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.shell = shell
        self._paths: list[Path] = []
        self._results: list[AnalysisResult] = []
        self.analyzing = False
        self.cancel_event: threading.Event | None = None
        self._active_tab = "results"

        self._build_toolbar()
        self._build_file_strip()
        self._build_tabs()
        self._build_content()
        self._build_status_bar()

        self._refresh_file_strip()
        self._show_empty_results()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        toolbar = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0)
        toolbar.pack(side="top", fill="x")
        inner = ctk.CTkFrame(toolbar, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)

        IconButton(inner, "Add File", icon="plus", command=self._add_files).pack(
            side="left", padx=(0, 6)
        )
        IconButton(
            inner, "Add Folder", icon="folder_plus", command=self._add_folder
        ).pack(side="left", padx=6)
        IconButton(
            inner, "Clear", icon="x", variant="danger", command=self._clear
        ).pack(side="left", padx=6)

        ctk.CTkFrame(inner, fg_color=COLORS["border"], width=1).pack(
            side="left", fill="y", padx=10, pady=4
        )

        self._model_dropdown = ModelDropdownButton(
            inner, self.shell.models, self.shell.models[0], on_select=lambda _m: None
        )
        self._model_dropdown.pack(side="left", padx=6)

        out_frame = ctk.CTkFrame(inner, fg_color="transparent")
        out_frame.pack(side="left", padx=10)
        ctk.CTkLabel(
            out_frame,
            text="Est. output:",
            font=theme.font(11),
            text_color=COLORS["muted_fg"],
        ).pack(side="left", padx=(0, 6))
        self._output_var = ctk.StringVar(
            value=str(self.shell.settings.default_output_tokens)
        )
        ctk.CTkEntry(
            out_frame,
            textvariable=self._output_var,
            width=90,
            font=theme.mono_font(11),
            fg_color=COLORS["input_bg"],
            border_width=0,
        ).pack(side="left")
        ctk.CTkLabel(
            out_frame, text="tokens", font=theme.font(11), text_color=COLORS["muted_fg"]
        ).pack(side="left", padx=(6, 0))

        self._analyze_btn = IconButton(
            inner, "Analyze", icon="zap", variant="primary", command=self._run_analysis
        )
        self._analyze_btn.pack(side="right")
        self._analyze_btn.configure(state="disabled")

    def _build_file_strip(self) -> None:
        wrapper = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0, height=100)
        wrapper.pack(side="top", fill="x")
        wrapper.pack_propagate(False)
        self._file_strip = ctk.CTkScrollableFrame(wrapper, fg_color=COLORS["bg"])
        self._file_strip.pack(fill="both", expand=True, padx=12, pady=6)
        enable_file_drop(wrapper, self._on_files_dropped, suffixes=SUPPORTED_EXTENSIONS)

    def _build_tabs(self) -> None:
        tabs = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0)
        tabs.pack(side="top", fill="x")
        self._tab_buttons: dict[str, ctk.CTkButton] = {}
        for tab_id, label in [("results", "Results"), ("logs", "Logs")]:
            btn = ctk.CTkButton(
                tabs,
                text=label,
                font=theme.font(12),
                corner_radius=0,
                height=32,
                width=90,
                fg_color="transparent",
                hover_color=COLORS["muted"],
                text_color=COLORS["muted_fg"],
                command=lambda t=tab_id: self._switch_tab(t),
            )
            btn.pack(
                side="left", padx=(12 if tab_id == "results" else 0, 0), pady=(4, 0)
            )
            self._tab_buttons[tab_id] = btn
        self._sync_tab_styles()

    def _sync_tab_styles(self) -> None:
        for tab_id, btn in self._tab_buttons.items():
            active = tab_id == self._active_tab
            btn.configure(
                text_color=COLORS["primary"] if active else COLORS["muted_fg"]
            )

    def _build_content(self) -> None:
        self._content = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self._content.pack(side="top", fill="both", expand=True)

        self._results_frame = ctk.CTkFrame(self._content, fg_color=COLORS["bg"])
        self._logs_frame = LogsPanel(self._content)

        for frame in (self._results_frame, self._logs_frame):
            frame.place(x=0, y=0, relwidth=1, relheight=1)
        self._results_frame.tkraise()

    def _build_status_bar(self) -> None:
        self._status_bar = ctk.CTkFrame(
            self, fg_color=COLORS["card"], corner_radius=0, height=32
        )
        self._status_left = ctk.CTkLabel(
            self._status_bar,
            text="",
            font=theme.font(11),
            text_color=COLORS["muted_fg"],
        )
        self._status_left.pack(side="left", padx=12)
        self._status_right = ctk.CTkLabel(
            self._status_bar,
            text="",
            font=theme.mono_font(11),
            text_color=COLORS["muted_fg"],
        )
        self._status_right.pack(side="right", padx=12)

    # ------------------------------------------------------------------
    # File selection
    # ------------------------------------------------------------------

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(filetypes=SUPPORTED_FILETYPES)
        for p in paths:
            self._paths.append(Path(p))
        self._refresh_file_strip()

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self._paths.append(Path(folder))
        self._refresh_file_strip()

    def _on_files_dropped(self, paths: list[Path]) -> None:
        self._paths.extend(paths)
        self._refresh_file_strip()

    def _remove_path(self, path: Path) -> None:
        self._paths = [p for p in self._paths if p != path]
        self._refresh_file_strip()

    def _clear(self) -> None:
        if self.analyzing and self.cancel_event is not None:
            self.cancel_event.set()
        self._reset_busy_state()
        self._paths = []
        self._results = []
        self._refresh_file_strip()
        self._show_empty_results()
        self._status_bar.pack_forget()
        self.shell.update_header_count(0)

    def _refresh_file_strip(self) -> None:
        for child in self._file_strip.winfo_children():
            child.destroy()

        if not self._paths:
            ctk.CTkLabel(
                self._file_strip,
                text=(
                    "No files selected. Click 'Add File' or 'Add Folder' "
                    "to get started."
                ),
                font=theme.font(11),
                text_color=COLORS["muted_fg"],
            ).pack(pady=10)
        else:
            for path in self._paths:
                self._build_file_row(path)

        self._analyze_btn.configure(
            state="normal" if (self._paths and not self.analyzing) else "disabled"
        )
        self.shell.update_header_count(len(self._paths))

    def _build_file_row(self, path: Path) -> None:
        row = ctk.CTkFrame(self._file_strip, fg_color="transparent")
        row.pack(fill="x", pady=1)
        icon = ICONS["folder_open"] if path.is_dir() else ICONS["file_text"]
        ctk.CTkLabel(
            row,
            text=f"{icon}  {path}",
            font=theme.mono_font(11),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        remove_btn = ctk.CTkLabel(
            row,
            text=ICONS["x"],
            font=theme.font(11),
            text_color=COLORS["muted_fg"],
            cursor="hand2",
        )
        remove_btn.pack(side="right", padx=6)
        remove_btn.bind("<Button-1>", lambda _e, p=path: self._remove_path(p))

    # ------------------------------------------------------------------
    # Results tab state
    # ------------------------------------------------------------------

    def _show_empty_results(self) -> None:
        for child in self._results_frame.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self._results_frame,
            text=f"{ICONS['bar_chart']}\n\nAdd files and click Analyze to see results",
            font=theme.font(13),
            text_color=COLORS["muted_fg"],
            justify="center",
        ).pack(expand=True)

    def _render_results(self, results: list[AnalysisResult]) -> None:
        for child in self._results_frame.winfo_children():
            child.destroy()

        stats_row = ctk.CTkFrame(self._results_frame, fg_color="transparent")
        stats_row.pack(fill="x", padx=12, pady=(10, 6))

        successful = [r for r in results if r.error is None]
        total_tokens = sum(r.token_count for r in successful)
        total_input_cost = sum(r.estimated_input_cost for r in successful)
        pct_values = [
            r.context_usage_pct for r in successful if r.context_usage_pct is not None
        ]
        avg_pct = sum(pct_values) / len(pct_values) if pct_values else None

        StatPill(stats_row, "Files", formatting.fmt_num(len(results))).pack(
            side="left", padx=(0, 24)
        )
        StatPill(stats_row, "Total tokens", formatting.fmt_num(total_tokens)).pack(
            side="left", padx=24
        )
        StatPill(stats_row, "Input cost", formatting.fmt_cost(total_input_cost)).pack(
            side="left", padx=24
        )
        StatPill(stats_row, "Avg context", formatting.fmt_context_pct(avg_pct)).pack(
            side="left", padx=24
        )
        IconButton(
            stats_row, "Export CSV", icon="file_text", command=self._export_csv
        ).pack(side="right", padx=(6, 0))
        IconButton(
            stats_row, "Export MD", icon="file_text", command=self._export_md
        ).pack(side="right")

        table = ResultsTable(self._results_frame)
        table.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        table.set_results(results)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_csv(self) -> None:
        if not self._results:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")]
        )
        if path:
            Path(path).write_text(
                analysis_results_to_csv(self._results), encoding="utf-8"
            )

    def _export_md(self) -> None:
        if not self._results:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".md", filetypes=[("Markdown", "*.md")]
        )
        if path:
            Path(path).write_text(
                analysis_results_to_markdown(self._results), encoding="utf-8"
            )

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------

    def _switch_tab(self, tab_id: str) -> None:
        self._active_tab = tab_id
        self._sync_tab_styles()
        if tab_id == "logs":
            self._logs_frame.tkraise()
            self._logs_frame.refresh()
        else:
            self._results_frame.tkraise()

    # ------------------------------------------------------------------
    # Analysis / threading
    # ------------------------------------------------------------------

    def _run_analysis(self) -> None:
        if self.analyzing or not self._paths:
            return
        self.analyzing = True
        self.cancel_event = threading.Event()
        self._analyze_btn.configure(
            text=f"{ICONS['x']} Cancel", command=self._cancel_analysis, state="normal"
        )

        model = self._model_dropdown.selected_model()
        paths = list(self._paths)
        cancel_event = self.cancel_event
        threading.Thread(
            target=self._analysis_worker,
            args=(paths, model, cancel_event),
            daemon=True,
        ).start()

    def _cancel_analysis(self) -> None:
        if self.cancel_event is not None:
            self.cancel_event.set()
        self._analyze_btn.configure(text="Cancelling…", state="disabled")

    def _analysis_worker(
        self, paths: list[Path], model: ModelInfo, cancel_event: threading.Event
    ) -> None:
        results: list[AnalysisResult] = []
        try:
            for path in paths:
                if cancel_event.is_set():
                    break
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
        except Exception as exc:  # noqa: BLE001
            self._schedule(self._analysis_error, str(exc))
            return
        self._schedule(self._analysis_complete, results, model, cancel_event.is_set())

    def _schedule(self, callback, *args) -> None:
        if not self.winfo_exists():
            return
        try:
            self.after(0, callback, *args)
        except (TclError, RuntimeError):
            pass

    def _on_file_progress(self, _result: AnalysisResult) -> None:
        pass

    def _reset_busy_state(self) -> None:
        self.analyzing = False
        self.cancel_event = None
        if not self.winfo_exists():
            return
        self._analyze_btn.configure(
            text=_ANALYZE_LABEL,
            command=self._run_analysis,
            state="normal" if self._paths else "disabled",
        )

    def _analysis_complete(
        self, results: list[AnalysisResult], model: ModelInfo, cancelled: bool
    ) -> None:
        if not self.winfo_exists():
            return
        self._reset_busy_state()
        self._results = results
        self._render_results(results)
        self.shell.update_header_count(len(results))

        successful = [r for r in results if r.error is None]
        total_tokens = sum(r.token_count for r in successful)
        total_input_cost = sum(r.estimated_input_cost for r in successful)
        prefix = "Cancelled — " if cancelled else "Done — "
        self._status_left.configure(
            text=f"{prefix}{len(results)} file(s) analysed with {model.display_name}"
        )
        tokens_str = formatting.fmt_num(total_tokens)
        cost_str = formatting.fmt_cost(total_input_cost)
        self._status_right.configure(
            text=f"Total tokens: {tokens_str}    Est. input cost: {cost_str}"
        )
        self._status_bar.pack(side="bottom", fill="x")
        if self._active_tab == "logs":
            self._logs_frame.refresh()

    def _analysis_error(self, message: str) -> None:
        if not self.winfo_exists():
            return
        self._reset_busy_state()
        self._status_left.configure(
            text=f"{ICONS['x_circle']} Analysis failed: {message}"
        )
        self._status_right.configure(text="")
        self._status_bar.pack(side="bottom", fill="x")
