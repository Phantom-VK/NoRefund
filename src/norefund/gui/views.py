"""Design-inspired CustomTkinter UI for NoRefund."""

from __future__ import annotations

import json
import math
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from norefund.core.models_registry import ModelInfo, list_models
from norefund.core.service import AnalysisResult, analyze_file, analyze_folder
from norefund.logging_config import latest_log_file

COLORS = {
    "bg": ("#f5f6f8", "#111318"),
    "card": ("#ffffff", "#1c2029"),
    "sidebar": ("#ffffff", "#181c23"),
    "muted": ("#e8eaed", "#242830"),
    "input": ("#eef0f3", "#242830"),
    "border": ("#d9dde3", "#30363d"),
    "text": ("#0f1117", "#e6edf3"),
    "muted_text": ("#6b7280", "#7d8590"),
    "primary": ("#00b894", "#00d4aa"),
    "primary_hover": ("#00a383", "#00bd98"),
    "primary_text": ("#ffffff", "#0d1117"),
    "danger": ("#ef4444", "#f85149"),
    "warning": ("#f59e0b", "#f59e0b"),
    "sidebar_accent": ("#f0faf8", "#17352f"),
}

PROVIDER_COLORS = {
    "OpenAI": "#10a37f",
    "Anthropic": "#d4a373",
    "Google": "#4285f4",
    "DeepSeek": "#5b5ea6",
    "Meta": "#0668e1",
    "Mistral": "#fa7343",
}

SUPPORTED_FILETYPES = [
    ("Supported files", "*.txt *.md *.pdf *.pptx *.docx *.py *.json"),
    ("All files", "*.*"),
]


def _fmt_num(value: int | float) -> str:
    return f"{value:,.0f}"


def _fmt_float(value: float, decimals: int = 1) -> str:
    return f"{value:,.{decimals}f}"


def _fmt_cost(value: float) -> str:
    if value < 0.01:
        return f"${value:.6f}"
    return f"${value:,.2f}"


def _parse_int(value: str) -> int:
    try:
        return max(0, int(value.replace(",", "").strip() or "0"))
    except ValueError:
        return 0


def _context_color(pct: float) -> str:
    if pct >= 100:
        return COLORS["danger"][1]
    if pct >= 75:
        return COLORS["warning"][1]
    return COLORS["primary"][1]


def _provider_color(provider: str) -> str:
    return PROVIDER_COLORS.get(provider, COLORS["primary"][1])


def _context_pct(tokens: int, model: ModelInfo) -> float:
    if model.context_window <= 0:
        return 0
    return (tokens / model.context_window) * 100


def _chunks(tokens: int, model: ModelInfo) -> int:
    if tokens <= 0:
        return 0
    if model.context_window <= 0:
        return 0
    return max(1, math.ceil(tokens / model.context_window))


def _model_label(model: ModelInfo) -> str:
    return f"{model.display_name}  ·  {model.provider}"


class ContextBar(ctk.CTkFrame):
    def __init__(self, parent, height: int = 7, **kw) -> None:
        super().__init__(parent, fg_color="transparent", **kw)
        self._bar = ctk.CTkProgressBar(
            self,
            height=height,
            fg_color=COLORS["muted"],
            progress_color=COLORS["primary"],
        )
        self._bar.set(0)
        self._bar.pack(fill="x", expand=True)

    def set_value(self, pct: float) -> None:
        self._bar.set(min(max(pct, 0), 100) / 100)
        self._bar.configure(progress_color=_context_color(pct))


class StatPill(ctk.CTkFrame):
    def __init__(self, parent, label: str, value: str = "-", **kw) -> None:
        super().__init__(parent, fg_color="transparent", **kw)
        ctk.CTkLabel(
            self,
            text=label.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["muted_text"],
            anchor="w",
        ).pack(anchor="w")
        self._value = ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont(size=14, weight="bold", family="monospace"),
            text_color=COLORS["text"],
            anchor="w",
        )
        self._value.pack(anchor="w", pady=(2, 0))

    def set(self, value: str) -> None:
        self._value.configure(text=value)


