import tkinter as tk
from tkinter import ttk
from typing import Optional


class StatusBar(ttk.Frame):
    """Reusable status bar widget.
    
    Provides a status display with left and right sections.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.configure(style="Dark.TFrame")

        self._create_widgets()

    def _create_widgets(self):
        self.left_label = ttk.Label(
            self,
            text="Listo",
            style="Dark.TLabel",
        )
        self.left_label.pack(side=tk.LEFT)

        self.right_label = ttk.Label(
            self,
            text="",
            style="Dark.TLabel",
        )
        self.right_label.pack(side=tk.RIGHT)

    def set_status(self, text: str):
        self.left_label.config(text=text)

    def set_info(self, text: str):
        self.right_label.config(text=text)

    def set(self, left: Optional[str] = None, right: Optional[str] = None):
        if left is not None:
            self.set_status(left)
        if right is not None:
            self.set_info(right)

    def clear(self):
        self.left_label.config(text="Listo")
        self.right_label.config(text="")

    def set_scanning(self, path: str = ""):
        if path:
            self.set_status(f"Escaneando: {path}")
        else:
            self.set_status("Escaneando...")

    def set_idle(self, status: str = "Listo"):
        self.set_status(status)

    def set_error(self, message: str):
        self.set_status(f"Error: {message}")

    def set_success(self, message: str):
        self.set_status(message)
