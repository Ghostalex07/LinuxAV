# LinuxAV Usage Guide

## Getting Started

### Running the Application

```bash
cd LinuxAV/src
python -m linuxav.main
```

Or with PYTHONPATH set:
```bash
PYTHONPATH=src python -m linuxav.main
```

### GUI Overview

The main window consists of:

1. **Title Bar**: "LinuxAV - Antivirus"
2. **Status Bar**: Shows current status and ClamAV version
3. **Control Buttons**:
   - Full Scan (/) - Scan entire filesystem
   - Scan Folder - Select specific directory
   - Update DB - Update virus definitions
   - Cancel - Stop ongoing operation
4. **Progress Bar**: Shows scan/update progress
5. **Console**: Real-time output log

## Scanning Files

### Full System Scan

Click "Full Scan (/)" to scan the entire root filesystem (/)
- Automatically excludes /proc, /sys, /dev, /run, /snap
- Scans all files recursively
- Shows progress in real-time
- Displays threats when found

### Directory Scan

Click "Scan Folder" to select a specific directory
- File picker opens for directory selection
- Only the selected directory is scanned
- Useful for quick scans of specific areas

### Scan Results

- **Clean**: Green "Limpio" status, "X files scanned, clean" message
- **Infected**: Red "INFECTADO - N threats" status, alert dialog
- **Error**: Error message displayed in console

## Database Updates

### Automatic Updates

Click "Update DB" to download latest ClamAV definitions:
1. Stops clamav-freshclam service (if running)
2. Downloads new database via freshclam
3. Restarts the service
4. Shows real-time progress

### Mirror Fallback

If default ClamAV mirrors fail, the system automatically tries:
- https://database.clamav.net/main.cvd
- https://db.local.clamav.net/main.cvd
- https://clamdb.lemani.it/main.cvd

### Update Status

- Success: "Database updated successfully"
- Already up-to-date: "Database already up to date"  
- Failure: Error message with details

## Cancellation

### Canceling a Scan

Click "Cancel" during a scan to:
1. Terminate the clamscan subprocess immediately
2. Return UI to idle state
3. Log cancellation message

### Canceling an Update

Click "Cancel" during database update to:
1. Kill the freshclam process
2. Restart clamav-freshclam service
3. Show cancellation message

## Command Line Options

```bash
python -m linuxav.main -v    # Verbose logging
python -m linuxav.main --verbose  # Same as above
```

## Troubleshooting

### ClamAV Not Found

If ClamAV is not installed:
```
sudo apt-get install clamav clamav-freshclam  # Debian/Ubuntu
sudo dnf install clamav clamav-update         # Fedora
sudo pacman -S clamav                        # Arch Linux
```

### Permission Denied

Some directories require root access to scan:
```bash
sudo python -m linuxav.main  # Run as root (not recommended)
```

### Network Errors

If database update fails:
- Check internet connection
- Try again later
- Mirrors may be temporarily unavailable

## Log Files

Application logs are stored in:
- `logs/linuxav.log` - Main application log
- `/var/log/clamav/clamav.log` - ClamAV scan log (may require sudo)