class IconButton(ctk.CTkButton):
    def __init__(self, parent, text: str, variant: str = "muted", **kw) -> None:
        if variant == "primary":
            colors = {
                "fg_color": COLORS["primary"],
                "hover_color": COLORS["primary_hover"],
                "text_color": COLORS["primary_text"],
            }
        elif variant == "danger":
            colors = {
                "fg_color": COLORS["muted"],
                "hover_color": ("#fee2e2", "#3a2428"),
                "text_color": COLORS["danger"],
            }
        else:
            colors = {
                "fg_color": COLORS["muted"],
                "hover_color": ("#dde2e8", "#303640"),
                "text_color": COLORS["text"],
            }
        colors.update(kw)
        super().__init__(
            parent,
            text=text,
            corner_radius=5,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            **colors,
        )


class ModelDropdown(ctk.CTkOptionMenu):
    def __init__(self, parent, models: list[ModelInfo], command=None, **kw) -> None:
        self.models = models
        self.model_by_label = {_model_label(model): model for model in models}
        values = list(self.model_by_label)
        self.var = ctk.StringVar(value=values[0] if values else "")
        super().__init__(
            parent,
            values=values,
            variable=self.var,
            command=command,
            fg_color=COLORS["muted"],
            button_color=COLORS["muted"],
            button_hover_color=("gray75", "gray25"),
            text_color=COLORS["text"],
            dropdown_fg_color=COLORS["card"],
            dropdown_hover_color=COLORS["muted"],
            dropdown_text_color=COLORS["text"],
            corner_radius=5,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            **kw,
        )

    def selected_model(self) -> ModelInfo:
        return self.model_by_label[self.var.get()]


class SidebarItem(ctk.CTkButton):
    def __init__(self, parent, label: str, icon: str, command) -> None:
        super().__init__(
            parent,
            text=f"{icon}  {label}",
            command=command,
            anchor="w",
            height=36,
            corner_radius=5,
            fg_color="transparent",
            hover_color=COLORS["muted"],
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=13, weight="bold"),
        )

    def set_active(self, active: bool) -> None:
        self.configure(
            fg_color=COLORS["sidebar_accent"] if active else "transparent",
            text_color=COLORS["primary"] if active else COLORS["muted_text"],
        )


