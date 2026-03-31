import logging
import threading
import queue
from pathlib import Path
from typing import Optional, Callable, Set
from dataclasses import dataclass


@dataclass
class FileEvent:
    path: str
    event_type: str


class MonitorService:
    """Service for monitoring filesystem changes using inotify.
    
    Detects new/modified files and can trigger automatic scans.
    Uses efficient inotify mechanism.
    """

    WATCHED_EVENTS = (
        "IN_CREATE",
        "IN_MODIFY",
        "IN_MOVED_TO",
    )

    def __init__(self):
        self.logger = logging.getLogger("linuxav.monitor_service")
        self._is_monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._watched_paths: Set[str] = set()
        self._file_queue: queue.Queue = queue.Queue()
        self._on_file_callback: Optional[Callable[[str], None]] = None
        self._inotify_fd: Optional[int] = None

    def set_file_callback(self, callback: Callable[[str], None]):
        self._on_file_callback = callback

    def start_monitoring(self, paths: list[str]) -> bool:
        if self._is_monitoring:
            self.logger.warning("Already monitoring")
            return False

        try:
            import inotify.adapters
            self._inotify = inotify.adapters.Inotify()
        except ImportError:
            self.logger.error("python-inotify not installed")
            self.logger.info("Install with: pip install inotify")
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize inotify: {e}")
            return False

        self._watched_paths = set()
        for path in paths:
            p = Path(path)
            if p.exists() and p.is_dir():
                try:
                    self._inotify.add_watch(str(p))
                    self._watched_paths.add(str(p))
                    self.logger.info(f"Watching: {path}")
                except Exception as e:
                    self.logger.warning(f"Cannot watch {path}: {e}")

        if not self._watched_paths:
            self.logger.error("No paths to monitor")
            return False

        self._is_monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_worker,
            daemon=True,
        )
        self._monitor_thread.start()
        self.logger.info(f"Monitoring started: {self._watched_paths}")
        return True

    def stop_monitoring(self):
        if not self._is_monitoring:
            return

        self._is_monitoring = False

        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)

        if self._inotify:
            try:
                self._inotify.remove_watch
            except Exception:
                pass

        self.logger.info("Monitoring stopped")

    def _monitor_worker(self):
        try:
            for event in self._inotify.event_gen(yield_nonascii_timeouts=True):
                if not self._is_monitoring:
                    break

                if event is None:
                    continue

                (_, event_type_names, path, filename) = event

                if any(
                    name in self.WATCHED_EVENTS
                    for name in event_type_names
                ):
                    full_path = str(Path(path) / filename) if filename else path

                    if self._on_file_callback:
                        try:
                            self._on_file_callback(full_path)
                        except Exception as e:
                            self.logger.error(f"File callback error: {e}")

        except Exception as e:
            self.logger.exception(f"Monitor error: {e}")
        finally:
            self._is_monitoring = False

    def get_watched_paths(self) -> set[str]:
        return self._watched_paths.copy()

    @property
    def is_monitoring(self) -> bool:
        return self._is_monitoring
