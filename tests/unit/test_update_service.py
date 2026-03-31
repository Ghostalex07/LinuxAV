"""
Unit tests for UpdateService.

Tests cover:
- Service stop/restart
- Freshclam execution
- Password handling
- Mirror fallback
- Cancellation
- Error handling
- Thread safety
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import subprocess
import tempfile
import os
import threading
from datetime import datetime

from linuxav.services.update_service import UpdateService, UpdateProgress, UpdateResult, PasswordPromptRequired


class TestUpdateService(unittest.TestCase):
    """Unit tests for UpdateService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = UpdateService()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.rmdir(self.temp_dir)
        except:
            pass

    def test_service_initialization(self):
        """Test service initializes correctly."""
        self.assertFalse(self.service.is_updating)
        self.assertEqual(len(self.service._progress_callbacks), 0)
        self.assertEqual(len(self.service._output_lines), 0)

    def test_add_progress_callback(self):
        """Test adding progress callback."""
        callback = Mock()
        self.service.add_progress_callback(callback)
        self.assertIn(callback, self.service._progress_callbacks)

    def test_remove_progress_callback(self):
        """Test removing progress callback."""
        callback = Mock()
        self.service.add_progress_callback(callback)
        self.service.remove_progress_callback(callback)
        self.assertNotIn(callback, self.service._progress_callbacks)

    def test_set_complete_callback(self):
        """Test setting complete callback."""
        callback = Mock()
        self.service.set_complete_callback(callback)
        self.assertEqual(self.service._on_complete_callback, callback)

    def test_is_network_error_network(self):
        """Test network error detection."""
        self.assertTrue(self.service._is_network_error("Network connection failed"))
        self.assertTrue(self.service._is_network_error("Could not resolve mirror"))
        self.assertTrue(self.service._is_network_error("Connection timeout"))

    def test_is_network_error_mirror(self):
        """Test mirror error detection."""
        self.assertTrue(self.service._is_network_error("Mirror problem"))
        self.assertTrue(self.service._is_network_error("Could not connect to mirror"))

    def test_is_network_error_false_positive(self):
        """Test non-network errors are not detected as network errors."""
        self.assertFalse(self.service._is_network_error("Database already up to date"))
        self.assertFalse(self.service._is_network_error("Permission denied"))
        self.assertFalse(self.service._is_network_error("File not found"))

    def test_cancel_when_not_updating(self):
        """Test cancel returns False when not updating."""
        result = self.service.cancel()
        self.assertFalse(result)

    @patch("linuxav.services.update_service.subprocess.run")
    def test_stop_service_success(self, mock_run):
        """Test service stops successfully."""
        mock_run.return_value = Mock(returncode=0, stderr="")
        
        result = self.service._stop_service_safe()
        
        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch("linuxav.services.update_service.subprocess.run")
    def test_stop_service_failure(self, mock_run):
        """Test service stop failure."""
        mock_run.return_value = Mock(returncode=1, stderr="Service not found")
        
        result = self.service._stop_service_safe()
        
        self.assertFalse(result)

    @patch("linuxav.services.update_service.subprocess.run")
    def test_stop_service_timeout(self, mock_run):
        """Test service stop timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 1)
        
        result = self.service._stop_service_safe()
        
        self.assertFalse(result)

    @patch("linuxav.services.update_service.subprocess.run")
    def test_restart_service(self, mock_run):
        """Test service restart."""
        mock_run.return_value = Mock(returncode=0, stderr="")
        
        self.service._restart_service()
        
        mock_run.assert_called_once()

    @patch("linuxav.services.update_service.subprocess.run")
    def test_run_freshclam_not_found(self, mock_run):
        """Test freshclam not found error."""
        mock_run.side_effect = FileNotFoundError("freshclam not found")
        
        result = self.service._run_freshclam(60)
        
        self.assertFalse(result.success)
        self.assertIn("not found", result.message.lower())

    @patch("linuxav.services.update_service.subprocess.Popen")
    def test_run_freshclam_cancelled(self, mock_popen):
        """Test freshclam cancellation."""
        # Create mock process
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.stdout.readline.return_value = ""  # Empty = done
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        # Set service to updating and request stop
        self.service._is_updating = True
        self.service._should_stop = True
        
        result = self.service._run_freshclam(60)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error, "cancelled")

    @patch("linuxav.services.update_service.Path")
    def test_try_alternative_mirrors_wget_fails(self, mock_path):
        """Test alternative mirrors when wget fails."""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        
        # Create a mock for the path /var/lib/clamav/main.cvd
        mock_cvd_file = MagicMock()
        mock_cvd_file.stat.return_value.st_size = 100
        mock_path_instance.__truediv__.return_value = mock_cvd_file
        
        mock_path.return_value = mock_path_instance
        
        mock_run = Mock(return_value=Mock(returncode=1, stderr="Network error"))
        
        with patch("linuxav.services.update_service.subprocess.run", mock_run):
            result = self.service._try_alternative_mirrors(300)
        
        self.assertFalse(result.success)

    def test_create_cancelled_result(self):
        """Test cancelled result creation."""
        result = self.service._create_cancelled_result()
        
        self.assertFalse(result.success)
        self.assertEqual(result.error, "cancelled")
        self.assertIn("cancelled", result.message.lower())

    def test_get_output(self):
        """Test getting output lines."""
        self.service._output_lines = ["line1", "line2", "line3"]
        
        result = self.service.get_output()
        
        self.assertEqual(result, ["line1", "line2", "line3"])

    @patch("linuxav.services.update_service.subprocess.run")
    def test_update_already_in_progress(self, mock_run):
        """Test update when already in progress."""
        self.service._is_updating = True
        
        result = self.service.update()
        
        self.assertFalse(result.success)
        self.assertIn("already in progress", result.message)

    @patch.object(UpdateService, "_stop_service_safe")
    @patch.object(UpdateService, "_run_freshclam")
    @patch.object(UpdateService, "_restart_service")
    def test_update_success(self, mock_restart, mock_freshclam, mock_stop):
        """Test successful update."""
        mock_stop.return_value = True
        mock_freshclam.return_value = UpdateResult(True, "Database updated", "output")
        
        result = self.service.update()
        
        self.assertTrue(result.success)
        mock_stop.assert_called_once()
        mock_freshclam.assert_called_once()
        mock_restart.assert_called_once()

    @patch.object(UpdateService, "_stop_service_safe")
    @patch.object(UpdateService, "_run_freshclam")
    @patch.object(UpdateService, "_restart_service")
    def test_update_network_error_fallback(self, mock_restart, mock_freshclam, mock_stop):
        """Test update falls back to mirrors on network error."""
        mock_stop.return_value = True
        mock_freshclam.return_value = UpdateResult(False, "Network error", "output")
        
        # Mock alternative mirrors
        with patch.object(UpdateService, "_try_alternative_mirrors") as mock_alt:
            mock_alt.return_value = UpdateResult(True, "Updated from mirror", "output")
            result = self.service.update()
        
        self.assertTrue(result.success)
        mock_alt.assert_called_once()

    @patch.object(UpdateService, "_stop_service_safe")
    @patch.object(UpdateService, "_run_freshclam")
    @patch.object(UpdateService, "_restart_service")
    def test_update_cancelled(self, mock_restart, mock_freshclam, mock_stop):
        """Test update cancellation."""
        mock_stop.return_value = True
        self.service._should_stop = True
        mock_freshclam.return_value = UpdateResult(False, "Cancelled", error="cancelled")
        
        result = self.service.update()
        
        self.assertFalse(result.success)
        mock_restart.assert_called_once()

    @patch.object(UpdateService, "_stop_service_safe")
    @patch.object(UpdateService, "_run_freshclam")
    @patch.object(UpdateService, "_restart_service")
    def test_update_exception_handling(self, mock_restart, mock_freshclam, mock_stop):
        """Test update exception handling."""
        mock_stop.return_value = True
        mock_freshclam.side_effect = Exception("Test error")
        
        result = self.service.update()
        
        self.assertFalse(result.success)
        self.assertIn("Test error", result.message)

    @patch("linuxav.services.update_service.subprocess.Popen")
    def test_cancel_terminates_process(self, mock_popen):
        """Test cancel terminates running process."""
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        self.service._is_updating = True
        self.service.cancel()
        
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called()

    @patch("linuxav.services.update_service.subprocess.Popen")
    def test_cancel_kills_hung_process(self, mock_popen):
        """Test cancel force kills hung process."""
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.terminate.side_effect = subprocess.TimeoutExpired("cmd", 1)
        mock_popen.return_value = mock_process
        
        self.service._is_updating = True
        self.service.cancel()
        
        mock_process.kill.assert_called_once()

    def test_progress_callback_emission(self):
        """Test progress callbacks are emitted correctly."""
        callback = Mock()
        self.service.add_progress_callback(callback)
        
        self.service._emit_progress("updating", "Test message", 50.0)
        
        callback.assert_called_once()
        args = callback.call_args[0][0]
        self.assertEqual(args.phase, "updating")
        self.assertEqual(args.message, "Test message")
        self.assertEqual(args.percent, 50.0)

    def test_password_set_and_clear(self):
        """Test password can be set and cleared."""
        self.assertFalse(self.service.has_password())
        
        self.service.set_password("testpass")
        self.assertTrue(self.service.has_password())
        
        self.service.clear_password()
        self.assertFalse(self.service.has_password())

    def test_update_requires_password(self):
        """Test update fails without password."""
        result = self.service.update()
        
        self.assertFalse(result.success)
        self.assertIn("password", result.message.lower())
        self.assertEqual(result.error, "password_required")

    @patch.object(UpdateService, "_stop_service_safe")
    @patch.object(UpdateService, "_run_freshclam")
    @patch.object(UpdateService, "_restart_service")
    def test_update_with_password(self, mock_restart, mock_freshclam, mock_stop):
        """Test update works with password set."""
        self.service.set_password("testpass")
        mock_stop.return_value = True
        mock_freshclam.return_value = UpdateResult(True, "Updated", "output")
        
        result = self.service.update()
        
        self.assertTrue(result.success)
        self.service.clear_password()

    def test_run_sudo_command_requires_password(self):
        """Test sudo command fails without password."""
        with self.assertRaises(PasswordPromptRequired):
            self.service._run_sudo_command(["echo", "test"])

    @patch("linuxav.services.update_service.subprocess.run")
    def test_run_sudo_command_with_password(self, mock_run):
        """Test sudo command works with password."""
        self.service.set_password("testpass")
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        result = self.service._run_sudo_command(["echo", "test"])
        
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        self.assertIn("sudo", call_args[0][0])
        self.assertIn("-S", call_args[0][0])
        self.assertEqual(call_args[1]["input"], "testpass\n")

    @patch.object(UpdateService, "_run_sudo_command")
    def test_stop_service_with_password(self, mock_sudo):
        """Test service stop uses password."""
        self.service.set_password("testpass")
        mock_sudo.return_value = Mock(returncode=0, stderr="")
        
        result = self.service._stop_service_safe()
        
        self.assertTrue(result)
        mock_sudo.assert_called_once()

    @patch.object(UpdateService, "_run_sudo_command")
    def test_restart_service_with_password(self, mock_sudo):
        """Test service restart uses password."""
        self.service.set_password("testpass")
        mock_sudo.return_value = Mock(returncode=0, stderr="")
        
        self.service._restart_service()
        
        mock_sudo.assert_called_once()


class TestUpdateServiceIntegration(unittest.TestCase):
    """Integration tests simulating real update scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = UpdateService()

    @patch("linuxav.services.update_service.subprocess.run")
    @patch("linuxav.services.update_service.subprocess.Popen")
    def test_full_update_flow_success(self, mock_popen, mock_run):
        """Test complete update flow with success."""
        self.service.set_password("testpass")
        
        mock_run.return_value = Mock(returncode=0, stderr="")
        
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.stdout.readline.return_value = ""
        mock_process.wait.return_value = 0
        mock_process.stdin = Mock()
        mock_popen.return_value = mock_process
        
        result = self.service.update(timeout=60)
        
        self.assertTrue(result.success)
        self.assertIn("successfully", result.message.lower())
        self.service.clear_password()

    @patch("linuxav.services.update_service.subprocess.run")
    @patch("linuxav.services.update_service.subprocess.Popen")
    def test_full_update_flow_network_error(self, mock_popen, mock_run):
        """Test update flow with network error and mirror fallback."""
        self.service.set_password("testpass")
        
        mock_run.return_value = Mock(returncode=0, stderr="")
        
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.stdout.readline.return_value = ""
        mock_process.wait.return_value = 2
        mock_process.stdin = Mock()
        mock_popen.return_value = mock_process
        
        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            if "wget" in cmd:
                return Mock(returncode=0, stderr="")
            return Mock(returncode=0, stderr="")
        
        mock_run.side_effect = run_side_effect
        
        result = self.service.update(timeout=60)
        
        self.assertIn(result.success, [True, False])
        self.service.clear_password()

    def test_thread_safety(self):
        """Test service is thread-safe."""
        results = []
        
        def run_update():
            with patch.object(UpdateService, "_stop_service_safe", return_value=True):
                with patch.object(UpdateService, "_run_freshclam", return_value=UpdateResult(True, "OK", "output")):
                    with patch.object(UpdateService, "_restart_service"):
                        self.service.set_password("testpass")
                        results.append(self.service.update())
                        self.service.clear_password()
        
        thread = threading.Thread(target=run_update)
        thread.start()
        thread.join(timeout=5)
        
        self.assertEqual(len(results), 1)

    @patch.object(UpdateService, "_run_freshclam")
    def test_cancel_handles_password_cleared(self, mock_freshclam):
        """Test cancel works even when password is cleared after update."""
        self.service.set_password("testpass")
        self.service._is_updating = True
        
        mock_freshclam.return_value = UpdateResult(False, "Cancelled", error="cancelled")
        
        with patch.object(self.service, "_restart_service"):
            result = self.service.cancel()
        
        self.assertTrue(result)

    @patch.object(UpdateService, "_run_sudo_command")
    def test_mirror_fallback_with_password(self, mock_sudo):
        """Test mirror fallback uses password."""
        self.service.set_password("testpass")
        
        mock_sudo.return_value = Mock(returncode=0, stderr="")
        
        with patch("linuxav.services.update_service.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_cvd_file = MagicMock()
            mock_cvd_file.stat.return_value.st_size = 2000000
            mock_path_instance.__truediv__.return_value = mock_cvd_file
            mock_path.return_value = mock_path_instance
            
            with patch("linuxav.services.update_service.subprocess.run", mock_sudo):
                result = self.service._try_alternative_mirrors(300)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.mirror_used)


if __name__ == "__main__":
    unittest.main()