class SettingsModal(ctk.CTkToplevel):
    def __init__(self, parent: MainView) -> None:
        super().__init__(parent)
        self.title("Settings")
        self.geometry("430x330")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=8)
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            header,
            text="Settings",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(side="left")
        IconButton(header, "x", width=30, command=self.destroy).pack(side="right")

        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=8)

        ctk.CTkLabel(
            body, text="Default currency", text_color=COLORS["muted_text"], anchor="w"
        ).pack(fill="x")
        ctk.CTkOptionMenu(
            body,
            values=["USD", "EUR", "GBP", "INR"],
            fg_color=COLORS["input"],
            button_color=COLORS["input"],
            state="disabled",
        ).pack(fill="x", pady=(4, 14))

        ctk.CTkLabel(
            body,
            text="Default output tokens estimate",
            text_color=COLORS["muted_text"],
            anchor="w",
        ).pack(fill="x")
        ctk.CTkEntry(
            body,
            textvariable=parent.default_output_tokens,
            fg_color=COLORS["input"],
            border_width=0,
        ).pack(fill="x", pady=(4, 14))

        parent.chunk_warnings = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            body,
            text="Show chunk warnings",
            variable=parent.chunk_warnings,
            progress_color=COLORS["primary"],
        ).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(
            body,
            text="Currency conversion and preference persistence are placeholders.",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(fill="x", pady=(8, 0))

        footer = ctk.CTkFrame(frame, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(4, 16))
        IconButton(footer, "Cancel", width=88, command=self.destroy).pack(
            side="right", padx=(8, 0)
        )
        IconButton(
            footer, "Save changes", variant="primary", width=120, command=self.destroy
        ).pack(side="right")


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
            text=(
                "Prices are estimates. Check each provider's pricing page "
                "for exact rates."
            ),
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
        input_tokens = _parse_int(self.input_tokens.get())
        output_tokens = _parse_int(self.output_tokens.get())
        input_cost = (input_tokens / 1_000_000) * model.input_price_per_million
        output_cost = (output_tokens / 1_000_000) * model.output_price_per_million
        pct = _context_pct(input_tokens, model)
        fits = input_tokens <= model.context_window
        color = _context_color(pct)

        self.context_bar.set_value(pct)
        self.context_pct_label.configure(text=f"{_fmt_float(pct)}%", text_color=color)
        context_text = (
            f"{_fmt_num(input_tokens)} input tokens of "
            f"{_fmt_num(model.context_window)} max"
        )
        self.context_detail.configure(text=context_text)
        if fits:
            self.fit_label.configure(
                text="OK  Fits in one context window", text_color=COLORS["primary"]
            )
        else:
            overage = input_tokens - model.context_window
            chunks_needed = _chunks(input_tokens, model)
            self.fit_label.configure(
                text=(
                    f"Exceeds by {_fmt_num(overage)} tokens - "
                    f"{chunks_needed} chunks required"
                ),
                text_color=COLORS["danger"],
            )
        self.input_cost.set(
            f"{_fmt_cost(input_cost)}  @ ${model.input_price_per_million:g}/M"
        )
        self.output_cost.set(
            f"{_fmt_cost(output_cost)}  @ ${model.output_price_per_million:g}/M"
        )
        self.total_cost.set(_fmt_cost(input_cost + output_cost))


class ResultsTable(ctk.CTkScrollableFrame):
    HEADERS = [
        "File",
        "Tokens",
        "Context %",
        "Fits?",
        "Chunks",
        "Input Cost",
        "Words",
        "Chars",
    ]
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
            _fmt_num(result.token_count),
            f"{_fmt_float(result.context_usage_pct)}%",
            "OK" if result.fits_in_context else "NO",
            str(result.min_chunks_needed),
            _fmt_cost(result.estimated_input_cost),
            _fmt_num(result.word_count),
            _fmt_num(result.char_count),
        ]
        for col, (value, width) in enumerate(zip(values, self.WIDTHS)):
            color = COLORS["text"]
            if col == 2:
                color = _context_color(result.context_usage_pct)
            if col == 3:
                color = (
                    COLORS["primary"] if result.fits_in_context else COLORS["danger"]
                )
            ctk.CTkLabel(
                self,
                text=value,
                width=width,
                fg_color=bg,
                text_color=color,
                font=ctk.CTkFont(
                    size=12, weight="bold" if col in {0, 1, 5} else "normal"
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
            self.text.insert(
                "end", "No logs yet. Run an analysis to see output here.\n"
            )
            return
        try:
            for line in path.read_text(encoding="utf-8").splitlines()[-120:]:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    ctx = obj.get("ctx") or {}
                    message = obj.get("message", "log")
                    self.text.insert(
                        "end", f"> [{obj.get('level', 'INFO')}] {message} {ctx}\n"
                    )
                except json.JSONDecodeError:
                    self.text.insert("end", line + "\n")
        except OSError as exc:
            self.text.insert("end", f"Error reading log file: {exc}\n")


class ParserView(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        main_view: MainView,
        models: list[ModelInfo],
        default_output: ctk.StringVar,
    ) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.parent_view = main_view
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
            toolbar, "Analyze", variant="primary", width=110, command=self._run_analysis
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
            self.parent_view.update_header_count(len(self.paths))

    def _remove_path(self, path: Path) -> None:
        self.paths = [item for item in self.paths if item != path]
        self.status.set(f"Removed {path.name}")
        self._render_files()
        self.parent_view.update_header_count(len(self.paths))

    def _clear(self) -> None:
        self.paths.clear()
        self.results.clear()
        self.status.set("Cleared. Add a file or folder to begin.")
        self._render_files()
        self._render_results()
        self.parent_view.update_header_count(0)

    def _render_files(self) -> None:
        for child in self.files_frame.winfo_children():
            child.destroy()
        if not self.paths:
            row = ctk.CTkFrame(self.files_frame, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=14)
            ctk.CTkLabel(
                row,
                text=(
                    'No files selected. Click "Add File" or '
                    '"Add Folder" to get started.'
                ),
                text_color=COLORS["muted_text"],
                anchor="w",
            ).pack(fill="x")
            return
        for path in self.paths:
            row = ctk.CTkFrame(
                self.files_frame, fg_color=COLORS["muted"], corner_radius=5
            )
            row.pack(fill="x", padx=18, pady=3)
            ctk.CTkLabel(
                row,
                text=f"{'[folder]' if path.is_dir() else '[file]'} {path}",
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
            except Exception as exc:  # noqa: BLE001 - report per-file failures in the UI.
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
        self.stat_files.set(str(count))
        self.stat_tokens.set(_fmt_num(total_tokens))
        self.stat_cost.set(_fmt_cost(total_cost))
        self.stat_context.set(f"{_fmt_float(avg_context)}%")


class RegistryView(ctk.CTkFrame):
    def __init__(self, parent, models: list[ModelInfo]) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.models = models
        self.provider = "All"
        self._build()
        self._render_models()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        ctk.CTkLabel(
            header,
            text="Model Registry",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=17, weight="bold"),
            anchor="w",
        ).pack(anchor="w")
        providers = len({model.provider for model in self.models})
        ctk.CTkLabel(
            header,
            text=(
                f"{len(self.models)} models across {providers} providers "
                "- offline pricing data."
            ),
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(anchor="w", pady=(2, 12))
        filters = ctk.CTkFrame(header, fg_color="transparent")
        filters.pack(fill="x")
        for provider in ["All", *sorted({model.provider for model in self.models})]:
            IconButton(
                filters,
                provider,
                width=max(58, len(provider) * 10),
                command=lambda p=provider: self._set_provider(p),
            ).pack(side="left", padx=(0, 6), pady=2)

        self.model_grid = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.model_grid.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 20))
        self.model_grid.grid_columnconfigure((0, 1, 2), weight=1, uniform="model")

    def _set_provider(self, provider: str) -> None:
        self.provider = provider
        self._render_models()

    def _render_models(self) -> None:
        for child in self.model_grid.winfo_children():
            child.destroy()
        models = [
            m
            for m in self.models
            if self.provider == "All" or m.provider == self.provider
        ]
        for idx, model in enumerate(models):
            self._model_card(model, idx // 3, idx % 3)

    def _model_card(self, model: ModelInfo, row: int, column: int) -> None:
        accent = _provider_color(model.provider)
        card = ctk.CTkFrame(self.model_grid, fg_color=COLORS["card"], corner_radius=6)
        card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)

        head = ctk.CTkFrame(card, fg_color=COLORS["muted"], corner_radius=6)
        head.pack(fill="x", padx=0, pady=0)
        ctk.CTkLabel(
            head,
            text=model.display_name,
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 0))
        ctk.CTkLabel(
            head,
            text=model.id,
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=10, family="monospace"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(
            card,
            text=model.provider.upper(),
            text_color=accent,
            font=ctk.CTkFont(size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 8))
        ctk.CTkLabel(
            card,
            text=f"Context window      {_fmt_num(model.context_window)} tokens",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=12, family="monospace"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=2)
        ctk.CTkLabel(
            card,
            text=f"Input / 1M          ${model.input_price_per_million:.2f}",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=12, family="monospace"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=2)
        ctk.CTkLabel(
            card,
            text=f"Output / 1M         ${model.output_price_per_million:.2f}",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=12, family="monospace"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=2)
        ctk.CTkLabel(
            card,
            text=f"Tokenizer: {model.tokenizer_name}",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=10, family="monospace"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 12))
        ctk.CTkLabel(
            card,
            text="Docs link: backend field pending",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 12))


