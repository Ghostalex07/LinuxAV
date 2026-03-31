import logging
import threading
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from linuxav.adapters.clamav_adapter import (
    ClamAVAdapter,
    ScanProgress as ClamScanProgress,
)
from linuxav.domain.models import ScanConfig, ScanResult
from linuxav.domain.enums import ScanStatus
from linuxav.domain.validators import validate_scan_path


@dataclass
class ScanProgressEvent:
    current_file: str = ""
    files_scanned: int = 0
    threats_found: int = 0
    current_threat: Optional[str] = None
    threat_file: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class ScanService:
    """Service for executing antivirus scans.
    
    Handles scan operations with real-time progress reporting.
    Decoupled from UI - uses callbacks for progress events.
    Supports cancellation via stop_scan().
    """

    def __init__(self):
        self.logger = logging.getLogger("linuxav.scan_service")
        self.clamav = ClamAVAdapter()
        self._scan_thread: Optional[threading.Thread] = None
        self._is_scanning = False
        self._should_stop = False
        self._progress_callbacks: list[Callable[[ScanProgressEvent], None]] = []
        self._on_complete_callback: Optional[Callable[[ScanResult], None]] = None

    @property
    def is_scanning(self) -> bool:
        return self._is_scanning

    def add_progress_callback(self, callback: Callable[[ScanProgressEvent], None]) -> None:
        self._progress_callbacks.append(callback)

    def remove_progress_callback(self, callback: Callable[[ScanProgressEvent], None]) -> None:
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)

    def set_complete_callback(self, callback: Callable[[ScanResult], None]) -> None:
        self._on_complete_callback = callback

    def scan_directory(
        self,
        path: str,
        recursive: bool = True,
        remove: bool = False,
        detect_pua: bool = True,
    ) -> ScanResult:
        valid, error_msg = validate_scan_path(path)
        if not valid:
            return ScanResult(
                path=path,
                status=ScanStatus.ERROR,
                error_message=error_msg,
            )

        if self._is_scanning:
            return ScanResult(
                path=path,
                status=ScanStatus.ERROR,
                error_message="Scan already in progress",
            )

        self._is_scanning = True
        self._should_stop = False

        try:
            config = ScanConfig(
                path=path,
                recursive=recursive,
                remove=remove,
                detect_pua=detect_pua,
            )

            response = self.clamav.scan(config, progress_callback=self._on_clamav_progress)

            return self._build_result(path, response)

        except Exception as e:
            self.logger.exception(f"Scan error: {e}")
            return ScanResult(
                path=path,
                status=ScanStatus.ERROR,
                error_message=str(e),
            )
        finally:
            self._is_scanning = False

    def scan_directory_async(
        self,
        path: str,
        recursive: bool = True,
        remove: bool = False,
        detect_pua: bool = True,
    ) -> bool:
        valid, error_msg = validate_scan_path(path)
        if not valid:
            self.logger.error(f"Invalid path: {error_msg}")
            return False

        if self._is_scanning:
            self.logger.warning("Scan already in progress")
            return False

        self._scan_thread = threading.Thread(
            target=self._async_scan_worker,
            args=(path, recursive, remove, detect_pua),
            daemon=True,
        )
        self._scan_thread.start()
        return True

    def _async_scan_worker(
        self,
        path: str,
        recursive: bool,
        remove: bool,
        detect_pua: bool,
    ):
        result = self.scan_directory(path, recursive, remove, detect_pua)
        if self._on_complete_callback:
            try:
                self._on_complete_callback(result)
            except Exception as e:
                self.logger.error(f"Complete callback error: {e}")

    def stop_scan(self) -> None:
        """Stop the current scan by terminating the ClamAV process."""
        if not self._is_scanning:
            return
        
        self._should_stop = True
        self.logger.info("Stopping scan - requesting ClamAV adapter to stop")
        
        # Stop the ClamAV adapter which will kill the subprocess
        self.clamav.stop_scan()
        
        self.logger.info("Stop requested completed")

    def get_clamscan_version(self) -> str:
        return self.clamav.get_version()

    def is_clamav_available(self) -> bool:
        return self.clamav.is_available()

    def _on_clamav_progress(self, progress: ClamScanProgress):
        event = ScanProgressEvent(
            current_file=progress.current_file,
            files_scanned=progress.files_scanned,
            threats_found=progress.threats_found,
        )
        self._notify_progress(event)

    def _notify_progress(self, event: ScanProgressEvent):
        for callback in self._progress_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Progress callback error: {e}")

    def _build_result(self, path: str, response) -> ScanResult:
        threat_name = None
        if hasattr(response, 'threats') and response.threats:
            threat_name = response.threats[0][1]

        return ScanResult(
            path=path,
            status=response.status,
            threat_name=threat_name,
            scanned_files=response.scanned_files,
            threats_found=response.threats_found,
            error_message=response.error,
        )
