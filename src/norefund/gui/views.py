"""Main view — placeholder until feat/gui-foundation."""

import customtkinter as ctk


class MainView(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent)
        ctk.CTkLabel(
            self,
            text="NoRefund",
            font=ctk.CTkFont(size=32, weight="bold"),
        ).pack(pady=(80, 8))
        ctk.CTkLabel(
            self,
            text="Token counter and cost estimator for LLMs.",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        ).pack()
        ctk.CTkLabel(
            self,
            text="GUI coming in feat/gui-foundation",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).pack(pady=(40, 0))
