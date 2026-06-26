"""Model registry screen."""

from __future__ import annotations

import customtkinter as ctk

from norefund.core.models_registry import ModelInfo
from norefund.gui.formatting import fmt_num, provider_color
from norefund.gui.theme import COLORS
from norefund.gui.widgets import IconButton


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
            model
            for model in self.models
            if self.provider == "All" or model.provider == self.provider
        ]
        for idx, model in enumerate(models):
            self._model_card(model, idx // 3, idx % 3)

    def _model_card(self, model: ModelInfo, row: int, column: int) -> None:
        accent = provider_color(model.provider)
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
            text=f"Context window      {fmt_num(model.context_window)} tokens",
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
