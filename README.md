# LinuxAV

A professional antivirus application for Linux with a modern GUI, powered by ClamAV.

## Features

- **Full System Scan**: Scan the entire filesystem (/) 
- **Directory Scan**: Select specific folders to scan
- **Real-time Progress**: Live progress display with file count and threat detection
- **Database Updates**: Update ClamAV virus definitions with automatic mirror fallback
- **Cancel Support**: Cancel ongoing scans and updates at any time
- **Dark Theme**: Modern dark UI built with Tkinter
- **Thread-safe**: All operations run in background threads to keep UI responsive
- **Event-driven Architecture**: Clean separation between UI and business logic

## Requirements

- Python 3.8+
- ClamAV (clamscan/freshclam)
- Linux operating system

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/LinuxAV.git
cd LinuxAV
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure ClamAV is installed:
```bash
# Debian/Ubuntu
sudo apt-get install clamav clamav-freshclam

# Fedora
sudo dnf install clamav clamav-update

# Arch Linux
sudo pacman -S clamav
```

## Usage

Start the application:
```bash
cd src
python -m linuxav.main
```

Or from the project root:
```bash
PYTHONPATH=src python -m linuxav.main
```

### Command Line Options

- `-v, --verbose`: Enable verbose logging

### GUI Controls

- **Full Scan (/)**: Scan the entire root filesystem
- **Scan Folder**: Select a specific directory to scan
- **Update DB**: Update ClamAV virus definitions
- **Cancel**: Stop ongoing scan or update

## Architecture

LinuxAV follows clean architecture principles:

```
src/linuxav/
├── domain/          # Business entities (models, enums, validators)
├── adapters/        # External integrations (ClamAV adapter)
├── services/        # Business logic (scan, update, log, monitor)
├── app/             # Application layer (controller, state, events)
└── ui/              # Presentation layer (window, widgets, styles)
```

### Key Components

- **ClamAVAdapter**: Abstracts all ClamAV command execution
- **ScanService**: Manages scan operations with progress callbacks
- **UpdateService**: Handles database updates with mirror fallback
- **Controller**: Coordinates between UI and services
- **EventBus**: Thread-safe pub/sub event system

## Development

Run tests:
```bash
PYTHONPATH=src python -m pytest tests/unit/ -v
```

## License

MIT License - see LICENSE file for details.

## Screenshots

The application features a modern dark theme with:
- Real-time scan progress
- Console output for detailed information
- Status bar showing ClamAV version and scan status
- Threat detection alerts
