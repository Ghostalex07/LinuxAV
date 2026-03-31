import logging
from typing import Optional, Callable, Dict, Any, Union

from linuxav.app.state import StateManager
from linuxav.app.events import EventBus, EventType
from linuxav.services.scan_service import ScanService
from linuxav.services.update_service import UpdateService, UpdateResult, UpdateProgress
from linuxav.services.log_service import LogService
from linuxav.domain.models import ScanResult
from linuxav.domain.enums import ScanStatus


class Controller:
    """Middleware controller connecting UI with services.
    
    Coordinates between services and UI, handles state management,
    and provides clean API for the presentation layer.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger("linuxav.controller")
        self.state = StateManager()
        self.event_bus = EventBus()
        
        self.scan_service = ScanService()
        self.update_service = UpdateService()
        self.log_service = LogService()

        self._setup_service_callbacks()
        self._get_password_callback: Optional[Callable[[], Optional[str]]] = None
        self.logger.info("Controller initialized")

    def _setup_service_callbacks(self) -> None:
        self.scan_service.set_complete_callback(self._on_scan_complete)
        self.scan_service.add_progress_callback(self._on_scan_progress)
        self.update_service.add_progress_callback(self._on_update_progress)

    def set_password_callback(self, callback: Callable[[], Optional[str]]) -> None:
        """Set callback to get sudo password from UI."""
        self._get_password_callback = callback

    def start_scan(
        self,
        path: str,
        recursive: bool = True,
        remove: bool = False,
        detect_pua: bool = True,
    ) -> bool:
        """Start a directory scan."""
        if self.state.is_scanning:
            self.logger.warning("Scan already in progress")
            return False

        self.logger.info(f"Starting scan: {path}")
        self.state.set_scanning(path)
        self.event_bus.publish(EventType.SCAN_STARTED, {"path": path})

        self.scan_service.scan_directory_async(
            path=path,
            recursive=recursive,
            remove=remove,
            detect_pua=detect_pua,
        )
        return True

    def cancel_scan(self) -> None:
        """Cancel current scan."""
        if not self.state.is_scanning:
            return

        self.logger.info("Cancelling scan")
        self.scan_service.stop_scan()
        self.state.set_idle()
        self.event_bus.publish(EventType.SCAN_CANCELLED, None)

    def update_database(self, timeout: int = 600, password: Optional[str] = None) -> bool:
        """Update ClamAV database."""
        if self.update_service.is_updating:
            self.logger.warning("Update already in progress")
            return False

        if not password and self._get_password_callback:
            password = self._get_password_callback()
        
        if not password:
            self.logger.warning("No password provided for update")
            self.event_bus.publish(EventType.UPDATE_COMPLETED, {
                "success": False,
                "message": "Sudo password required",
                "error": "password_required",
            })
            return False

        self.update_service.set_password(password)
        
        self.logger.info("Starting database update")
        self.event_bus.publish(EventType.UPDATE_STARTED, {"phase": "starting", "message": "Iniciando actualización..."})

        self.update_service.set_complete_callback(self._on_update_complete)
        return self.update_service.update_async(timeout)

    def cancel_update(self) -> bool:
        """Cancel ongoing database update."""
        if not self.update_service.is_updating:
            return False

        self.logger.info("Cancelling database update")
        success = self.update_service.cancel()

        if success:
            self.event_bus.publish(EventType.UPDATE_CANCELLED, {"message": "Actualización cancelada"})

        return success

    def check_clamav_status(self) -> Dict[str, Any]:
        """Get ClamAV status information."""
        return {
            "available": self.scan_service.is_clamav_available(),
            "version": self.scan_service.get_clamscan_version(),
            "is_scanning": self.state.is_scanning,
            "is_updating": self.update_service.is_updating,
            "status": self.state.status.value,
        }

    def get_scan_history(self, limit: int = 20) -> list[Dict[str, Any]]:
        """Get recent scan history."""
        return self.state.get_scan_history(limit)

    def get_logs(self, lines: int = 100) -> list[str]:
        """Get application logs."""
        return self.log_service.read_app_log(lines)

    def get_clam_logs(self, lines: int = 100) -> list[Dict[str, Any]]:
        """Get ClamAV logs."""
        entries = self.log_service.read_clam_log(lines)
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "level": e.level,
                "message": e.message,
            }
            for e in entries
        ]

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Get current state snapshot for UI."""
        return self.state.get_snapshot()

    def subscribe(self, event: Union[str, EventType], callback: Callable[[Any], None]) -> None:
        """Subscribe to events."""
        self.event_bus.subscribe(event, callback)

    def _on_scan_progress(self, progress: Any) -> None:
        self.state.update_progress(
            current_file=progress.current_file,
            files_scanned=progress.files_scanned,
            threats_found=progress.threats_found,
        )
        self.event_bus.publish(EventType.SCAN_PROGRESS, {
            "current_file": progress.current_file,
            "files_scanned": progress.files_scanned,
            "threats_found": progress.threats_found,
        })

    def _on_scan_complete(self, result: ScanResult) -> None:
        self.state.set_idle()
        self.state.last_scan_time = result.timestamp

        scan_record: Dict[str, Any] = {
            "path": result.path,
            "status": result.status.value,
            "scanned_files": result.scanned_files,
            "threats_found": result.threats_found,
            "error": result.error_message,
        }
        self.state.add_scan_to_history(scan_record)

        self.event_bus.publish(EventType.SCAN_COMPLETED, {
            "path": result.path,
            "status": result.status.value,
            "scanned_files": result.scanned_files,
            "threats_found": result.threats_found,
            "threat_name": result.threat_name,
            "error": result.error_message,
        })
        self.logger.info(f"Scan completed: {result.status.value}")

    def _on_update_progress(self, progress: UpdateProgress) -> None:
        """Handle update progress events."""
        self.event_bus.publish(EventType.UPDATE_PROGRESS, {
            "phase": progress.phase,
            "message": progress.message,
            "percent": progress.percent,
            "output_line": progress.output_line,
        })

    def _on_update_complete(self, result: UpdateResult) -> None:
        self.event_bus.publish(EventType.UPDATE_COMPLETED, {
            "success": result.success,
            "message": result.message,
            "output": result.output,
            "error": result.error,
        })
        self.logger.info(f"Update completed: {result.success} - {result.message}")
