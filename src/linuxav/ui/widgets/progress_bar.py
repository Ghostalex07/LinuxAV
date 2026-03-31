import tkinter as tk
from tkinter import ttk


class ProgressBar(ttk.Frame):
    """Reusable progress bar widget.
    
    Provides a progress bar with optional label.
    """

    def __init__(self, parent, show_label: bool = True):
        super().__init__(parent)
        self.configure(style="Dark.TFrame")

        self._show_label = show_label
        self._create_widgets()

    def _create_widgets(self):
        self.progress = ttk.Progressbar(
            self,
            mode="indeterminate",
            style="Dark.Horizontal.TProgressbar",
        )
        self.progress.pack(fill=tk.X)

        if self._show_label:
            self.label = ttk.Label(
                self,
                text="Listo",
                style="Dark.TLabel",
            )
            self.label.pack(pady=(5, 0))

    def start(self):
        self.progress.start(10)

    def stop(self):
        self.progress.stop()

    def set_label(self, text: str):
        if self._show_label:
            self.label.config(text=text)

    def reset(self):
        self.stop()
        self.set_label("Listo")

    def set_indeterminate(self, indeterminate: bool):
        mode = "indeterminate" if indeterminate else "determinate"
        self.progress.config(mode=mode)
