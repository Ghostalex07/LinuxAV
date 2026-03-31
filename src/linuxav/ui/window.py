import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading


class MainWindow:
    """Main window UI for LinuxAV using Tkinter.
    
    Pure presentation layer - all actions delegated to controller.
    Uses reusable widgets and centralized styles.
    """

    def __init__(self, controller):
        self.controller = controller
        self.root = tk.Tk()
        self.root.title("LinuxAV")

        from linuxav.ui.styles import get_dimensions
        dims = get_dimensions()
        self.root.geometry(f"{dims['window_width']}x{dims['window_height']}")
        self.root.configure(bg="#1e1e1e")

        from linuxav.ui.styles import apply_theme
        apply_theme()

        self._create_widgets()
        self._bind_events()
        self._check_clamav()

    def _create_widgets(self):
        from linuxav.ui.styles import get_dimensions
        from linuxav.ui.widgets import StatusBar, ScanControls, ProgressBar, OutputConsole, PasswordDialog

        dims = get_dimensions()
        pad = dims["padding"]
        spacing = dims["spacing"]

        main_frame = ttk.Frame(self.root, style="Dark.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=pad, pady=pad)

        title = ttk.Label(main_frame, text="LinuxAV - Antivirus", style="Title.TLabel")
        title.pack(pady=(0, spacing))

        self.status_bar = StatusBar(main_frame)
        self.status_bar.pack(fill=tk.X, pady=(0, spacing))

        self.scan_controls = ScanControls(
            main_frame,
            on_full_scan=self._on_full_scan,
            on_folder_scan=self._on_folder_scan,
            on_update=self._on_update,
            on_cancel=self._on_cancel,
        )
        self.scan_controls.pack(fill=tk.X, pady=(0, spacing))

        self.progress_bar = ProgressBar(main_frame, show_label=True)
        self.progress_bar.pack(fill=tk.X, pady=(0, spacing))

        self.console = OutputConsole(main_frame)
        self.console.pack(fill=tk.BOTH, expand=True)

    def _bind_events(self):
        self.controller.subscribe("scan_started", self._on_scan_started)
        self.controller.subscribe("scan_progress", self._on_scan_progress)
        self.controller.subscribe("scan_completed", self._on_scan_completed)
        self.controller.subscribe("scan_cancelled", self._on_scan_cancelled)
        self.controller.subscribe("update_started", self._on_update_started)
        self.controller.subscribe("update_progress", self._on_update_progress)
        self.controller.subscribe("update_completed", self._on_update_completed)
        self.controller.subscribe("update_cancelled", self._on_update_cancelled)

    def _check_clamav(self):
        def check():
            status = self.controller.check_clamav_status()
            available = status.get("available", False)
            version = status.get("version", "N/A")

            if available:
                self.root.after(0, lambda: self.status_bar.set_info(f"ClamAV: {version}"))
            else:
                self.root.after(0, lambda: self.status_bar.set_info("ClamAV: No encontrado"))
                self.root.after(0, lambda: self.console.write_line("WARNING: ClamAV no encontrado"))

        threading.Thread(target=check, daemon=True).start()

    def _on_full_scan(self):
        self.controller.start_scan("/", recursive=True, remove=False)

    def _on_folder_scan(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta para escanear")
        if path:
            self.controller.start_scan(path, recursive=True, remove=False)

    def _on_update(self):
        from linuxav.ui.widgets import PasswordDialog
        
        dialog = PasswordDialog(self.root)
        password = dialog.show()
        
        if password:
            self.controller.update_database(password=password)

    def _on_cancel(self):
        # Try to cancel scan first, then update
        if self.controller.state.is_scanning:
            self.controller.cancel_scan()
        elif self.controller.update_service.is_updating:
            self.controller.cancel_update()

    def _on_scan_started(self, data):
        self.root.after(0, self._update_scan_started_ui, data)

    def _update_scan_started_ui(self, data):
        path = data.get("path", "")
        self.status_bar.set_scanning(path)
        self.progress_bar.start()
        self.scan_controls.set_enabled(False)
        self.scan_controls.set_cancel_enabled(True)
        self.console.write_line(f"Iniciando escaneo: {path}")

    def _on_scan_progress(self, data):
        self.root.after(0, self._update_scan_progress_ui, data)

    def _update_scan_progress_ui(self, data):
        files = data.get("files_scanned", 0)
        threats = data.get("threats_found", 0)
        current_file = data.get("current_file", "")

        self.progress_bar.set_label(f"Archivos: {files} | Amenazas: {threats}")
        if current_file:
            self.console.write(current_file + "\r")

    def _on_scan_completed(self, data):
        self.root.after(0, self._update_scan_completed_ui, data)

    def _update_scan_completed_ui(self, data):
        self.progress_bar.stop()
        self.scan_controls.set_enabled(True)
        self.scan_controls.set_cancel_enabled(False)

        status = data.get("status", "")
        scanned = data.get("scanned_files", 0)
        threats = data.get("threats_found", 0)
        error = data.get("error")

        if error:
            self.status_bar.set_error(error)
            self.console.write_line(f"ERROR: {error}")
        elif status == "infected":
            self.status_bar.set_status(f"INFECTADO - {threats} amenazas")
            self.console.write_line(f"ESCANEO COMPLETO: {threats} amenazas encontradas")
            messagebox.showwarning("Análisis completo", f"Se encontraron {threats} amenazas")
        else:
            self.status_bar.set_success("Limpio")
            self.console.write_line(f"ESCANEO COMPLETO: {scanned} archivos escaneados, limpio")

        self.progress_bar.set_label("Listo")

    def _on_scan_cancelled(self, data):
        self.root.after(0, self._update_scan_cancelled_ui)

    def _update_scan_cancelled_ui(self):
        self.progress_bar.stop()
        self.scan_controls.set_enabled(True)
        self.scan_controls.set_cancel_enabled(False)
        self.status_bar.set_status("Escaneo cancelado")
        self.progress_bar.set_label("Cancelado")
        self.console.write_line("Escaneo cancelado por el usuario")

    # Update events
    def _on_update_started(self, data):
        self.root.after(0, self._update_update_started_ui, data)

    def _update_update_started_ui(self, data):
        message = data.get("message", "Iniciando actualización...")
        self.status_bar.set_status(message)
        self.progress_bar.start()
        self.scan_controls.set_enabled(False)
        self.scan_controls.set_cancel_enabled(True)
        self.console.write_line("=" * 50)
        self.console.write_line("Iniciando actualización de base de datos...")

    def _on_update_progress(self, data):
        self.root.after(0, self._update_update_progress_ui, data)

    def _update_update_progress_ui(self, data):
        phase = data.get("phase", "")
        message = data.get("message", "")
        output_line = data.get("output_line")
        percent = data.get("percent", 0)

        if percent > 0:
            self.progress_bar.set_label(f"Actualizando... {percent:.0f}%")

        if output_line:
            self.console.write(output_line)
        elif message:
            self.console.write_line(message)

    def _on_update_completed(self, data):
        self.root.after(0, self._update_update_completed_ui, data)

    def _update_update_completed_ui(self, data):
        self.progress_bar.stop()
        self.scan_controls.set_enabled(True)
        self.scan_controls.set_cancel_enabled(False)

        success = data.get("success", False)
        message = data.get("message", "")
        output = data.get("output", "")
        error = data.get("error")

        self.console.write_line("=" * 50)

        if success:
            self.status_bar.set_success("Base de datos actualizada")
            self.console.write_line("Base de datos actualizada correctamente")
            if output:
                for line in output.split("\n")[-5:]:
                    if line.strip():
                        self.console.write_line(f"  {line}")
        else:
            self.status_bar.set_error("Error en actualización")
            self.console.write_line(f"ERROR: {message}")
            if error and error != "cancelled":
                self.console.write_line(f"Detalles: {error}")

        self.progress_bar.set_label("Listo")

    def _on_update_cancelled(self, data):
        self.root.after(0, self._update_update_cancelled_ui, data)

    def _update_update_cancelled_ui(self, data):
        self.progress_bar.stop()
        self.scan_controls.set_enabled(True)
        self.scan_controls.set_cancel_enabled(False)
        self.status_bar.set_status("Actualización cancelada")
        self.progress_bar.set_label("Cancelado")
        self.console.write_line("=" * 50)
        self.console.write_line("Actualización cancelada por el usuario")

    def run(self):
        self.root.mainloop()
