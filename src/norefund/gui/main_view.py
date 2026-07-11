"""App shell: sidebar navigation, header, and view switching."""

from __future__ import annotations

import threading
from importlib.metadata import PackageNotFoundError, version
from tkinter import TclError

import customtkinter as ctk

from norefund.core.models_registry import list_models
from norefund.core.settings import SettingsStore
from norefund.gui import theme
from norefund.gui.theme import COLORS, ICONS
from norefund.gui.widgets import ModelDropdownButton, NoticeBanner, SidebarItem

_FALLBACK_VERSION = "0.1.0"

try:
    _APP_VERSION = version("norefund")
except PackageNotFoundError:
    _APP_VERSION = _FALLBACK_VERSION

_TITLES = {
    "calculator": "Token Calculator",
    "parser": "File Parser",
    "registry": "Model Registry",
    "resources": "Resources",
    "compare": "Compare Models",
}


class MainView(ctk.CTkFrame):
    VIEW_CALCULATOR = "calculator"
    VIEW_PARSER = "parser"
    VIEW_REGISTRY = "registry"
    VIEW_RESOURCES = "resources"
    VIEW_COMPARE = "compare"

    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.pack_propagate(False)

        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()
        self.models = list_models()

        self._nav_items: dict[str, SidebarItem] = {}
        self._view_cache: dict[str, ctk.CTkFrame] = {}
        self._current_view: str | None = None
        self._file_count = 0

        self._build_sidebar()
        right = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        right.pack(side="right", fill="both", expand=True)
        self._build_header(right)

        self._banner: NoticeBanner | None = None
        self._content = ctk.CTkFrame(right, fg_color=COLORS["bg"], corner_radius=0)
        self._content.pack(side="top", fill="both", expand=True)

        self.show_view(self.VIEW_CALCULATOR)
        self._bind_shortcuts()
        if not self.settings.onboarding_dismissed:
            threading.Thread(target=self._check_onboarding, daemon=True).start()

    # ------------------------------------------------------------------
    # First-run onboarding banner
    # ------------------------------------------------------------------

    def _check_onboarding(self) -> None:
        from norefund.core.resources import build_resource_report

        report = build_resource_report(self.models)
        if not any(t.is_cached for t in report.tokenizers):
            self._schedule(self._show_onboarding_banner)

    def _show_onboarding_banner(self) -> None:
        if not self.winfo_exists() or self.settings.onboarding_dismissed:
            return
        self._banner = NoticeBanner(
            self._content.master,
            "No tokenizers downloaded yet — counts will be rough approximations.",
            action_text="Open Resources",
            on_action=lambda: self.show_view(self.VIEW_RESOURCES),
            on_dismiss=self._dismiss_onboarding,
        )
        self._banner.pack(side="top", fill="x", before=self._content)

    def _dismiss_onboarding(self) -> None:
        self.settings.onboarding_dismissed = True
        self.settings_store.save(self.settings)

    def _schedule(self, callback, *args) -> None:
        if not self.winfo_exists():
            return
        try:
            self.after(0, callback, *args)
        except (TclError, RuntimeError):
            pass

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _bind_shortcuts(self) -> None:
        root = self.winfo_toplevel()
        view_order = [
            self.VIEW_CALCULATOR,
            self.VIEW_PARSER,
            self.VIEW_COMPARE,
            self.VIEW_REGISTRY,
            self.VIEW_RESOURCES,
        ]
        for i, view_id in enumerate(view_order, start=1):
            root.bind(f"<Control-Key-{i}>", lambda _e, v=view_id: self.show_view(v))
        root.bind("<Escape>", self._cancel_active_work)

    def _cancel_active_work(self, _event=None) -> None:
        view = self._view_cache.get(self._current_view)
        cancel_event = getattr(view, "cancel_event", None)
        if cancel_event is not None:
            cancel_event.set()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(
            self, width=208, fg_color=COLORS["sidebar"], corner_radius=0
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_row.pack(fill="x", padx=16, pady=(20, 16))
        ctk.CTkLabel(
            logo_row,
            text="$",
            width=28,
            height=28,
            corner_radius=6,
            fg_color=COLORS["primary"],
            text_color=COLORS["primary_fg"],
            font=theme.font(14, "bold"),
        ).pack(side="left")
        title_col = ctk.CTkFrame(logo_row, fg_color="transparent")
        title_col.pack(side="left", padx=(10, 0))
        ctk.CTkLabel(
            title_col,
            text="NoRefund",
            font=theme.font(14, "bold"),
            text_color=COLORS["sidebar_fg"],
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            title_col,
            text="TOKEN & COST ANALYZER",
            font=theme.font(9),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x")

        self._nav_section(
            sidebar,
            "Tools",
            [
                (self.VIEW_CALCULATOR, "Token Calculator", "calculator"),
                (self.VIEW_PARSER, "File Parser", "folder_open"),
                (self.VIEW_COMPARE, "Compare Models", "bar_chart"),
            ],
        )
        self._nav_section(
            sidebar,
            "Data",
            [
                (self.VIEW_REGISTRY, "Model Registry", "layers"),
                (self.VIEW_RESOURCES, "Resources", "hard_drive"),
            ],
        )

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=12, pady=12)
        warn = ctk.CTkFrame(footer, fg_color=COLORS["muted"], corner_radius=6)
        warn.pack(fill="x")
        ctk.CTkLabel(
            warn,
            text=(
                f"{ICONS['check']}  Local analysis. "
                "Your files never leave this machine."
            ),
            font=theme.font(10),
            text_color=COLORS["muted_fg"],
            wraplength=170,
            justify="left",
        ).pack(padx=8, pady=8, fill="x")
        ctk.CTkLabel(
            footer,
            text=f"v{_APP_VERSION} · open-source",
            font=theme.font(9),
            text_color=COLORS["muted_fg"],
        ).pack(pady=(8, 0))

    def _nav_section(
        self, parent, label: str, items: list[tuple[str, str, str]]
    ) -> None:
        ctk.CTkLabel(
            parent,
            text=label.upper(),
            font=theme.font(9, "bold"),
            text_color=COLORS["muted_fg"],
            anchor="w",
        ).pack(fill="x", padx=16, pady=(12, 4))
        for view_id, text, icon in items:
            item = SidebarItem(
                parent, text, icon, command=lambda v=view_id: self.show_view(v)
            )
            item.pack(fill="x", padx=10, pady=1)
            self._nav_items[view_id] = item

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self, parent) -> None:
        header = ctk.CTkFrame(
            parent, height=44, fg_color=COLORS["card"], corner_radius=0
        )
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=16)
        self._header_title = ctk.CTkLabel(
            left,
            text=_TITLES[self.VIEW_CALCULATOR],
            font=theme.font(14, "bold"),
            text_color=COLORS["fg"],
        )
        self._header_title.pack(side="left")
        self._header_badge = ctk.CTkLabel(
            left,
            text="",
            font=theme.font(10),
            fg_color=COLORS["muted"],
            text_color=COLORS["muted_fg"],
            corner_radius=8,
        )

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=12)
        self._theme_btn = ctk.CTkButton(
            right,
            text="",
            width=32,
            height=32,
            corner_radius=6,
            fg_color="transparent",
            hover_color=COLORS["muted"],
            text_color=COLORS["fg"],
            command=self._toggle_theme,
        )
        self._theme_btn.pack(side="left", padx=4)
        ctk.CTkButton(
            right,
            text=ICONS["settings"],
            width=32,
            height=32,
            corner_radius=6,
            fg_color="transparent",
            hover_color=COLORS["muted"],
            text_color=COLORS["fg"],
            command=self._open_settings,
        ).pack(side="left", padx=4)

        self._sync_theme_icon()

    def _sync_theme_icon(self) -> None:
        is_dark = ctk.get_appearance_mode() == "Dark"
        self._theme_btn.configure(text=ICONS["moon"] if is_dark else ICONS["sun"])

    def _toggle_theme(self) -> None:
        new_mode = "Light" if ctk.get_appearance_mode() == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self.settings.theme = new_mode.lower()
        self.settings_store.save(self.settings)
        self._sync_theme_icon()

    def _open_settings(self) -> None:
        from norefund.gui.settings_modal import SettingsModal

        SettingsModal(self, self.settings, self._on_settings_saved)

    def _on_settings_saved(self, settings) -> None:
        self.settings = settings

    # ------------------------------------------------------------------
    # View switching
    # ------------------------------------------------------------------

    def update_header_count(self, count: int) -> None:
        self._file_count = count
        if self._current_view == self.VIEW_PARSER and count > 0:
            self._header_badge.configure(
                text=f"{count} file{'s' if count != 1 else ''}"
            )
            self._header_badge.pack(side="left", padx=(10, 0), ipadx=6, ipady=2)
        else:
            self._header_badge.pack_forget()

    def show_view(self, view_id: str) -> None:
        # Popovers (e.g. the model dropdown) are separate CTkToplevels, so
        # raising a different cached view frame on top of them doesn't
        # close them on its own -- force it here on every navigation.
        ModelDropdownButton.close_all()
        for vid, item in self._nav_items.items():
            item.set_active(vid == view_id)

        if view_id not in self._view_cache:
            view = self._make_view(view_id)
            view.place(in_=self._content, x=0, y=0, relwidth=1, relheight=1)
            self._view_cache[view_id] = view
        self._view_cache[view_id].tkraise()

        self._current_view = view_id
        self._header_title.configure(text=_TITLES[view_id])
        self.update_header_count(self._file_count)

    def _make_view(self, view_id: str) -> ctk.CTkFrame:
        if view_id == self.VIEW_CALCULATOR:
            from norefund.gui.calculator_view import CalculatorView

            return CalculatorView(self._content, self)
        if view_id == self.VIEW_PARSER:
            from norefund.gui.parser_view import ParserView

            return ParserView(self._content, self)
        if view_id == self.VIEW_REGISTRY:
            from norefund.gui.registry_view import RegistryView

            return RegistryView(self._content, self)
        if view_id == self.VIEW_RESOURCES:
            from norefund.gui.resources_view import ResourcesView

            return ResourcesView(self._content, self)
        if view_id == self.VIEW_COMPARE:
            from norefund.gui.compare_view import CompareView

            return CompareView(self._content, self)
        raise ValueError(f"Unknown view: {view_id}")
