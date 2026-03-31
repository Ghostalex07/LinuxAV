# LinuxAV Architecture

## Overview

LinuxAV is a production-quality antivirus application for Linux that follows clean architecture principles. The codebase is modular, typed, and thread-safe.

## Layer Structure

### 1. Domain Layer (`src/linuxav/domain/`)

Contains business entities and rules:

- **models.py**: Core data structures (`ScanResult`, `ScanConfig`, `ThreatInfo`)
- **enums.py**: Type definitions (`ScanStatus`, `ThreatSeverity`)
- **validators.py**: Path validation (blocks dangerous paths like `/proc`, `/sys`, `/dev`)

### 2. Adapter Layer (`src/linuxav/adapters/`)

External tool integrations:

- **clamav_adapter.py**: Abstracts all ClamAV CLI commands
  - Builds scan commands from config
  - Parses real-time output
  - Provides progress callbacks
  - Supports cancellation via `stop_scan()`

- **system_adapter.py**: System information (disk usage, memory, notifications)

### 3. Service Layer (`src/linuxav/services/`)

Business logic (UI-agnostic):

- **scan_service.py**: Scan orchestration
  - Validates paths
  - Runs scans in background threads
  - Emits progress events
  - Supports cancellation

- **update_service.py**: Database updates
  - Manages clamav-freshclam service
  - Falls back to alternative mirrors
  - Real-time progress output
  - Cancellation support

- **log_service.py**: Log parsing and management

- **monitor_service.py**: Filesystem monitoring with inotify

### 4. Application Layer (`src/linuxav/app/`)

Orchestration and state:

- **controller.py**: Middleware between UI and services
  - Coordinates all services
  - Manages state
  - Publishes events

- **state.py**: Thread-safe state management
  - Uses locks for thread safety
  - Maintains scan history

- **events.py**: Event pub/sub system
  - Typed event bus with `EventType` enum
  - Supports both string and enum event types
  - Thread-safe subscriber management

### 5. UI Layer (`src/linuxav/ui/`)

Presentation only (no business logic):

- **window.py**: Main application window
- **widgets/**: Reusable UI components
  - `scan_controls.py`: Scan buttons
  - `output_console.py`: Log display
  - `progress_bar.py`: Progress indicator
  - `status_bar.py`: Status display
- **styles/**: Theme configuration
  - `theme.py`: Color palette, fonts, dimensions
  - `__init__.py`: Theme application

## Thread Safety

- All services use background threads for long-running operations
- `StateManager` uses `threading.RLock` for thread-safe access
- `EventBus` is thread-safe for publish/subscribe
- UI updates use `root.after()` to run on main thread

## Event System

Events flow from services → controller → UI:

```
ClamAVAdapter.scan() → ScanService._on_progress() 
    → controller._on_scan_progress() 
    → event_bus.publish(SCAN_PROGRESS, data) 
    → window._on_scan_progress() → UI update
```

## Extension Points

- **Replace ClamAV**: Create new adapter implementing same interface
- **Add VirusTotal**: Add new integration in `integrations/`
- **Add scan types**: Extend `ScanType` enum and service

## Key Design Decisions

1. **No UI logic in services**: Services only emit events; UI decides how to display
2. **Typed throughout**: Full type hints for maintainability
3. **Cancellation**: Both scan and update support cancellation
4. **Progress real-time**: UI shows file-by-file progress
5. **Mirror fallback**: Updates try alternative mirrors if defaults fail
