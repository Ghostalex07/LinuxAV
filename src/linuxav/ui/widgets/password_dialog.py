"""Password dialog for sudo authentication."""

import tkinter as tk
from tkinter import ttk


class PasswordDialog:
    """Modal dialog for entering sudo password."""

    def __init__(self, parent: tk.Tk, title: str = "Authentication Required"):
        self.result = None
        self._password = ""
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        
        self._create_widgets()
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.dialog.bind("<Return>", lambda _: self._on_ok())
        self.dialog.bind("<Escape>", lambda _: self._on_cancel())
        
        self.dialog.geometry("350x150")
        self.dialog.resizable(False, False)
        
        self.password_entry.focus_set()

    def _create_widgets(self) -> None:
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        label = ttk.Label(
            main_frame, 
            text="Enter sudo password for database update:",
            wraplength=300,
        )
        label.pack(pady=(0, 10))
        
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            main_frame,
            textvariable=self.password_var,
            show="*",
            width=30,
        )
        self.password_entry.pack(pady=(0, 15))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side=tk.RIGHT, padx=5)

    def _on_ok(self) -> None:
        self._password = self.password_var.get()
        self.dialog.destroy()

    def _on_cancel(self) -> None:
        self._password = ""
        self.dialog.destroy()

    def show(self) -> str:
        """Show dialog and return password or empty string if cancelled."""
        self.dialog.wait_window()
        return self._password