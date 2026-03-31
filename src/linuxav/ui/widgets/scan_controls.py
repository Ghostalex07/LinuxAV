import tkinter as tk
from tkinter import ttk


class ScanControls(ttk.Frame):
    """Reusable scan control buttons widget.
    
    Provides standardized scan action buttons.
    """

    def __init__(
        self,
        parent,
        on_full_scan=None,
        on_folder_scan=None,
        on_update=None,
        on_cancel=None,
    ):
        super().__init__(parent)
        self.configure(style="Dark.TFrame")

        self._on_full_scan = on_full_scan
        self._on_folder_scan = on_folder_scan
        self._on_update = on_update
        self._on_cancel = on_cancel

        self._create_widgets()

    def _create_widgets(self):
        self.btn_full = ttk.Button(
            self,
            text="Full Scan (/)",
            style="Dark.TButton",
            command=self._on_full_scan or (lambda: None),
        )
        self.btn_full.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_folder = ttk.Button(
            self,
            text="Scan Carpeta",
            style="Dark.TButton",
            command=self._on_folder_scan or (lambda: None),
        )
        self.btn_folder.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_update = ttk.Button(
            self,
            text="Update DB",
            style="Dark.TButton",
            command=self._on_update or (lambda: None),
        )
        self.btn_update.pack(side=tk.LEFT)

        self.btn_cancel = ttk.Button(
            self,
            text="Cancelar",
            style="Dark.TButton",
            command=self._on_cancel or (lambda: None),
            state=tk.DISABLED,
        )
        self.btn_cancel.pack(side=tk.RIGHT)

    def set_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.btn_full.config(state=state)
        self.btn_folder.config(state=state)
        self.btn_update.config(state=state)

    def set_cancel_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.btn_cancel.config(state=state)

    def set_buttons_enabled(self, enabled: bool, show_cancel: bool = False):
        self.set_enabled(enabled)
        self.set_cancel_enabled(show_cancel)
