"""CustomTkinter root window."""

import customtkinter as ctk

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("NoRefund — Token & Cost Analyzer")
        self.geometry("1000x680")
        self.minsize(800, 560)
        self._setup_views()

    def _setup_views(self) -> None:
        from norefund.gui.views import MainView

        MainView(self).pack(fill="both", expand=True)
