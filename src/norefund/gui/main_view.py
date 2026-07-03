"""Main desktop application shell."""

from __future__ import annotations

import customtkinter as ctk

from norefund.core.models_registry import list_models
from norefund.core.settings import SettingsStore
from norefund.gui.calculator_view import CalculatorView
from norefund.gui.parser_view import ParserView
from norefund.gui.registry_view import RegistryView
from norefund.gui.settings_modal import SettingsModal
from norefund.gui.theme import COLORS, ICONS, mono_font
from norefund.gui.theme import font as themed_font
from norefund.gui.widgets import IconButton, SidebarItem

VIEW_CALCULATOR = "calculator"
VIEW_PARSER = "parser"
VIEW_REGISTRY = "registry"


class MainView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()

        self.models = list_models()
        self.default_output_tokens = ctk.StringVar(
            value=str(self.settings.default_output_tokens)
        )
        self.currency = ctk.StringVar(value=self.settings.currency)
        self.current_view = VIEW_PARSER
        self.header_count = ctk.StringVar(value="0 files")
        self.title_var = ctk.StringVar(value="File Parser")
        self.theme_dark = self.settings.theme != "light"
        self._view_cache: dict[str, ctk.CTkFrame] = {}

        self._build_shell()
        ctk.set_appearance_mode("Dark" if self.theme_dark else "Light")
        self._show_view(VIEW_PARSER)

    def _build_shell(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(
            self, width=210, fg_color=COLORS["sidebar"], corner_radius=0
        )
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        self._build_logo(sidebar)
        self._build_sidebar_nav(sidebar)
        self._build_sidebar_footer(sidebar)

        main = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        self._build_header(main)
        self._build_content(main)

    def _build_logo(self, sidebar: ctk.CTkFrame) -> None:
        logo = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo.pack(fill="x", padx=16, pady=(18, 8))
        ctk.CTkLabel(
            logo,
            text="$",
            width=32,
            height=32,
            fg_color=COLORS["primary"],
            text_color=COLORS["primary_text"],
            corner_radius=5,
            font=themed_font(18, "bold"),
        ).pack(side="left")
        brand = ctk.CTkFrame(logo, fg_color="transparent")
        brand.pack(side="left", padx=10)
        ctk.CTkLabel(
            brand,
            text="NoRefund",
            text_color=COLORS["text"],
            font=themed_font(15, "bold"),
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand,
            text="TOKEN & COST ANALYZER",
            text_color=COLORS["muted_text"],
            font=themed_font(9, "bold"),
            anchor="w",
        ).pack(anchor="w")

    def _build_sidebar_nav(self, sidebar: ctk.CTkFrame) -> None:
        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=12)
        ctk.CTkLabel(
            nav,
            text="TOOLS",
            text_color=COLORS["muted_text"],
            font=themed_font(9, "bold"),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(16, 4))
        self.nav_buttons = {
            VIEW_CALCULATOR: SidebarItem(
                nav,
                "Token Calculator",
                ICONS["calculator"],
                lambda: self._show_view(VIEW_CALCULATOR),
            ),
            VIEW_PARSER: SidebarItem(
                nav,
                "File Parser",
                ICONS["folder_open"],
                lambda: self._show_view(VIEW_PARSER),
            ),
            VIEW_REGISTRY: SidebarItem(
                nav,
                "Model Registry",
                ICONS["layers"],
                lambda: self._show_view(VIEW_REGISTRY),
            ),
        }
        self.nav_buttons[VIEW_CALCULATOR].pack(fill="x", pady=(0, 2))
        self.nav_buttons[VIEW_PARSER].pack(fill="x", pady=2)
        ctk.CTkLabel(
            nav,
            text="DATA",
            text_color=COLORS["muted_text"],
            font=themed_font(9, "bold"),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(16, 4))
        self.nav_buttons[VIEW_REGISTRY].pack(fill="x", pady=2)

    def _build_sidebar_footer(self, sidebar: ctk.CTkFrame) -> None:
        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=14)
        offline_note = ctk.CTkFrame(footer, fg_color=COLORS["muted"], corner_radius=5)
        offline_note.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            offline_note,
            text=ICONS["warning"],
            text_color=COLORS["warning"],
            font=themed_font(11),
        ).pack(side="left", padx=(8, 4), pady=8)
        ctk.CTkLabel(
            offline_note,
            text="100% offline. No API calls made.",
            text_color=COLORS["muted_text"],
            font=themed_font(10),
            wraplength=120,
            justify="left",
            anchor="w",
        ).pack(side="left", fill="x", expand=True, padx=(0, 8), pady=8)
        ctk.CTkLabel(
            footer,
            text="v0.1.0 · open-source",
            text_color=COLORS["muted_text"],
            font=themed_font(9),
        ).pack()

    def _build_header(self, main: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(main, height=46, fg_color=COLORS["card"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        ctk.CTkLabel(
            header,
            textvariable=self.title_var,
            text_color=COLORS["text"],
            font=themed_font(14, "bold"),
        ).pack(side="left", padx=(20, 8))
        self.count_badge = ctk.CTkLabel(
            header,
            textvariable=self.header_count,
            text_color=COLORS["muted_text"],
            fg_color=COLORS["muted"],
            corner_radius=4,
            font=mono_font(10),
        )
        self.count_badge.pack(side="left", ipadx=8, ipady=2)
        IconButton(
            header,
            ICONS["settings"],
            width=32,
            height=32,
            font=themed_font(15),
            command=self._open_settings,
        ).pack(side="right", padx=(6, 18), pady=7)
        self.theme_btn = IconButton(
            header,
            ICONS["sun"] if self.theme_dark else ICONS["moon"],
            width=32,
            height=32,
            font=themed_font(15),
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side="right", padx=6, pady=7)

    def _build_content(self, main: ctk.CTkFrame) -> None:
        self.content = ctk.CTkFrame(main, fg_color=COLORS["bg"], corner_radius=0)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def _make_view(self, name: str) -> ctk.CTkFrame:
        if name == VIEW_CALCULATOR:
            return CalculatorView(self.content, self.models, self.default_output_tokens)
        if name == VIEW_PARSER:
            return ParserView(self.content, self, self.models, self.default_output_tokens)
        if name == VIEW_REGISTRY:
            return RegistryView(self.content, self.models)
        raise ValueError(f"Unknown view: {name}")

    def _show_view(self, name: str) -> None:
        self.current_view = name
        titles = {
            VIEW_CALCULATOR: "Token Calculator",
            VIEW_PARSER: "File Parser",
            VIEW_REGISTRY: "Model Registry",
        }
        self.title_var.set(titles[name])
        for key, button in self.nav_buttons.items():
            button.set_active(key == name)

        if name not in self._view_cache:
            view = self._make_view(name)
            view.grid(row=0, column=0, sticky="nsew")
            self._view_cache[name] = view

        self._view_cache[name].tkraise()

        if name == VIEW_PARSER:
            self.count_badge.pack(side="left", ipadx=8, ipady=2)
        else:
            self.count_badge.pack_forget()

    def update_header_count(self, count: int) -> None:
        label = "file" if count == 1 else "files"
        self.header_count.set(f"{count} {label}")

    def _toggle_theme(self) -> None:
        self.theme_dark = not self.theme_dark
        ctk.set_appearance_mode("Dark" if self.theme_dark else "Light")
        glyph = ICONS["sun"] if self.theme_dark else ICONS["moon"]
        self.theme_btn.configure(text=glyph)
        self.settings.theme = "dark" if self.theme_dark else "light"
        self.settings_store.save(self.settings)

    def _open_settings(self) -> None:
        SettingsModal(self)
