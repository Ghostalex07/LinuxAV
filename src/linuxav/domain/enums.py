from enum import Enum


class ScanStatus(Enum):
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"
    SCANNING = "scanning"


class ThreatSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
