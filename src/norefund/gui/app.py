"""CustomTkinter root window."""

import customtkinter as ctk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("NoRefund — Token & Cost Analyzer")
        self.geometry("1280x780")
        self.minsize(1040, 640)
        self._setup_views()

    def _setup_views(self) -> None:
        from norefund.gui.main_view import MainView

        MainView(self).pack(fill="both", expand=True)


if __name__ == "__main__":
    App().mainloop()
