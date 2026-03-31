"""
LinuxAV Database Update Service.

Handles ClamAV database updates with:
- Password-based sudo for GUI password prompt
- Safe service stop/restart with timeout
- Alternative mirror fallback on network errors
- Real-time progress reporting
- Thread-safe cancellation
- Comprehensive logging
"""

import logging
import subprocess
import threading
import time
from typing import Optional, Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UpdateProgress:
    """Progress event for database update."""
    phase: str  # "stopping_service", "updating", "starting_service", "complete", "error"
    message: str
    percent: float = 0.0
    output_line: Optional[str] = None


@dataclass
class UpdateResult:
    """Result of database update operation."""
    success: bool
    message: str
    output: str = ""
    error: Optional[str] = None
    mirror_used: Optional[str] = None


class PasswordPromptRequired(Exception):
    """Raised when password is required but not provided."""
    pass


class UpdateService:
    """Service for updating ClamAV database.
    
    Features:
    - Safe service management with timeout
    - Single sudo session for all commands
    - Alternative mirror fallback
    - Real-time progress callbacks
    - Thread-safe cancellation
    - Comprehensive logging
    """

    # Official and alternative ClamAV mirrors
    DEFAULT_MIRRORS = [
        "https://database.clamav.net/main.cvd",
    ]
    
    ALTERNATIVE_MIRRORS = [
        "https://db.local.clamav.net/main.cvd",
        "https://clamdb.lemani.it/main.cvd",
        "https://edge.clamav.net/main.cvd",
    ]

    # Service name
    SERVICE_NAME = "clamav-freshclam"

    # Timeouts
    SERVICE_STOP_TIMEOUT = 15
    FRESHCLAM_TIMEOUT = 600
    WGET_TIMEOUT = 300

    def __init__(self):
        self.logger = logging.getLogger("linuxav.update_service")
        self._is_updating = False
        self._should_stop = False
        self._update_process: Optional[subprocess.Popen] = None
        self._update_thread: Optional[threading.Thread] = None
        self._progress_callbacks: list[Callable[[UpdateProgress], None]] = []
        self._output_lines: list[str] = []
        self._lock = threading.Lock()
        self._on_complete_callback: Optional[Callable[[UpdateResult], None]] = None
        self._sudo_password: Optional[str] = None

    @property
    def is_updating(self) -> bool:
        with self._lock:
            return self._is_updating

    def add_progress_callback(self, callback: Callable[[UpdateProgress], None]) -> None:
        """Add callback for progress updates."""
        self._progress_callbacks.append(callback)

    def remove_progress_callback(self, callback: Callable[[UpdateProgress], None]) -> None:
        """Remove progress callback."""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)

    def set_complete_callback(self, callback: Callable[[UpdateResult], None]) -> None:
        """Set callback for completion."""
        self._on_complete_callback = callback

    def set_password(self, password: str) -> None:
        """Store sudo password for this update session."""
        self._sudo_password = password
        self.logger.debug("Password set for update session")

    def clear_password(self) -> None:
        """Clear stored password from memory."""
        self._sudo_password = None
        self.logger.debug("Password cleared from session")

    def has_password(self) -> bool:
        """Check if password is available."""
        return self._sudo_password is not None

    def _run_sudo_command(self, args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run command with sudo using password from stdin."""
        if not self._sudo_password:
            raise PasswordPromptRequired("Sudo password required")

        cmd = ["sudo", "-S", "-k"] + args
        self.logger.debug(f"Running sudo command: {args[0]}")

        try:
            result = subprocess.run(
                cmd,
                input=self._sudo_password + "\n",
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Sudo command timed out after {timeout}s: {args[0]}")
            raise

    def cancel(self) -> bool:
        """Cancel ongoing update. Returns True if cancel was attempted."""
        if not self.is_updating:
            return False

        self.logger.info("Cancel requested by user")
        self._should_stop = True

        if self._update_process and self._update_process.poll() is None:
            try:
                self.logger.info("Terminating update process")
                self._update_process.terminate()
                try:
                    self._update_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Process did not terminate, forcing kill")
                    self._update_process.kill()
                    self._update_process.wait()
            except Exception as e:
                self.logger.warning(f"Error killing process: {e}")

        self.logger.info("Restarting service after cancellation")
        self._restart_service()
        self.clear_password()

        return True

    def update(self, timeout: int = FRESHCLAM_TIMEOUT) -> UpdateResult:
        """Update ClamAV database synchronously."""
        if self.is_updating:
            return UpdateResult(False, "Update already in progress")

        if not self._sudo_password:
            return UpdateResult(False, "Sudo password required", error="password_required")

        with self._lock:
            self._is_updating = True
        self._should_stop = False
        self._output_lines = []

        self.logger.info("Starting database update process")
        self._emit_progress("initializing", "Initializing database update...", 0.0)

        try:
            if self._should_stop:
                return self._create_cancelled_result()

            # Phase 1: Stop the clamav-freshclam service safely
            self._emit_progress("stopping_service", "Stopping clamav-freshclam service...", 5.0)
            self.logger.info("Phase 1: Stopping clamav-freshclam service")
            
            service_stopped = self._stop_service_safe()
            if not service_stopped:
                self.logger.warning("Service stop failed or timed out, trying process kill")
                self._kill_freshclam_processes()

            if self._should_stop:
                self._restart_service()
                return self._create_cancelled_result()

            # Phase 2: Run freshclam with default mirrors
            self._emit_progress("updating", "Running freshclam update...", 20.0)
            self.logger.info("Phase 2: Running freshclam with default mirrors")
            
            update_result = self._run_freshclam(timeout)
            
            if self._should_stop:
                self._restart_service()
                return self._create_cancelled_result()

            # Phase 3: If network error, try alternative mirrors
            if not update_result.success and self._is_network_error(update_result.message):
                self.logger.warning("Network error detected, trying alternative mirrors")
                self._emit_progress("mirrors", "Trying alternative mirrors...", 50.0)
                update_result = self._try_alternative_mirrors(timeout)

            # Phase 4: Always restart the service
            self._emit_progress("starting_service", "Restarting clamav-freshclam service...", 95.0)
            self.logger.info("Phase 4: Restarting clamav-freshclam service")
            self._restart_service()

            # Final status
            if update_result.success:
                self._emit_progress("complete", "Database updated successfully", 100.0)
                self.logger.info(f"Database update completed successfully: {update_result.message}")
            else:
                self._emit_progress("error", f"Update failed: {update_result.message}", 0.0)
                self.logger.error(f"Database update failed: {update_result.message}")

            return update_result

        except Exception as e:
            self.logger.exception(f"Unexpected error during update: {e}")
            error_result = UpdateResult(False, str(e), error=str(e))
            self._emit_progress("error", f"Error: {e}", 0.0)
            
            # Ensure service is restarted on error
            try:
                self._restart_service()
            except Exception:
                pass
                
            return error_result
        finally:
            with self._lock:
                self._is_updating = False
            self.clear_password()

    def update_async(self, timeout: int = FRESHCLAM_TIMEOUT) -> bool:
        """Start update in background thread."""
        if self.is_updating:
            self.logger.warning("Update already in progress")
            return False

        self.logger.info("Starting async database update")
        self._update_thread = threading.Thread(
            target=self._async_worker,
            args=(timeout,),
            daemon=True,
        )
        self._update_thread.start()
        return True

    def _async_worker(self, timeout: int) -> None:
        result = self.update(timeout)
        if self._on_complete_callback:
            try:
                self._on_complete_callback(result)
            except Exception as e:
                self.logger.error(f"Complete callback error: {e}")

    def _is_network_error(self, message: str) -> bool:
        """Check if error message indicates network problem."""
        message_lower = message.lower()
        network_keywords = ["network", "mirror", "connection", "timeout", "resolve", "could not resolve", 
                          "failed", "cannot", "unable"]
        return any(keyword in message_lower for keyword in network_keywords)

    def _stop_service_safe(self) -> bool:
        """Stop the clamav-freshclam service with timeout."""
        self.logger.info(f"Stopping {self.SERVICE_NAME} service with {self.SERVICE_STOP_TIMEOUT}s timeout")
        
        try:
            result = self._run_sudo_command(
                ["systemctl", "stop", self.SERVICE_NAME],
                timeout=self.SERVICE_STOP_TIMEOUT,
            )
            
            if result.returncode == 0:
                self.logger.info(f"{self.SERVICE_NAME} service stopped successfully")
                time.sleep(1)
                return True
            else:
                self.logger.warning(f"Could not stop service: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Service stop timed out after {self.SERVICE_STOP_TIMEOUT}s")
            return False
        except FileNotFoundError:
            self.logger.warning("systemctl not found, trying alternative method")
            return False
        except PasswordPromptRequired:
            raise
        except Exception as e:
            self.logger.warning(f"Error stopping service: {e}")
            return False

    def _kill_freshclam_processes(self) -> None:
        """Kill any remaining freshclam processes."""
        self.logger.info("Killing remaining freshclam processes")
        
        methods = [
            ["pkill", "-15", "freshclam"],  # SIGTERM first
            ["pkill", "-9", "freshclam"],     # SIGKILL as fallback
        ]
        
        for cmd in methods:
            try:
                self._run_sudo_command(cmd, timeout=10)
                time.sleep(0.5)
            except Exception as e:
                self.logger.debug(f"Process kill method failed: {e}")
        
        time.sleep(1)
        self.logger.info("Freshclam processes killed")

    def _restart_service(self) -> None:
        """Restart the clamav-freshclam service."""
        self.logger.info(f"Restarting {self.SERVICE_NAME} service")
        
        try:
            result = self._run_sudo_command(
                ["systemctl", "start", self.SERVICE_NAME],
                timeout=30,
            )
            
            if result.returncode == 0:
                self.logger.info(f"{self.SERVICE_NAME} service restarted successfully")
            else:
                self.logger.warning(f"Service restart returned: {result.stderr}")
                
        except Exception as e:
            self.logger.warning(f"Could not restart service: {e}")

    def _run_freshclam(self, timeout: int) -> UpdateResult:
        """Run freshclam with default mirrors."""
        self._output_lines = []

        if not self._sudo_password:
            return UpdateResult(False, "Sudo password required", error="password_required")

        try:
            freshclam_path = self._find_freshclam()
            if not freshclam_path:
                return UpdateResult(False, "freshclam not found in system")

            self.logger.info(f"Running freshclam from {freshclam_path}")
            self._emit_progress("updating", "Running freshclam update...", 25.0)

            cmd = ["sudo", "-S", "-k", freshclam_path, "-v", "--quiet"]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._update_process = process

            # Send password to stdin
            process.stdin.write(self._sudo_password + "\n")
            process.stdin.flush()
            process.stdin.close()

            # Read output line by line
            while True:
                if self._should_stop:
                    process.terminate()
                    return self._create_cancelled_result()

                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    continue
                
                line = line.rstrip()
                self._output_lines.append(line)
                
                if any(keyword in line.lower() for keyword in ["downloading", "testing", "byte", "kb", "mb", "gb", "progress"]):
                    self._emit_progress("updating", line, output_line=line)

            process.wait()
            returncode = process.returncode
            self._update_process = None

            output = "\n".join(self._output_lines)

            if returncode == 0:
                self.logger.info("Freshclam completed successfully - database updated")
                return UpdateResult(True, "Database updated successfully", output)
            elif returncode == 1:
                self.logger.info("Database already up to date")
                return UpdateResult(True, "Database already up to date", output)
            elif returncode == 2:
                self.logger.error("Network error or mirror problem")
                return UpdateResult(False, "Network error or mirror problem (code 2)", output)
            elif returncode == 3:
                self.logger.error("Database file error")
                return UpdateResult(False, "Database file error (code 3)", output)
            else:
                self.logger.error(f"Freshclam exited with code {returncode}")
                return UpdateResult(False, f"Freshclam exited with code {returncode}", output)

        except subprocess.TimeoutExpired:
            self.logger.error("Freshclam timeout")
            if self._update_process:
                self._update_process.kill()
            return UpdateResult(False, "Freshclam timeout exceeded", "\n".join(self._output_lines))
        except FileNotFoundError:
            self.logger.error("freshclam not found")
            return UpdateResult(False, "freshclam not found in system")
        except Exception as e:
            self.logger.exception(f"Freshclam error: {e}")
            return UpdateResult(False, str(e), error=str(e))
        finally:
            self._update_process = None

    def _try_alternative_mirrors(self, timeout: int) -> UpdateResult:
        """Try downloading from alternative mirrors."""
        self.logger.info("Trying alternative mirrors...")
        self._emit_progress("mirrors", "Trying alternative mirrors...", 50.0)

        if not self._sudo_password:
            return UpdateResult(False, "Sudo password required", error="password_required")

        clamav_dir = Path("/var/lib/clamav")
        if not clamav_dir.exists():
            return UpdateResult(False, "Cannot access /var/lib/clamav directory")

        all_mirrors = self.DEFAULT_MIRRORS + self.ALTERNATIVE_MIRRORS
        
        for i, mirror in enumerate(all_mirrors):
            if self._should_stop:
                return self._create_cancelled_result()

            percent = 55.0 + (i * 10)
            mirror_name = mirror.split("/")[-1]
            self.logger.info(f"Trying mirror {i+1}/{len(all_mirrors)}: {mirror_name}")
            self._emit_progress("mirrors", f"Trying {mirror_name}...", percent)

            try:
                cmd = ["sudo", "-S", "-k", "wget", "-q", "-O", str(clamav_dir / "main.cvd"), mirror]
                
                result = subprocess.run(
                    cmd,
                    input=self._sudo_password + "\n",
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                if result.returncode == 0:
                    cvd_file = clamav_dir / "main.cvd"
                    if cvd_file.exists():
                        file_size = cvd_file.stat().st_size
                        if file_size > 1000000:  # At least 1MB
                            self.logger.info(f"Successfully downloaded {mirror_name} ({file_size} bytes)")
                            self._emit_progress("complete", f"Downloaded from {mirror_name}", 100.0)
                            return UpdateResult(
                                True, 
                                f"Database updated from {mirror_name}", 
                                f"Downloaded {file_size} bytes",
                                mirror_used=mirror_name
                            )
                        else:
                            self.logger.warning(f"Downloaded file too small: {file_size}")
                else:
                    self.logger.warning(f"wget failed for {mirror_name}: {result.stderr}")

            except subprocess.TimeoutExpired:
                self.logger.warning(f"Timeout downloading from {mirror_name}")
            except Exception as e:
                self.logger.warning(f"Mirror {mirror_name} failed: {e}")
                continue

        return UpdateResult(False, "All mirrors failed")

    def _find_freshclam(self) -> str:
        """Find freshclam binary."""
        paths = ["/usr/bin/freshclam", "/usr/local/bin/freshclam", "/bin/freshclam"]
        for path in paths:
            if Path(path).exists():
                return path
        
        try:
            result = subprocess.run(["which", "freshclam"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        
        return "freshclam"

    def _emit_progress(self, phase: str, message: str, percent: float = 0.0, 
                      output_line: Optional[str] = None) -> None:
        """Emit progress event to all callbacks."""
        progress = UpdateProgress(
            phase=phase, 
            message=message, 
            percent=percent, 
            output_line=output_line
        )
        for callback in self._progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                self.logger.error(f"Progress callback error: {e}")

    def _create_cancelled_result(self) -> UpdateResult:
        """Create cancelled result."""
        self.logger.info("Update cancelled by user")
        return UpdateResult(False, "Update cancelled by user", error="cancelled")

    def get_output(self) -> list[str]:
        """Get accumulated output lines."""
        return self._output_lines.copy()
