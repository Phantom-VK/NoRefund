"""Model registry screen."""

from __future__ import annotations

import webbrowser

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
        self._cards: list[tuple[ModelInfo, ctk.CTkFrame]] = []
        self._build()
        self._build_cards()
        self._apply_filter()

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
        for p in ["All", *sorted({model.provider for model in self.models})]:
            IconButton(
                filters,
                p,
                width=max(58, len(p) * 10),
                command=lambda p=p: self._set_provider(p),
            ).pack(side="left", padx=(0, 6), pady=2)

        self.model_grid = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.model_grid.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 20))
        self.model_grid.grid_columnconfigure((0, 1, 2), weight=1, uniform="model")

    def _build_cards(self) -> None:
        for model in self.models:
            card = self._make_card(model)
            self._cards.append((model, card))

    def _make_card(self, model: ModelInfo) -> ctk.CTkFrame:
        accent = provider_color(model.provider)
        card = ctk.CTkFrame(self.model_grid, fg_color=COLORS["card"], corner_radius=8)
        head = ctk.CTkFrame(card, fg_color=accent, corner_radius=0, height=4)
        head.pack(fill="x")
        ctk.CTkLabel(
            card,
            text=model.display_name,
            text_color=COLORS["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 0))
        ctk.CTkLabel(
            card,
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
        for text in [
            f"Context window      {fmt_num(model.context_window)} tokens",
            f"Input / 1M          ${model.input_price_per_million:.2f}",
            f"Output / 1M         ${model.output_price_per_million:.2f}",
        ]:
            ctk.CTkLabel(
                card,
                text=text,
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
        ).pack(fill="x", padx=14, pady=(10, 2))
        if model.docs_url:
            docs_label = ctk.CTkLabel(
                card,
                text="Docs & pricing ↗",
                text_color=accent,
                font=ctk.CTkFont(size=11, weight="bold"),
                anchor="w",
                cursor="hand2",
            )
            docs_label.pack(fill="x", padx=14, pady=(0, 12))
            docs_label.bind(
                "<Button-1>", lambda _e, url=model.docs_url: webbrowser.open(url)
            )
        else:
            ctk.CTkLabel(
                card,
                text="Docs link unavailable",
                text_color=COLORS["muted_text"],
                font=ctk.CTkFont(size=11),
                anchor="w",
            ).pack(fill="x", padx=14, pady=(0, 12))
        return card

    def _set_provider(self, provider: str) -> None:
        self.provider = provider
        self._apply_filter()

    def _apply_filter(self) -> None:
        col = 0
        row = 0
        for model, card in self._cards:
            if self.provider == "All" or model.provider == self.provider:
                card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
                col += 1
                if col > 2:
                    col = 0
                    row += 1
            else:
                card.grid_remove()
