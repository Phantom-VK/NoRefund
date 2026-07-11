"""GUI entry point."""

from __future__ import annotations

import customtkinter as ctk

from norefund.core.settings import SettingsStore
from norefund.gui.dnd import dnd_root_class
from norefund.gui.main_view import MainView

_APPEARANCE_MODE = {"system": "System", "light": "Light", "dark": "Dark"}

# customtkinter's CTk isn't a TkinterDnD.Tk subclass, so when tkinterdnd2 is
# installed we mix it in to get drop-target support; otherwise plain CTk.
_DndMixin = dnd_root_class()
_BaseWindow = (_DndMixin, ctk.CTk) if _DndMixin is not None else (ctk.CTk,)


class App(*_BaseWindow):
    def __init__(self) -> None:
        super().__init__()

        settings = SettingsStore().load()
        ctk.set_appearance_mode(_APPEARANCE_MODE.get(settings.theme, "System"))
        ctk.set_default_color_theme("blue")

        self.title("NoRefund — Token & Cost Analyzer")
        self.geometry("1360x800")
        self.minsize(1040, 640)

        MainView(self).pack(fill="both", expand=True)


if __name__ == "__main__":
    App().mainloop()
