"""File parser and analysis screen."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from norefund.core.models_registry import ModelInfo
from norefund.core.service import AnalysisResult, analyze_file, analyze_folder
from norefund.gui.formatting import context_color, fmt_cost, fmt_float, fmt_num
from norefund.gui.theme import COLORS, SUPPORTED_FILETYPES
from norefund.gui.widgets import IconButton, ModelDropdown, StatPill
from norefund.logging_config import latest_log_file


def _tail_lines(path: Path, n: int = 120) -> list[str]:
    with path.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - 16_000))
        return f.read().decode("utf-8", errors="ignore").splitlines()[-n:]


class ResultsTable(ctk.CTkScrollableFrame):
    HEADERS = ["File", "Tokens", "Context %", "Fits?", "Chunks", "Input Cost", "Words", "Chars"]
    WIDTHS = [230, 90, 130, 70, 70, 100, 90, 90]

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
                font=ctk.CTkFont(size=10, weight="bold"),
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
        bg = COLORS["card"] if row % 2 else COLORS["bg"]
        values = [
            Path(result.file_path).name,
            fmt_num(result.token_count),
            f"{fmt_float(result.context_usage_pct)}%",
            "OK" if result.fits_in_context else "NO",
            str(result.min_chunks_needed),
            fmt_cost(result.estimated_input_cost),
            fmt_num(result.word_count),
            fmt_num(result.char_count),
        ]
        for col, (value, width) in enumerate(zip(values, self.WIDTHS)):
            color = COLORS["text"]
            if col == 2:
                color = context_color(result.context_usage_pct)
            elif col == 3:
                color = COLORS["primary"] if result.fits_in_context else COLORS["danger"]
            ctk.CTkLabel(
                self,
                text=value,
                width=width,
                fg_color=bg,
                text_color=color,
                font=ctk.CTkFont(
                    size=12,
                    weight="bold" if col in {0, 1, 5} else "normal",
                ),
                anchor="w",
                corner_radius=0,
            ).grid(row=row, column=col, sticky="ew", padx=(0, 1), pady=(0, 1))


class LogsPanel(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.text = ctk.CTkTextbox(
            self,
            fg_color=COLORS["bg"],
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=12, family="monospace"),
            wrap="none",
        )
        self.text.pack(fill="both", expand=True, padx=18, pady=16)
        self.refresh()

    def refresh(self) -> None:
        self.text.delete("1.0", "end")
        path = latest_log_file()
        if not path:
            self.text.insert("end", "No logs yet. Run an analysis to see output here.\n")
            return
        try:
            for line in _tail_lines(path):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    ctx = obj.get("ctx") or {}
                    message = obj.get("message", "log")
                    level = obj.get("level", "INFO")
                    self.text.insert("end", f"> [{level}] {message} {ctx}\n")
                except json.JSONDecodeError:
                    self.text.insert("end", line + "\n")
        except OSError as exc:
            self.text.insert("end", f"Error reading log file: {exc}\n")


class ParserView(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        shell,
        models: list[ModelInfo],
        default_output: ctk.StringVar,
    ) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.shell = shell
        self.models = models
        self.default_output = default_output
        self.output_tokens = ctk.StringVar(value=default_output.get())
        self.paths: list[Path] = []
        self.results: list[AnalysisResult] = []
        self.active_tab = "results"
        self.status = ctk.StringVar(value="Ready - add a file or folder to begin.")
        self.analyzing = False

        self._build()
        self._render_files()
        self._render_results()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0)
        toolbar.grid(row=0, column=0, sticky="ew")
        IconButton(toolbar, "+ Add File", width=104, command=self._pick_file).pack(
            side="left", padx=(18, 6), pady=10
        )
        IconButton(toolbar, "+ Add Folder", width=114, command=self._pick_folder).pack(
            side="left", padx=6, pady=10
        )
        IconButton(
            toolbar, "x Clear", variant="danger", width=82, command=self._clear
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
            font=ctk.CTkFont(size=12),
        ).pack(side="left")
        ctk.CTkEntry(
            toolbar,
            textvariable=self.output_tokens,
            width=76,
            fg_color=COLORS["input"],
            border_width=0,
            font=ctk.CTkFont(size=12, family="monospace"),
        ).pack(side="left", padx=(6, 3), pady=10)
        ctk.CTkLabel(
            toolbar,
            text="tokens",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left")
        self.analyze_btn = IconButton(
            toolbar,
            "Analyze",
            variant="primary",
            width=110,
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
        self.logs_tab.pack(side="left", padx=(4, 0), pady=8)

        self.content = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.content.grid(row=3, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self.results_panel = ctk.CTkFrame(
            self.content, fg_color=COLORS["bg"], corner_radius=0
        )
        self.logs_panel = LogsPanel(self.content)
        self.results_panel.grid(row=0, column=0, sticky="nsew")
        self.results_panel.grid_columnconfigure(0, weight=1)
        self.results_panel.grid_rowconfigure(1, weight=1)
        self.summary = ctk.CTkFrame(
            self.results_panel, fg_color=COLORS["card"], corner_radius=0
        )
        self.summary.grid(row=0, column=0, sticky="ew")
        self.summary.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="summary")
        self.stat_files = StatPill(self.summary, "Files")
        self.stat_tokens = StatPill(self.summary, "Total tokens")
        self.stat_cost = StatPill(self.summary, "Input cost")
        self.stat_context = StatPill(self.summary, "Avg context")
        for idx, stat in enumerate(
            [self.stat_files, self.stat_tokens, self.stat_cost, self.stat_context]
        ):
            stat.grid(row=0, column=idx, sticky="ew", padx=18, pady=12)
        self.table = ResultsTable(self.results_panel)
        self.table.grid(row=1, column=0, sticky="nsew")

        footer = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0)
        footer.grid(row=4, column=0, sticky="ew")
        ctk.CTkLabel(
            footer,
            textvariable=self.status,
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=11, family="monospace"),
            anchor="w",
        ).pack(side="left", padx=18, pady=8)

        self._set_tab("results")

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
                font=ctk.CTkFont(size=11, family="monospace"),
                anchor="w",
            ).pack(side="left", fill="x", expand=True, padx=10, pady=5)
            IconButton(
                row,
                "x",
                variant="danger",
                width=28,
                command=lambda p=path: self._remove_path(p),
            ).pack(side="right", padx=5, pady=4)

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
            self.results_panel.grid()
        else:
            self.logs_panel.refresh()
            self.results_panel.grid_remove()
            self.logs_panel.grid(row=0, column=0, sticky="nsew")

    def _run_analysis(self) -> None:
        if self.analyzing:
            return
        if not self.paths:
            self.status.set("No files selected. Use Add File or Add Folder first.")
            return
        self.analyzing = True
        self.analyze_btn.configure(state="disabled", text="Analyzing...")
        self.status.set("Analyzing - please wait...")
        threading.Thread(target=self._analysis_worker, daemon=True).start()

    def _analysis_worker(self) -> None:
        model = self.model_select.selected_model()
        results: list[AnalysisResult] = []
        errors: list[str] = []
        for path in list(self.paths):
            try:
                if path.is_dir():
                    results.extend(analyze_folder(path, model.id))
                else:
                    results.append(analyze_file(path, model.id))
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        self.after(0, self._analysis_complete, results, model, errors)

    def _analysis_complete(
        self, results: list[AnalysisResult], model: ModelInfo, errors: list[str]
    ) -> None:
        self.analyzing = False
        self.analyze_btn.configure(state="normal", text="Analyze")
        self.results = results
        self._render_results()
        self._set_tab("results")
        if errors:
            messagebox.showwarning(
                "Analysis completed with errors", "\n".join(errors[:8])
            )
        self.status.set(
            f"Done - {len(results)} file(s) analysed with {model.display_name}."
        )

    def _render_results(self) -> None:
        self.table.set_results(self.results)
        count = len(self.results)
        total_tokens = sum(item.token_count for item in self.results)
        total_cost = sum(item.estimated_input_cost for item in self.results)
        avg_context = (
            sum(item.context_usage_pct for item in self.results) / count if count else 0
        )
        self.stat_files.set_text(str(count))
        self.stat_tokens.set_text(fmt_num(total_tokens))
        self.stat_cost.set_text(fmt_cost(total_cost))
        self.stat_context.set_text(f"{fmt_float(avg_context)}%")
