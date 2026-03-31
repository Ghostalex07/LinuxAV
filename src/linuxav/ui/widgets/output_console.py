import tkinter as tk
from tkinter import scrolledtext
from typing import Optional


class OutputConsole(scrolledtext.ScrolledText):
    """Reusable console output widget.
    
    Provides a scrollable text area for log/output display.
    """

    def __init__(self, parent, **kwargs):
        defaults = {
            "bg": "#0d0d0d",
            "fg": "#00ff88",
            "font": ("Consolas", 9),
            "state": tk.DISABLED,
            "wrap": tk.WORD,
        }
        defaults.update(kwargs)

        super().__init__(parent, **defaults)

    def write(self, message: str, newline: bool = True):
        self.config(state=tk.NORMAL)
        if newline:
            self.insert(tk.END, message + "\n")
        else:
            self.insert(tk.END, message)
        self.see(tk.END)
        self.config(state=tk.DISABLED)

    def write_line(self, message: str):
        self.write(message, newline=True)

    def clear(self):
        self.config(state=tk.NORMAL)
        self.delete(1.0, tk.END)
        self.config(state=tk.DISABLED)

    def set_colors(self, bg: Optional[str] = None, fg: Optional[str] = None):
        if bg:
            self.config(bg=bg)
        if fg:
            self.config(fg=fg)
