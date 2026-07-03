"""Model registry screen."""

from __future__ import annotations

import webbrowser

import customtkinter as ctk

from norefund.core.models_registry import ModelInfo
from norefund.gui.formatting import fmt_num, provider_color, tint
from norefund.gui.theme import COLORS, mono_font
from norefund.gui.theme import font as themed_font
from norefund.gui.widgets import IconButton, ProviderBadge


class RegistryView(ctk.CTkFrame):
    def __init__(self, parent, models: list[ModelInfo]) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.models = models
        self.provider = "All"
        self._cards: list[tuple[ModelInfo, ctk.CTkFrame]] = []
        self.filter_buttons: dict[str, IconButton] = {}
        self._build()
        self._build_cards()
        self._apply_filter()
        self._style_filters()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 12))
        ctk.CTkLabel(
            header,
            text="Model Registry",
            text_color=COLORS["text"],
            font=themed_font(17, "bold"),
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
            font=themed_font(12),
            anchor="w",
        ).pack(anchor="w", pady=(2, 12))
        filters = ctk.CTkFrame(header, fg_color="transparent")
        filters.pack(fill="x")
        for p in ["All", *sorted({model.provider for model in self.models})]:
            btn = IconButton(
                filters,
                p,
                width=max(58, len(p) * 10),
                height=24,
                corner_radius=12,
                command=lambda p=p: self._set_provider(p),
            )
            btn.pack(side="left", padx=(0, 6), pady=2)
            self.filter_buttons[p] = btn

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

        head = ctk.CTkFrame(card, fg_color=tint(accent, 0.09), corner_radius=0)
        head.pack(fill="x")
        head_text = ctk.CTkFrame(head, fg_color="transparent")
        head_text.pack(side="left", fill="x", expand=True, padx=14, pady=10)
        ctk.CTkLabel(
            head_text,
            text=model.display_name,
            text_color=COLORS["text"],
            font=themed_font(14, "bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            head_text,
            text=model.id,
            text_color=COLORS["muted_text"],
            font=mono_font(10),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))
        ProviderBadge(head, model.provider).pack(side="right", padx=14)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=14, pady=12)

        ctx_row = ctk.CTkFrame(body, fg_color="transparent")
        ctx_row.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            ctx_row,
            text="Context window",
            text_color=COLORS["muted_text"],
            font=themed_font(10),
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            ctx_row,
            text=f"{fmt_num(model.context_window)} tokens",
            text_color=COLORS["text"],
            font=mono_font(12, "bold"),
            anchor="e",
        ).pack(side="right")

        tiles = ctk.CTkFrame(body, fg_color="transparent")
        tiles.pack(fill="x", pady=(0, 10))
        tiles.grid_columnconfigure((0, 1), weight=1, uniform="price")
        for col, (label, price) in enumerate(
            [
                ("Input / 1M", model.input_price_per_million),
                ("Output / 1M", model.output_price_per_million),
            ]
        ):
            tile = ctk.CTkFrame(tiles, fg_color=COLORS["muted"], corner_radius=5)
            tile.grid(row=0, column=col, sticky="ew", padx=(0, 6) if col == 0 else 0)
            ctk.CTkLabel(
                tile,
                text=label,
                text_color=COLORS["muted_text"],
                font=themed_font(9),
                anchor="w",
            ).pack(fill="x", padx=10, pady=(6, 0))
            ctk.CTkLabel(
                tile,
                text=f"${price:.2f}",
                text_color=COLORS["text"],
                font=mono_font(13, "bold"),
                anchor="w",
            ).pack(fill="x", padx=10, pady=(0, 6))

        divider = ctk.CTkFrame(body, height=1, fg_color=COLORS["border"])
        divider.pack(fill="x", pady=(0, 8))

        footer = ctk.CTkFrame(body, fg_color="transparent")
        footer.pack(fill="x")
        ctk.CTkLabel(
            footer,
            text=model.tokenizer_name,
            text_color=COLORS["muted_text"],
            font=mono_font(10),
            anchor="w",
        ).pack(side="left")
        if model.docs_url:
            docs_label = ctk.CTkLabel(
                footer,
                text="Docs & pricing ↗",
                text_color=accent,
                font=themed_font(11, "bold"),
                cursor="hand2",
            )
            docs_label.pack(side="right")
            docs_label.bind(
                "<Button-1>", lambda _e, url=model.docs_url: webbrowser.open(url)
            )
        else:
            ctk.CTkLabel(
                footer,
                text="Docs link unavailable",
                text_color=COLORS["muted_text"],
                font=themed_font(11),
            ).pack(side="right")
        return card

    def _style_filters(self) -> None:
        for provider, btn in self.filter_buttons.items():
            active = provider == self.provider
            btn.configure(
                fg_color=COLORS["primary"] if active else COLORS["muted"],
                text_color=COLORS["primary_text"] if active else COLORS["muted_text"],
            )

    def _set_provider(self, provider: str) -> None:
        self.provider = provider
        self._apply_filter()
        self._style_filters()

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
