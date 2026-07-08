"""Model Registry — read-only browsable grid of every configured model."""

from __future__ import annotations

import webbrowser

import customtkinter as ctk

from norefund.core.models_registry import ModelInfo
from norefund.gui import formatting, theme
from norefund.gui.theme import COLORS, ICONS
from norefund.gui.widgets import ProviderBadge, bind_mousewheel

_MIN_CARD_WIDTH = 300


class RegistryView(ctk.CTkFrame):
    def __init__(self, parent, shell) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.shell = shell
        self._active_provider = "All"
        self._pills: dict[str, ctk.CTkButton] = {}
        self._cards: list[tuple[ModelInfo, ctk.CTkFrame]] = []
        self._loading = False
        self._last_col_count = -1

        self._build_header()
        self._build_grid()
        bind_mousewheel(self._scroll)
        self._start_loading()

    # ------------------------------------------------------------------

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 12))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            left,
            text="Model Registry",
            font=theme.font(16, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(fill="x")
        providers = sorted({m.provider for m in self.shell.models})
        subtitle = (
            f"{len(self.shell.models)} models across {len(providers)} providers"
            " — offline pricing data."
        )
        ctk.CTkLabel(
            left,
            text=subtitle,
            font=theme.font(11),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        pills_row = ctk.CTkFrame(header, fg_color="transparent")
        pills_row.pack(side="right")
        for label in ["All", *providers]:
            pill = ctk.CTkButton(
                pills_row,
                text=label,
                font=theme.font(11),
                corner_radius=14,
                height=26,
                width=1,
                fg_color=COLORS["muted"],
                text_color=COLORS["muted_fg"],
                hover_color=COLORS["border"],
                command=lambda p=label: self._apply_filter(p),
            )
            pill.pack(side="left", padx=3)
            self._pills[label] = pill
        self._sync_pill_styles()

    def _sync_pill_styles(self) -> None:
        for label, pill in self._pills.items():
            if label == self._active_provider:
                pill.configure(
                    fg_color=COLORS["primary"], text_color=COLORS["primary_fg"]
                )
            else:
                pill.configure(fg_color=COLORS["muted"], text_color=COLORS["muted_fg"])

    def _sync_pill_enabled(self) -> None:
        state = "disabled" if self._loading else "normal"
        for pill in self._pills.values():
            pill.configure(state=state)

    def _build_grid(self) -> None:
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"])
        self._scroll.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self._scroll.bind("<Configure>", lambda _e: self._relayout())
        # Parented on the canvas (the scroll area's actual visible viewport,
        # not the inner content frame that grows/shrinks with card count) so
        # relx/rely=0.5 centers it on the screen the user sees, regardless
        # of scroll position or how many cards end up being built.
        self._loading_label = ctk.CTkLabel(
            self._scroll._parent_canvas,
            text="Loading models…",
            font=theme.font(12),
            text_color=COLORS["muted_fg"],
        )

    # ------------------------------------------------------------------
    # Loading: build every real card off-screen first, then reveal them
    # all together in one grid pass. A plain text label covers the wait
    # instead of a skeleton grid.
    # ------------------------------------------------------------------

    def _start_loading(self) -> None:
        self._loading = True
        self._cards = []
        self._sync_pill_enabled()
        self._loading_label.place(relx=0.5, rely=0.5, anchor="center")
        self.after(1, self._build_next_card, 0, [])

    def _build_next_card(
        self, index: int, built: list[tuple[ModelInfo, ctk.CTkFrame]]
    ) -> None:
        if not self.winfo_exists():
            return
        if index >= len(self.shell.models):
            self._finish_loading(built)
            return
        # Built off-screen (never gridded here) so cards only become visible
        # once all of them are ready, in a single _relayout call.
        model = self.shell.models[index]
        built.append((model, self._build_card(model)))
        self.after(1, self._build_next_card, index + 1, built)

    def _finish_loading(self, built: list[tuple[ModelInfo, ctk.CTkFrame]]) -> None:
        if not self.winfo_exists():
            return
        self._loading = False
        self._loading_label.place_forget()
        self._cards = built
        self._sync_pill_enabled()
        self._relayout(force=True)

    def _refresh_scrollregion(self) -> None:
        """Force the canvas scrollregion to match current content.

        CTkScrollableFrame is supposed to keep this in sync via an internal
        <Configure> binding, but that doesn't reliably fire on every grid
        change here - a stale/empty scrollregion lets the canvas scroll past
        real content into empty space. Recomputing it explicitly after every
        grid change keeps scrolling bounded to what's actually on screen.
        """
        canvas = self._scroll._parent_canvas
        self._scroll.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _build_card(self, model: ModelInfo) -> ctk.CTkFrame:
        accent = theme.provider_color(model.provider)
        card = ctk.CTkFrame(self._scroll, fg_color=COLORS["card"], corner_radius=6)

        header_tint = (
            formatting.tint(accent, COLORS["card"][0], 0.09),
            formatting.tint(accent, COLORS["card"][1], 0.09),
        )
        header = ctk.CTkFrame(card, fg_color=header_tint, corner_radius=0)
        header.pack(fill="x")
        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=14, pady=10)
        top_row = ctk.CTkFrame(header_inner, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(
            top_row,
            text=model.display_name,
            font=theme.font(13, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(side="left")
        ProviderBadge(top_row, model.provider).pack(side="right")
        ctk.CTkLabel(
            header_inner,
            text=model.id,
            font=theme.mono_font(10),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(
            body,
            text="Context window",
            font=theme.font(10),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            body,
            text=formatting.fmt_context_window(model.context_window),
            font=theme.mono_font(13, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        pricing = ctk.CTkFrame(body, fg_color="transparent")
        pricing.pack(fill="x")
        pricing.columnconfigure((0, 1), weight=1)
        self._price_cell(pricing, 0, "Input / 1M", model.input_price_per_million)
        self._price_cell(pricing, 1, "Output / 1M", model.output_price_per_million)

        footer = ctk.CTkFrame(card, fg_color="transparent", border_width=0)
        ctk.CTkFrame(footer, fg_color=COLORS["border"], height=1).pack(fill="x")
        footer_inner = ctk.CTkFrame(footer, fg_color="transparent")
        footer_inner.pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(
            footer_inner,
            text=f"{ICONS['hash']} {model.tokenizer_name}",
            font=theme.mono_font(10),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(side="left")
        if model.docs_url:
            docs_btn = ctk.CTkLabel(
                footer_inner,
                text=f"Docs {ICONS['external_link']}",
                font=theme.font(10),
                text_color=COLORS["primary"],
                cursor="hand2",
            )
            docs_btn.pack(side="right")
            docs_btn.bind(
                "<Button-1>", lambda _e, url=model.docs_url: webbrowser.open(url)
            )
        footer.pack(fill="x")

        return card

    def _price_cell(self, parent, col: int, label: str, price: float) -> None:
        cell = ctk.CTkFrame(parent, fg_color=COLORS["muted"], corner_radius=4)
        cell.grid(
            row=0,
            column=col,
            sticky="ew",
            padx=(0 if col == 0 else 6, 0 if col == 1 else 6),
        )
        inner = ctk.CTkFrame(cell, fg_color="transparent")
        inner.pack(padx=8, pady=6, fill="x")
        ctk.CTkLabel(
            inner,
            text=label,
            font=theme.font(9),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            inner,
            text=f"${price:,.2f}",
            font=theme.mono_font(12, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(fill="x")

    # ------------------------------------------------------------------

    def _apply_filter(self, provider: str) -> None:
        self._active_provider = provider
        self._sync_pill_styles()
        self._relayout(force=True)

    def _visible_cards(self) -> list[ctk.CTkFrame]:
        return [
            card
            for model, card in self._cards
            if self._active_provider == "All" or model.provider == self._active_provider
        ]

    def _relayout(self, force: bool = False) -> None:
        if not self.winfo_exists():
            return
        width = self._scroll.winfo_width()
        col_count = max(1, width // _MIN_CARD_WIDTH)
        if col_count == self._last_col_count and not force:
            return
        self._last_col_count = col_count

        for i in range(col_count):
            self._scroll.columnconfigure(i, weight=1)

        for model, card in self._cards:
            card.grid_forget()

        for index, card in enumerate(self._visible_cards()):
            row, col = divmod(index, col_count)
            card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

        self._refresh_scrollregion()
