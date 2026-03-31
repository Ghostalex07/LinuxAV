import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class ClamLogEntry:
    timestamp: datetime
    level: str
    message: str
    source: Optional[str] = None


class LogService:
    """Service for parsing and managing ClamAV logs.
    
    Reads and parses log files from /var/log/clamav/
    and application logs.
    """

    CLAM_LOG_PATHS = [
        "/var/log/clamav/clamav.log",
        "/var/log/clamav/freshclam.log",
        "logs/clamav.log",
    ]

    def __init__(self, app_log_dir: Optional[Path] = None):
        self.logger = logging.getLogger("linuxav.log_service")
        self._app_log_dir = app_log_dir or Path("logs")

    def find_clam_log(self) -> Optional[Path]:
        for log_path in self.CLAM_LOG_PATHS:
            p = Path(log_path)
            if p.exists() and p.is_file():
                return p
        return None

    def read_clam_log(self, lines: Optional[int] = None) -> list[ClamLogEntry]:
        log_path = self.find_clam_log()
        if not log_path:
            return []

        try:
            content = log_path.read_text()
            entries = self._parse_log_content(content)

            if lines:
                return entries[-lines:]
            return entries

        except PermissionError:
            self.logger.warning(f"Cannot read {log_path}: permission denied")
            return []
        except Exception as e:
            self.logger.error(f"Error reading log: {e}")
            return []

    def _parse_log_content(self, content: str) -> list[ClamLogEntry]:
        entries = []
        timestamp_pattern = re.compile(
            r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})"
        )
        level_pattern = re.compile(r"(INFO|WARNING|ERROR|DEBUG)", re.IGNORECASE)

        for line in content.split("\n"):
            if not line.strip():
                continue

            ts_match = timestamp_pattern.search(line)
            level_match = level_pattern.search(line)

            timestamp = datetime.now()
            if ts_match:
                try:
                    timestamp = datetime.strptime(
                        ts_match.group(1), "%b %d %H:%M:%S"
                    )
                except ValueError:
                    pass

            level = "INFO"
            if level_match:
                level = level_match.group(1).upper()

            entries.append(ClamLogEntry(
                timestamp=timestamp,
                level=level,
                message=line.strip(),
            ))

        return entries

    def get_scan_summary(self) -> dict:
        """Get summary of recent scans from logs."""
        entries = self.read_clam_log(lines=500)

        scans = {"clean": 0, "infected": 0, "errors": 0}

        for entry in entries:
            msg = entry.message.upper()
            if "FOUND" in msg:
                scans["infected"] += 1
            elif "SCAN" in msg or "SCANNED" in msg:
                scans["clean"] += 1
            elif "ERROR" in msg:
                scans["errors"] += 1

        return scans

    def get_threats_from_log(self) -> list[dict]:
        """Extract detected threats from log."""
        entries = self.read_clam_log()
        threats = []

        threat_pattern = re.compile(r"(.+?)\s+FOUND\s+(.+)")

        for entry in entries:
            if "FOUND" in entry.message:
                match = threat_pattern.search(entry.message)
                if match:
                    threats.append({
                        "file": match.group(1),
                        "threat": match.group(2),
                        "timestamp": entry.timestamp.isoformat(),
                    })

        return threats

    def write_app_log(self, message: str, level: str = "INFO"):
        """Write to application log file."""
        self._app_log_dir.mkdir(parents=True, exist_ok=True)
        log_file = self._app_log_dir / "linuxav.log"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"{timestamp} - {level} - {message}\n"

        try:
            with open(log_file, "a") as f:
                f.write(log_line)
        except Exception as e:
            self.logger.error(f"Cannot write to log: {e}")

    def read_app_log(self, lines: int = 100) -> list[str]:
        """Read application log."""
        log_file = self._app_log_dir / "linuxav.log"

        if not log_file.exists():
            return []

        try:
            content = log_file.read_text()
            all_lines = content.split("\n")
            return all_lines[-lines:] if lines else all_lines
        except Exception as e:
            self.logger.error(f"Cannot read app log: {e}")
            return []
