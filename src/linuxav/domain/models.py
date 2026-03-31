from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from linuxav.domain.enums import ScanStatus, ThreatSeverity


@dataclass
class ThreatInfo:
    file_path: str
    threat_name: str
    severity: ThreatSeverity
    detected_at: datetime


@dataclass
class ScanResult:
    path: str
    status: ScanStatus
    threat_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    scanned_files: int = 0
    threats_found: int = 0
    error_message: Optional[str] = None

    def is_clean(self) -> bool:
        return self.status == ScanStatus.CLEAN

    def is_infected(self) -> bool:
        return self.status == ScanStatus.INFECTED

    def has_error(self) -> bool:
        return self.status == ScanStatus.ERROR


@dataclass
class ScanConfig:
    path: str
    recursive: bool = True
    remove: bool = False
    detect_pua: bool = True
    exclude_dirs: tuple = ("/proc", "/sys", "/dev")
    log_path: Optional[str] = None
    verbose: bool = True

    def to_clamav_args(self) -> list[str]:
        args = ["clamscan"]

        if self.recursive:
            args.append("-r")

        if self.verbose:
            args.append("--verbose")

        args.extend(["--infected"])

        if self.remove:
            args.append("--remove=yes")

        if self.detect_pua:
            args.append("--detect-pua=yes")

        for excl in self.exclude_dirs:
            args.extend(["--exclude-dir", excl])

        if self.log_path:
            args.extend(["--log", self.log_path])

        args.append(self.path)

        return args
