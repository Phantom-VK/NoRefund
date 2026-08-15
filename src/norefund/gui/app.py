"""GUI entry point."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from norefund.core.settings import SettingsStore
from norefund.gui.dnd import dnd_root_class
from norefund.gui.main_view import MainView

_APPEARANCE_MODE = {"system": "System", "light": "Light", "dark": "Dark"}

# customtkinter's CTk isn't a TkinterDnD.Tk subclass, so when tkinterdnd2 is
# installed we mix it in to get drop-target support; otherwise plain CTk.
_DndMixin = dnd_root_class()
_BaseWindow = (_DndMixin, ctk.CTk) if _DndMixin is not None else (ctk.CTk,)


def _maximize(window: ctk.CTk) -> None:
    """Open `window` filling the screen, on any OS/window manager, without
    raising. Tries the native maximized state first (Windows and most X11
    window managers both support "zoomed"), then the X11 zoomed attribute,
    then falls back to an explicit full-screen geometry -- which has no OS
    or window-manager dependency and always works. Keeps the title bar and
    window controls (this is "maximized", not borderless fullscreen).

    Both native attempts are verified, not just assumed to have worked:
    `-zoomed` in particular is accepted without error even when nothing
    actually enforces it (e.g. no window manager, or a minimal/tiling one
    that ignores the hint), so a bare `try/except TclError` alone would
    silently leave the window at its pre-maximize size in that case.
    """
    try:
        window.state("zoomed")
        window.update_idletasks()
        if window.state() == "zoomed":
            return
    except tk.TclError:
        pass
    try:
        window.attributes("-zoomed", True)
        window.update_idletasks()
        if window.attributes("-zoomed"):
            return
    except tk.TclError:
        pass
    window.geometry(f"{window.winfo_screenwidth()}x{window.winfo_screenheight()}+0+0")


class App(*_BaseWindow):
    def __init__(self) -> None:
        super().__init__()

        settings = SettingsStore().load()
        ctk.set_appearance_mode(_APPEARANCE_MODE.get(settings.theme, "System"))
        ctk.set_default_color_theme("blue")

        self.title("NoRefund — Token & Cost Analyzer")
        # Pre-maximize fallback size/floor -- applied briefly before
        # _maximize() takes effect, and minsize is what the window can be
        # resized down to afterward, so both need to fit a 1366x768 laptop
        # screen (a common resolution this app was previously too tall for).
        self.geometry("1440x900")
        self.minsize(1024, 640)
        _maximize(self)

        MainView(self).pack(fill="both", expand=True)


if __name__ == "__main__":
    App().mainloop()
