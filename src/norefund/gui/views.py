"""Main view — full GUI implementation with logging pane.

Layout (top to bottom):
  1. Top toolbar   — file/folder picker + model dropdown + Analyze button
  2. Results table — per-file breakdown (tokens, context %, cost, fit status)
  3. Summary bar   — total tokens, total cost, context usage bar
  4. Tabs          — [Results] [Logs]
  5. Status bar    — current operation message
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from tkinter import filedialog
from typing import List

import customtkinter as ctk

from norefund.core.models_registry import ModelInfo, list_models
from norefund.core.service import AnalysisResult, analyze_file, analyze_folder
from norefund.logging_config import latest_log_file


_GREEN  = "#2ecc71"
_YELLOW = "#f39c12"
_RED    = "#e74c3c"
_MUTED  = "gray"


def _usage_colour(pct: float) -> str:
    if pct <= 80:
        return _GREEN
    if pct <= 100:
        return _YELLOW
    return _RED


class _SectionLabel(ctk.CTkLabel):
    def __init__(self, parent, text: str, **kw):
        super().__init__(
            parent,
            text=text,
            font=ctk.CTkFont(size=13, weight="bold"),
            **kw,
        )


class _ContextBar(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self._bar = ctk.CTkProgressBar(self, width=180, height=10)
        self._bar.set(0)
        self._bar.pack(side="left", padx=(0, 8), pady=4)
        self._label = ctk.CTkLabel(self, text="—", font=ctk.CTkFont(size=12), width=60, anchor="w")
        self._label.pack(side="left")

    def update(self, pct: float) -> None:
        capped = min(pct / 100, 1.0)
        self._bar.set(capped)
        colour = _usage_colour(pct)
        self._bar.configure(progress_color=colour)
        self._label.configure(text=f"{pct:.1f}%", text_color=colour)

    def reset(self) -> None:
        self._bar.set(0)
        self._bar.configure(progress_color=_GREEN)
        self._label.configure(text="—", text_color=_MUTED)


_COLUMNS = [
    ("File",          260, "w"),
    ("Tokens",         90, "e"),
    ("Context %",      90, "e"),
    ("Fits?",           60, "center"),
    ("Chunks needed",  110, "e"),
    ("Input cost",      90, "e"),
    ("Words",           70, "e"),
    ("Chars",           70, "e"),
]


class ResultsTable(ctk.CTkScrollableFrame):
    _HEADER_FG  = ("#e5e5e5", "#2b2b2b")
    _ROW_EVEN   = ("#f9f9f9", "#222222")
    _ROW_ODD    = ("#f0f0f0", "#1e1e1e")

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self._draw_header()

    def _draw_header(self) -> None:
        font = ctk.CTkFont(size=12, weight="bold")
        for col, (name, width, anchor) in enumerate(_COLUMNS):
            ctk.CTkLabel(
                self,
                text=name,
                font=font,
                width=width,
                anchor=anchor,
                fg_color=self._HEADER_FG,
                corner_radius=0,
            ).grid(row=0, column=col, padx=1, pady=(0, 2), sticky="ew")

    def clear(self) -> None:
        for widget in self.winfo_children():
            info = widget.grid_info()
            if info and int(info["row"]) > 0:
                widget.destroy()

    def add_result(self, result: AnalysisResult, row_idx: int) -> None:
        bg = self._ROW_EVEN if row_idx % 2 == 0 else self._ROW_ODD
        font = ctk.CTkFont(size=12)
        fits_text  = "✅" if result.fits_in_context else "❌"
        pct_colour = _usage_colour(result.context_usage_pct)

        cells = [
            (Path(result.file_path).name,           "w",      None),
            (f"{result.token_count:,}",              "e",      None),
            (f"{result.context_usage_pct:.1f}%",    "e",      pct_colour),
            (fits_text,                              "center", None),
            (str(result.min_chunks_needed),          "e",      None),
            (f"${result.estimated_input_cost:.4f}",  "e",      None),
            (f"{result.word_count:,}",               "e",      None),
            (f"{result.char_count:,}",               "e",      None),
        ]

        for col, (text, anchor, text_color) in enumerate(cells):
            width = _COLUMNS[col][1]
            kw: dict = dict(
                text=text,
                font=font,
                width=width,
                anchor=anchor,
                fg_color=bg,
                corner_radius=0,
            )
            if text_color:
                kw["text_color"] = text_color
            ctk.CTkLabel(self, **kw).grid(
                row=row_idx + 1,
                column=col,
                padx=1,
                pady=1,
                sticky="ew",
            )


class _SummaryPanel(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        ctk.CTkLabel(self, text="Total tokens:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, padx=(16, 4), pady=8, sticky="e")
        self._lbl_tokens = ctk.CTkLabel(self, text="—", font=ctk.CTkFont(size=12))
        self._lbl_tokens.grid(row=0, column=1, padx=(0, 24), pady=8, sticky="w")

        ctk.CTkLabel(self, text="Est. input cost:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=2, padx=(0, 4), pady=8, sticky="e")
        self._lbl_cost = ctk.CTkLabel(self, text="—", font=ctk.CTkFont(size=12))
        self._lbl_cost.grid(row=0, column=3, padx=(0, 24), pady=8, sticky="w")

        ctk.CTkLabel(self, text="Context usage:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=4, padx=(0, 4), pady=8, sticky="e")
        self._ctx_bar = _ContextBar(self)
        self._ctx_bar.grid(row=0, column=5, padx=(0, 16), pady=8, sticky="w")

    def update(self, results: List[AnalysisResult], model: ModelInfo) -> None:
        total_tokens = sum(r.token_count for r in results)
        total_cost   = sum(r.estimated_input_cost for r in results)
        avg_pct      = sum(r.context_usage_pct for r in results) / len(results) if results else 0

        self._lbl_tokens.configure(text=f"{total_tokens:,}")
        self._lbl_cost.configure(text=f"${total_cost:.4f}")
        self._ctx_bar.update(avg_pct)

    def reset(self) -> None:
        self._lbl_tokens.configure(text="—")
        self._lbl_cost.configure(text="—")
        self._ctx_bar.reset()


class LogsView(ctk.CTkFrame):
    """Read-only view that shows the latest JSON log file.

    - The file is resolved via logging_config.latest_log_file()
    - The user can refresh to re-read the file while the app is running
    - Lines are parsed and prettified for readability
    """

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)

        self._text = ctk.CTkTextbox(self, wrap="none", font=ctk.CTkFont(size=11))
        self._text.pack(fill="both", expand=True, padx=8, pady=8)

        btn_bar = ctk.CTkFrame(self)
        btn_bar.pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkButton(btn_bar, text="Refresh", width=90, command=self._refresh).pack(
            side="left", padx=(0, 8), pady=4
        )
        self._lbl_path = ctk.CTkLabel(btn_bar, text="No log file yet", anchor="w")
        self._lbl_path.pack(side="left", padx=(0, 8), pady=4)

    def _refresh(self) -> None:
        path = latest_log_file()
        self._text.delete("1.0", "end")
        if not path:
            self._lbl_path.configure(text="No log file found")
            return

        self._lbl_path.configure(text=str(path))
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        pretty = json.dumps(obj, indent=2, ensure_ascii=False)
                        self._text.insert("end", pretty + "\n\n")
                    except json.JSONDecodeError:
                        # Fallback: show raw line
                        self._text.insert("end", line + "\n")
        except OSError as exc:
            self._text.insert("end", f"Error reading log file: {exc}\n")


class MainView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent, fg_color="transparent")
        self._results:  List[AnalysisResult] = []
        self._models:   List[ModelInfo]       = list_models()
        self._model_map: dict[str, ModelInfo] = {m.display_name: m for m in self._models}

        self._build_toolbar()
        self._build_tabs()
        self._build_summary()
        self._build_status()

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, corner_radius=8)
        bar.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkButton(bar, text="📄 Add File", width=110, command=self._pick_file).pack(
            side="left", padx=(12, 6), pady=8
        )
        ctk.CTkButton(bar, text="📁 Add Folder", width=120, command=self._pick_folder).pack(
            side="left", padx=(0, 6), pady=8
        )
        ctk.CTkButton(
            bar, text="✕ Clear", width=80, fg_color="transparent", border_width=1, command=self._clear
        ).pack(side="left", padx=(0, 16), pady=8)

        _SectionLabel(bar, text="Model:").pack(side="left", padx=(0, 6))
        names = [m.display_name for m in self._models]
        self._model_var = ctk.StringVar(value=names[0] if names else "")
        ctk.CTkOptionMenu(
            bar,
            values=names,
            variable=self._model_var,
            width=220,
            command=self._on_model_change,
        ).pack(side="left", padx=(0, 16), pady=8)

        _SectionLabel(bar, text="Est. output tokens:").pack(side="left", padx=(0, 6))
        self._output_var = ctk.StringVar(value="500")
        ctk.CTkEntry(bar, textvariable=self._output_var, width=80).pack(
            side="left", padx=(0, 16), pady=8
        )

        self._btn_analyse = ctk.CTkButton(
            bar,
            text="⚡ Analyse",
            width=110,
            fg_color="#01696f",
            hover_color="#0c4e54",
            command=self._run_analysis,
        )
        self._btn_analyse.pack(side="right", padx=12, pady=8)

        self._path_frame = ctk.CTkScrollableFrame(self, height=60, corner_radius=6)
        self._path_frame.pack(fill="x", padx=12, pady=(0, 6))
        self._paths: list[Path] = []

    def _build_tabs(self) -> None:
        self._tabs = ctk.CTkTabview(self)
        self._tabs.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        tab_results = self._tabs.add("Results")
        tab_logs    = self._tabs.add("Logs")

        _SectionLabel(tab_results, text="Results").pack(anchor="w", padx=4, pady=(4, 2))
        self._table = ResultsTable(tab_results, corner_radius=8)
        self._table.pack(fill="both", expand=True, padx=4, pady=(0, 6))

        self._logs_view = LogsView(tab_logs)
        self._logs_view.pack(fill="both", expand=True)

    def _build_summary(self) -> None:
        self._summary = _SummaryPanel(self, corner_radius=8)
        self._summary.pack(fill="x", padx=12, pady=(0, 6))

    def _build_status(self) -> None:
        self._status_var = ctk.StringVar(value="Ready — pick a file or folder to begin.")
        ctk.CTkLabel(
            self,
            textvariable=self._status_var,
            font=ctk.CTkFont(size=11),
            text_color=_MUTED,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 8))

    def _pick_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a document",
            filetypes=[
                ("Supported files", "*.txt *.md *.pdf *.pptx *.docx *.py *.json"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._add_path(Path(path))

    def _pick_folder(self) -> None:
        path = filedialog.askdirectory(title="Select a folder")
        if path:
            self._add_path(Path(path))

    def _add_path(self, path: Path) -> None:
        if path in self._paths:
            return
        self._paths.append(path)
        ctk.CTkLabel(
            self._path_frame,
            text=str(path),
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(anchor="w", padx=4, pady=1)
        self._set_status(f"Added: {path.name}")

    def _clear(self) -> None:
        self._paths.clear()
        for w in self._path_frame.winfo_children():
            w.destroy()
        self._table.clear()
        self._summary.reset()
        self._results.clear()
        self._set_status("Cleared. Pick a file or folder to begin.")

    def _on_model_change(self, _: str) -> None:
        if self._paths:
            self._run_analysis()

    def _run_analysis(self) -> None:
        if not self._paths:
            self._set_status("⚠️  No files selected. Use 'Add File' or 'Add Folder' first.")
            return
        self._btn_analyse.configure(state="disabled", text="Analysing…")
        self._set_status("Analysing — please wait…")
        threading.Thread(target=self._analysis_worker, daemon=True).start()

    def _analysis_worker(self) -> None:
        model_name = self._model_var.get()
        model      = self._model_map[model_name]
        results: List[AnalysisResult] = []

        for path in self._paths:
            if path.is_dir():
                results.extend(analyze_folder(path, model.id))
            else:
                results.append(analyze_file(path, model.id))

        self._results = results
        self.after(0, self._render_results, results, model)

    def _render_results(self, results: List[AnalysisResult], model: ModelInfo) -> None:
        self._table.clear()
        for i, r in enumerate(results):
            self._table.add_result(r, i)
        self._summary.update(results, model)
        self._btn_analyse.configure(state="normal", text="⚡ Analyse")
        self._set_status(f"Done — {len(results)} file(s) analysed with {model.display_name}.")

    def _set_status(self, msg: str) -> None:
        self._status_var.set(msg)
