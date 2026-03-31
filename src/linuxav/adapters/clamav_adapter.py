import subprocess
import logging
import re
import signal
from typing import Optional, Callable
from dataclasses import dataclass, field

from linuxav.domain.models import ScanConfig
from linuxav.domain.enums import ScanStatus


@dataclass
class ScanProgress:
    current_file: str = ""
    files_scanned: int = 0
    threats_found: int = 0


@dataclass
class ScanResponse:
    status: ScanStatus
    scanned_files: int = 0
    threats_found: int = 0
    threats: list[tuple[str, str]] = field(default_factory=list)
    output: str = ""
    error: Optional[str] = None


class ClamAVAdapter:
    """Adapter for ClamAV scanning engine.
    
    Provides abstraction layer for ClamAV commands, allowing
    future replacement of the scanning engine.
    """

    DEFAULT_EXCLUDE_DIRS = ("/proc", "/sys", "/dev", "/run", "/snap")

    def __init__(self, clamav_path: Optional[str] = None):
        self.logger = logging.getLogger("linuxav.clamav_adapter")
        self._clamav_path = clamav_path or self._find_clamscan()
        self._freshclam_path = self._find_freshclam()
        self._current_process: Optional[subprocess.Popen] = None
        self._should_stop = False
        self.logger.info(f"ClamAV path: {self._clamav_path}")

    def _find_clamscan(self) -> str:
        paths = [
            "/usr/bin/clamscan",
            "/usr/local/bin/clamscan",
            "/bin/clamscan",
        ]
        for path in paths:
            if subprocess.run(["which", path], capture_output=True).returncode == 0:
                return path
        return "clamscan"

    def _find_freshclam(self) -> str:
        paths = [
            "/usr/bin/freshclam",
            "/usr/local/bin/freshclam",
            "/bin/freshclam",
        ]
        for path in paths:
            if subprocess.run(["which", path], capture_output=True).returncode == 0:
                return path
        return "freshclam"

    def build_scan_command(self, config: ScanConfig) -> list[str]:
        """Build clamscan command from ScanConfig."""
        args = [self._clamav_path]

        if config.recursive:
            args.append("-r")

        if config.verbose:
            args.append("--verbose")

        args.append("--infected")

        if config.remove:
            args.append("--remove=yes")

        if config.detect_pua:
            args.append("--detect-pua=yes")

        for exclude_dir in config.exclude_dirs or self.DEFAULT_EXCLUDE_DIRS:
            args.extend(["--exclude-dir", exclude_dir])

        if config.log_path:
            args.extend(["--log", config.log_path])

        args.append(config.path)

        self.logger.debug(f"Command: {' '.join(args)}")
        return args

    def stop_scan(self) -> None:
        """Stop the current scan by killing the process."""
        self._should_stop = True
        if self._current_process and self._current_process.poll() is None:
            try:
                self._current_process.terminate()
                try:
                    self._current_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._current_process.kill()
                    self._current_process.wait()
                self.logger.info("Scan process terminated")
            except Exception as e:
                self.logger.warning(f"Error terminating scan: {e}")

    def scan(
        self,
        config: ScanConfig,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None,
    ) -> ScanResponse:
        """Execute scan with real-time progress."""
        self.logger.info(f"Starting scan: {config.path}")
        self._should_stop = False

        cmd = self.build_scan_command(config)
        progress = ScanProgress()
        output_lines = []

        process: Optional[subprocess.Popen] = None
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._current_process = process

            for line in iter(process.stdout.readline, ""):
                if self._should_stop:
                    self.logger.info("Scan stop requested by user")
                    process.terminate()
                    return ScanResponse(
                        status=ScanStatus.ERROR,
                        error="Scan cancelled by user",
                        output="\n".join(output_lines),
                    )

                if not line:
                    break

                output_lines.append(line.rstrip())
                self._parse_line(line, progress, progress_callback)

            process.wait()
            self._current_process = None
            return self._build_response(progress, output_lines, process.returncode)

        except subprocess.TimeoutExpired:
            self.logger.error("Scan timeout")
            if process:
                process.kill()
            return ScanResponse(
                status=ScanStatus.ERROR,
                error="Scan timeout exceeded",
            )
        except FileNotFoundError:
            self.logger.error("ClamAV not found")
            return ScanResponse(
                status=ScanStatus.ERROR,
                error="ClamAV not found in system",
            )
        except Exception as e:
            self.logger.exception(f"Scan error: {e}")
            if process:
                process.kill()
            return ScanResponse(
                status=ScanStatus.ERROR,
                error=str(e),
            )
        finally:
            self._current_process = None

    def scan_directory(
        self,
        path: str,
        recursive: bool = True,
        remove: bool = False,
        detect_pua: bool = True,
        log_path: Optional[str] = None,
    ) -> ScanResponse:
        """Convenience method for simple directory scan."""
        config = ScanConfig(
            path=path,
            recursive=recursive,
            remove=remove,
            detect_pua=detect_pua,
            exclude_dirs=self.DEFAULT_EXCLUDE_DIRS,
            log_path=log_path,
        )
        return self.scan(config)

    def update_database(self, timeout: int = 600) -> dict:
        """Update ClamAV database using freshclam."""
        self.logger.info("Updating database...")

        try:
            result = subprocess.run(
                [self._freshclam_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            success = result.returncode == 0
            output = result.stdout + result.stderr

            if success:
                self.logger.info("Database updated successfully")
            else:
                self.logger.warning(f"Update returned code {result.returncode}")

            return {
                "success": success,
                "output": output,
            }

        except subprocess.TimeoutExpired:
            self.logger.error("Database update timeout")
            return {"success": False, "output": "Update timeout"}
        except Exception as e:
            self.logger.exception(f"Update error: {e}")
            return {"success": False, "output": str(e)}

    def get_version(self) -> str:
        """Get ClamAV version."""
        try:
            result = subprocess.run(
                [self._clamav_path, "--version"],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip().split("\n")[0]
        except Exception as e:
            return f"Unknown: {e}"

    def is_available(self) -> bool:
        """Check if ClamAV is installed."""
        try:
            result = subprocess.run(
                ["which", self._clamav_path],
                capture_output=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _parse_line(
        self,
        line: str,
        progress: ScanProgress,
        callback: Optional[Callable[[ScanProgress], None]],
    ):
        """Parse single output line and update progress."""
        line = line.strip()

        if "FOUND" in line:
            progress.threats_found += 1
            if callback:
                callback(progress)

        elif re.search(r"/(\S+)$", line):
            if any(
                x in line.lower()
                for x in ["scanning", "file", "directory"]
            ):
                progress.files_scanned += 1
                if callback and progress.files_scanned % 10 == 0:
                    callback(progress)

    def _build_response(
        self,
        progress: ScanProgress,
        output_lines: list[str],
        returncode: int,
    ) -> ScanResponse:
        """Build ScanResponse from scan results."""
        output = "\n".join(output_lines)

        if returncode == 0:
            status = ScanStatus.CLEAN
        elif returncode == 1:
            status = ScanStatus.INFECTED
        else:
            status = ScanStatus.ERROR

        threats = self._parse_threats(output)

        return ScanResponse(
            status=status,
            scanned_files=progress.files_scanned,
            threats_found=progress.threats_found,
            threats=threats,
            output=output,
        )

    def _parse_threats(self, output: str) -> list[tuple[str, str]]:
        """Parse threats from output."""
        threats = []
        for line in output.split("\n"):
            if "FOUND" in line:
                parts = line.split("FOUND", 1)
                if len(parts) == 2:
                    file_path = parts[0].strip()
                    threat_name = parts[1].strip()
                    threats.append((file_path, threat_name))
        return threats
