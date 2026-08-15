"""Model Registry — read-only browsable grid of every configured model."""

from __future__ import annotations

import webbrowser

import customtkinter as ctk

from norefund.core.models_registry import ModelInfo
from norefund.gui import formatting, motion, theme
from norefund.gui.theme import COLORS
from norefund.gui.widgets import LoadingOverlay, ProviderBadge, bind_mousewheel, card

_MIN_CARD_WIDTH = 340
_PILL_HEIGHT = theme.CONTROL_SM


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
        header.pack(
            fill="x", padx=theme.PAGE_GUTTER, pady=(theme.SPACE_5, theme.SPACE_3)
        )

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            left,
            text="Model Registry",
            font=theme.font(theme.FONT_HEADING, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(fill="x")
        providers = sorted({m.provider for m in self.shell.models})
        subtitle = (
            f"{len(self.shell.models)} models across {len(providers)} providers"
            " — locally stored pricing data."
        )
        ctk.CTkLabel(
            left,
            text=subtitle,
            font=theme.font(theme.FONT_BODY),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(theme.SPACE_1, 0))

        pills_row = ctk.CTkFrame(header, fg_color="transparent")
        pills_row.pack(side="right")
        for label in ["All", *providers]:
            pill = ctk.CTkButton(
                pills_row,
                text=label,
                font=theme.font(theme.FONT_BODY),
                corner_radius=_PILL_HEIGHT // 2,
                height=_PILL_HEIGHT,
                width=1,
                fg_color=COLORS["muted"],
                text_color=COLORS["muted_fg"],
                hover_color=COLORS["border"],
                command=lambda p=label: self._apply_filter(p),
            )
            pill.pack(side="left", padx=theme.SPACE_1)
            motion.press_feedback(pill)
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
        self._scroll.pack(
            fill="both", expand=True, padx=theme.PAGE_GUTTER, pady=(0, theme.SPACE_5)
        )
        # Tk's bindtags put the scroll frame's pathname in every descendant
        # card's bindtags too, so a plain bind() here fires on each of the
        # ~40 model cards' own Configure events, not just the scroll
        # frame's own resize -- filter to the real thing (same pattern as
        # widgets.py's root <Configure> handler).
        self._scroll.bind(
            "<Configure>",
            lambda e: self._relayout() if e.widget is self._scroll else None,
        )
        self._loading_overlay = LoadingOverlay(self._scroll, "Loading models…")

    # ------------------------------------------------------------------
    # Loading: build every real card off-screen first, then reveal them
    # all together in one grid pass. A plain text label covers the wait
    # instead of a skeleton grid.
    # ------------------------------------------------------------------

    def _start_loading(self) -> None:
        self._loading = True
        self._cards = []
        self._sync_pill_enabled()
        self._loading_overlay.show()
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
        self._loading_overlay.hide()
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
        model_card = card(self._scroll)

        header_tint = (
            formatting.blend(accent, COLORS["card"][0], 0.09),
            formatting.blend(accent, COLORS["card"][1], 0.09),
        )
        header = ctk.CTkFrame(model_card, fg_color=header_tint, corner_radius=0)
        header.pack(fill="x")
        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=theme.SPACE_4, pady=theme.SPACE_3)
        top_row = ctk.CTkFrame(header_inner, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(
            top_row,
            text=model.display_name,
            font=theme.font(theme.FONT_TITLE, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(side="left")
        ProviderBadge(top_row, model.provider).pack(side="right")
        ctk.CTkLabel(
            header_inner,
            text=model.id,
            font=theme.mono_font(theme.FONT_SMALL),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", pady=(theme.SPACE_1, 0))

        body = ctk.CTkFrame(model_card, fg_color="transparent")
        body.pack(fill="x", padx=theme.SPACE_4, pady=theme.SPACE_3)
        ctk.CTkLabel(
            body,
            text="Context window",
            font=theme.font(theme.FONT_SMALL),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            body,
            text=formatting.fmt_context_window(model.context_window),
            font=theme.mono_font(theme.FONT_TITLE, "bold"),
            text_color=COLORS["fg"],
            anchor="w",
        ).pack(fill="x", pady=(0, theme.SPACE_3))

        pricing = ctk.CTkFrame(body, fg_color="transparent")
        pricing.pack(fill="x")
        pricing.columnconfigure((0, 1), weight=1)
        self._price_cell(pricing, 0, "Input / 1M", model.input_price_per_million)
        self._price_cell(pricing, 1, "Output / 1M", model.output_price_per_million)

        footer = ctk.CTkFrame(model_card, fg_color="transparent", border_width=0)
        ctk.CTkFrame(footer, fg_color=COLORS["border"], height=1).pack(fill="x")
        footer_inner = ctk.CTkFrame(footer, fg_color="transparent")
        footer_inner.pack(fill="x", padx=theme.SPACE_4, pady=theme.SPACE_2)
        ctk.CTkLabel(
            footer_inner,
            text=model.tokenizer_name,
            image=theme.icon_image("hash", size=12, color=COLORS["muted_fg"]),
            compound="left",
            font=theme.mono_font(theme.FONT_SMALL),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(side="left")
        if model.docs_url:
            docs_btn = ctk.CTkLabel(
                footer_inner,
                text="Docs",
                image=theme.icon_image(
                    "external_link", size=12, color=COLORS["primary"]
                ),
                compound="right",
                font=theme.font(theme.FONT_SMALL),
                text_color=COLORS["primary"],
                cursor="hand2",
            )
            docs_btn.pack(side="right")
            docs_btn.bind(
                "<Button-1>", lambda _e, url=model.docs_url: webbrowser.open(url)
            )
        footer.pack(fill="x")

        return model_card

    def _price_cell(self, parent, col: int, label: str, price: float) -> None:
        cell = ctk.CTkFrame(
            parent, fg_color=COLORS["muted"], corner_radius=theme.RADIUS_CARD
        )
        # Only ever called with col=0 (left cell) or col=1 (right cell): a
        # gap between them, no outer padding.
        padx = (0, theme.SPACE_2) if col == 0 else (theme.SPACE_2, 0)
        cell.grid(row=0, column=col, sticky="ew", padx=padx)
        inner = ctk.CTkFrame(cell, fg_color="transparent")
        inner.pack(padx=theme.SPACE_2, pady=theme.SPACE_2, fill="x")
        ctk.CTkLabel(
            inner,
            text=label,
            font=theme.font(theme.FONT_MICRO),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            inner,
            text=f"${price:,.2f}",
            font=theme.mono_font(theme.FONT_LABEL, "bold"),
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
            card_frame
            for model, card_frame in self._cards
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

        for model, card_frame in self._cards:
            card_frame.grid_forget()

        for index, card_frame in enumerate(self._visible_cards()):
            row, col = divmod(index, col_count)
            card_frame.grid(
                row=row,
                column=col,
                sticky="nsew",
                padx=theme.SPACE_2,
                pady=theme.SPACE_2,
            )

        self._refresh_scrollregion()
