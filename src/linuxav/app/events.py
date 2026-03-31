import logging
from typing import Callable, Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from collections import defaultdict


logger = logging.getLogger("linuxav.events")


class EventType(Enum):
    SCAN_STARTED = "scan_started"
    SCAN_PROGRESS = "scan_progress"
    SCAN_THREAT_DETECTED = "scan_threat_detected"
    SCAN_COMPLETED = "scan_completed"
    SCAN_CANCELLED = "scan_cancelled"
    SCAN_ERROR = "scan_error"
    UPDATE_STARTED = "update_started"
    UPDATE_PROGRESS = "update_progress"
    UPDATE_COMPLETED = "update_completed"
    UPDATE_CANCELLED = "update_cancelled"
    UPDATE_ERROR = "update_error"

    @classmethod
    def from_string(cls, value: str) -> "EventType":
        """Convert string to EventType enum."""
        try:
            return cls(value)
        except ValueError:
            for member in cls:
                if member.value == value:
                    return member
            raise ValueError(f"Unknown event type: {value}")


EventTypeLike = Union[EventType, str]


@dataclass
class ScanProgressEvent:
    current_file: str
    files_scanned: int
    threats_found: int
    timestamp: datetime


@dataclass
class ThreatDetectedEvent:
    file_path: str
    threat_name: str
    timestamp: datetime


@dataclass
class ScanCompletedEvent:
    path: str
    status: str
    scanned_files: int
    threats_found: int
    threat_name: Optional[str]
    error: Optional[str]
    timestamp: datetime


@dataclass
class ScanErrorEvent:
    error: str
    timestamp: datetime


class EventBus:
    """Pub/sub event system for the application.
    
    Thread-safe event bus with typed events.
    Supports both EventType enum and string for backward compatibility.
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._logger = logger

    def _normalize_event_type(self, event_type: EventTypeLike) -> EventType:
        """Normalize string to EventType enum."""
        if isinstance(event_type, EventType):
            return event_type
        if isinstance(event_type, str):
            return EventType.from_string(event_type)
        raise TypeError(f"EventType must be EventType or str, got {type(event_type)}")

    def subscribe(self, event_type: EventTypeLike, callback: Callable) -> None:
        """Subscribe to an event."""
        normalized = self._normalize_event_type(event_type)
        self._subscribers[normalized].append(callback)
        self._logger.debug(f"Subscribed to {normalized.value}")

    def unsubscribe(self, event_type: EventTypeLike, callback: Callable) -> None:
        """Unsubscribe from an event."""
        normalized = self._normalize_event_type(event_type)
        if callback in self._subscribers[normalized]:
            self._subscribers[normalized].remove(callback)
            self._logger.debug(f"Unsubscribed from {normalized.value}")

    def publish(self, event_type: EventTypeLike, data: Any = None) -> None:
        """Publish an event."""
        normalized = self._normalize_event_type(event_type)
        self._logger.debug(f"Publishing {normalized.value}")
        
        for callback in self._subscribers[normalized]:
            try:
                callback(data)
            except Exception as e:
                self._logger.error(f"Error in callback {callback}: {e}")

    def subscribe_any(self, callback: Callable[[EventType, Any], None]) -> None:
        """Subscribe to all events."""
        for event_type in EventType:
            self._subscribers[event_type].append(callback)

    def clear_subscribers(self, event_type: Optional[EventTypeLike] = None) -> None:
        """Clear subscribers."""
        if event_type:
            normalized = self._normalize_event_type(event_type)
            self._subscribers[normalized].clear()
        else:
            self._subscribers.clear()

    def get_subscribers(self, event_type: EventTypeLike) -> List[Callable]:
        """Get subscribers for an event."""
        normalized = self._normalize_event_type(event_type)
        return self._subscribers.get(normalized, [])