class MainView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.models = list_models()
        self.default_output_tokens = ctk.StringVar(value="500")
        self.current_nav = "parser"
        self.header_count = ctk.StringVar(value="0 files")
        self.title_var = ctk.StringVar(value="File Parser")
        self.theme_dark = True
        self.views: dict[str, ctk.CTkFrame] = {}

        self._build_shell()
        self._show_view("parser")

    def _build_shell(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(
            self, width=210, fg_color=COLORS["sidebar"], corner_radius=0
        )
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        logo = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo.pack(fill="x", padx=16, pady=(18, 16))
        ctk.CTkLabel(
            logo,
            text="$",
            width=32,
            height=32,
            fg_color=COLORS["primary"],
            text_color=COLORS["primary_text"],
            corner_radius=5,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left")
        brand = ctk.CTkFrame(logo, fg_color="transparent")
        brand.pack(side="left", padx=10)
        ctk.CTkLabel(
            brand,
            text="NoRefund",
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand,
            text="TOKEN & COST ANALYZER",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=9, weight="bold"),
            anchor="w",
        ).pack(anchor="w")

        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.pack(fill="x", expand=True, padx=12)
        ctk.CTkLabel(
            nav,
            text="TOOLS",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=9, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(8, 4))
        self.nav_buttons = {
            "calculator": SidebarItem(
                nav, "Token Calculator", "#", lambda: self._show_view("calculator")
            ),
            "parser": SidebarItem(
                nav, "File Parser", "[]", lambda: self._show_view("parser")
            ),
            "registry": SidebarItem(
                nav, "Model Registry", "::", lambda: self._show_view("registry")
            ),
        }
        self.nav_buttons["calculator"].pack(fill="x", pady=2)
        self.nav_buttons["parser"].pack(fill="x", pady=2)
        ctk.CTkLabel(
            nav,
            text="DATA",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=9, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(16, 4))
        self.nav_buttons["registry"].pack(fill="x", pady=2)

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=14)
        ctk.CTkLabel(
            footer,
            text="100% offline. No API calls made.",
            text_color=COLORS["muted_text"],
            fg_color=COLORS["muted"],
            corner_radius=5,
            font=ctk.CTkFont(size=10),
            wraplength=150,
        ).pack(fill="x", pady=(0, 8), ipady=8)
        ctk.CTkLabel(
            footer,
            text="v0.1.0 · open-source",
            text_color=COLORS["muted_text"],
            font=ctk.CTkFont(size=9),
        ).pack()

        main = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(main, height=46, fg_color=COLORS["card"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        ctk.CTkLabel(
            header,
            textvariable=self.title_var,
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=(20, 8))
        self.count_badge = ctk.CTkLabel(
            header,
            textvariable=self.header_count,
            text_color=COLORS["muted_text"],
            fg_color=COLORS["muted"],
            corner_radius=4,
            font=ctk.CTkFont(size=10, family="monospace"),
        )
        self.count_badge.pack(side="left", ipadx=8, ipady=2)
        IconButton(header, "Settings", width=82, command=self._open_settings).pack(
            side="right", padx=(6, 18), pady=8
        )
        self.theme_btn = IconButton(
            header, "Light", width=68, command=self._toggle_theme
        )
        self.theme_btn.pack(side="right", padx=6, pady=8)

        self.content = ctk.CTkFrame(main, fg_color=COLORS["bg"], corner_radius=0)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.views = {
            "calculator": CalculatorView(
                self.content, self.models, self.default_output_tokens
            ),
            "parser": ParserView(
                self.content,
                self,
                self.models,
                self.default_output_tokens,
            ),
            "registry": RegistryView(self.content, self.models),
        }
        for view in self.views.values():
            view.grid(row=0, column=0, sticky="nsew")

    def _show_view(self, name: str) -> None:
        self.current_nav = name
        titles = {
            "calculator": "Token Calculator",
            "parser": "File Parser",
            "registry": "Model Registry",
        }
        self.title_var.set(titles[name])
        for key, button in self.nav_buttons.items():
            button.set_active(key == name)
        for key, view in self.views.items():
            if key == name:
                view.tkraise()
            else:
                view.lower()
        if name == "parser":
            self.count_badge.pack(side="left", ipadx=8, ipady=2)
        else:
            self.count_badge.pack_forget()

    def update_header_count(self, count: int) -> None:
        self.header_count.set(f"{count} file{'s' if count != 1 else ''}")

    def _toggle_theme(self) -> None:
        self.theme_dark = not self.theme_dark
        ctk.set_appearance_mode("Dark" if self.theme_dark else "Light")
        self.theme_btn.configure(text="Light" if self.theme_dark else "Dark")

    def _open_settings(self) -> None:
        SettingsModal(self)
