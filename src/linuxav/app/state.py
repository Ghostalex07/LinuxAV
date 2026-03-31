import threading
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from linuxav.domain.enums import ScanStatus


@dataclass
class ScanProgress:
    current_file: str = ""
    files_scanned: int = 0
    threats_found: int = 0
    percent: float = 0.0


@dataclass
class AppState:
    status: ScanStatus = ScanStatus.CLEAN
    current_path: str = ""
    progress: ScanProgress = field(default_factory=ScanProgress)
    last_scan_time: Optional[datetime] = None
    database_version: str = ""
    database_date: str = ""


class StateManager:
    """Thread-safe state manager for the application.
    
    Uses locks to ensure safe concurrent access from multiple threads.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._state = AppState()
        self._scan_history: list[dict] = []
        self._max_history = 100

    @property
    def status(self) -> ScanStatus:
        with self._lock:
            return self._state.status

    @status.setter
    def status(self, value: ScanStatus):
        with self._lock:
            self._state.status = value

    @property
    def is_scanning(self) -> bool:
        with self._lock:
            return self._state.status == ScanStatus.SCANNING

    @property
    def current_path(self) -> str:
        with self._lock:
            return self._state.current_path

    @current_path.setter
    def current_path(self, value: str):
        with self._lock:
            self._state.current_path = value

    @property
    def progress(self) -> ScanProgress:
        with self._lock:
            return self._state.progress

    def update_progress(
        self,
        current_file: str = "",
        files_scanned: int = 0,
        threats_found: int = 0,
        percent: float = 0.0,
    ):
        with self._lock:
            self._state.progress = ScanProgress(
                current_file=current_file,
                files_scanned=files_scanned,
                threats_found=threats_found,
                percent=percent,
            )

    @property
    def database_version(self) -> str:
        with self._lock:
            return self._state.database_version

    @database_version.setter
    def database_version(self, value: str):
        with self._lock:
            self._state.database_version = value

    @property
    def database_date(self) -> str:
        with self._lock:
            return self._state.database_date

    @database_date.setter
    def database_date(self, value: str):
        with self._lock:
            self._state.database_date = value

    @property
    def last_scan_time(self) -> Optional[datetime]:
        with self._lock:
            return self._state.last_scan_time

    @last_scan_time.setter
    def last_scan_time(self, value: datetime):
        with self._lock:
            self._state.last_scan_time = value

    def set_scanning(self, path: str):
        with self._lock:
            self._state.status = ScanStatus.SCANNING
            self._state.current_path = path
            self._state.progress = ScanProgress()

    def set_idle(self):
        with self._lock:
            self._state.status = ScanStatus.CLEAN
            self._state.current_path = ""

    def add_scan_to_history(self, result: dict):
        with self._lock:
            result["timestamp"] = datetime.now().isoformat()
            self._scan_history.append(result)
            if len(self._scan_history) > self._max_history:
                self._scan_history.pop(0)

    def get_scan_history(self, limit: int = 20) -> list[dict]:
        with self._lock:
            return self._scan_history[-limit:]

    def clear_history(self):
        with self._lock:
            self._scan_history.clear()

    def get_snapshot(self) -> dict:
        with self._lock:
            return {
                "status": self._state.status.value,
                "is_scanning": self._state.status == ScanStatus.SCANNING,
                "current_path": self._state.current_path,
                "progress": {
                    "current_file": self._state.progress.current_file,
                    "files_scanned": self._state.progress.files_scanned,
                    "threats_found": self._state.progress.threats_found,
                    "percent": self._state.progress.percent,
                },
                "database_version": self._state.database_version,
                "last_scan_time": (
                    self._state.last_scan_time.isoformat()
                    if self._state.last_scan_time
                    else None
                ),
            }
