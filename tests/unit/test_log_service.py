import unittest
from unittest.mock import patch, Mock, mock_open, MagicMock
import tempfile
import os
from pathlib import Path
from datetime import datetime

from linuxav.services.log_service import LogService, ClamLogEntry


class TestLogService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = LogService(Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_find_clam_log_not_found(self):
        with patch("linuxav.services.log_service.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            result = self.service.find_clam_log()
            self.assertIsNone(result)

    def test_read_clam_log_no_file(self):
        with patch.object(self.service, "find_clam_log", return_value=None):
            result = self.service.read_clam_log()
            self.assertEqual(result, [])

    def test_read_clam_log_with_content(self):
        log_content = """Tue Jan 15 10:00:00 2024 INFO: ClamAV started
Tue Jan 15 10:00:01 2024 WARNING: Invalid signature
"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".log"
        ) as f:
            f.write(log_content)
            log_path = f.name

        try:
            with patch(
                "linuxav.services.log_service.LogService.CLAM_LOG_PATHS",
                [log_path],
            ):
                result = self.service.read_clam_log()

            self.assertEqual(len(result), 2)
            self.assertEqual(result[0].level, "INFO")
            self.assertEqual(result[1].level, "WARNING")
        finally:
            os.unlink(log_path)

    def test_get_scan_summary_clean(self):
        log_content = """Tue Jan 15 10:00:00 2024 Scanning /home
Tue Jan 15 10:00:01 2024 Scanned 100 files
"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".log"
        ) as f:
            f.write(log_content)
            log_path = f.name

        try:
            with patch(
                "linuxav.services.log_service.LogService.CLAM_LOG_PATHS",
                [log_path],
            ):
                result = self.service.get_scan_summary()

            self.assertIn("clean", result)
        finally:
            os.unlink(log_path)

    def test_get_scan_summary_infected(self):
        log_content = """Tue Jan 15 10:00:00 2024 /tmp/virus FOUND Trojan.Generic
"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".log"
        ) as f:
            f.write(log_content)
            log_path = f.name

        try:
            with patch(
                "linuxav.services.log_service.LogService.CLAM_LOG_PATHS",
                [log_path],
            ):
                result = self.service.get_scan_summary()

            self.assertIn("infected", result)
            self.assertGreater(result["infected"], 0)
        finally:
            os.unlink(log_path)

    def test_get_threats_from_log(self):
        service = LogService(app_log_dir=Path(self.temp_dir.name))
        
        log_content = """Tue Jan 15 10:00:00 2024 /tmp/malware.exe FOUND Win.Trojan.abc
Tue Jan 15 10:00:01 2024 /home/virus.zip FOUND Email.Worm.bcd"""

        with patch.object(service, "find_clam_log", return_value=None):
            result = service.get_threats_from_log()
            self.assertEqual(len(result), 0)  # No log file found

    def test_get_threats_from_log_with_content(self):
        service = LogService(app_log_dir=Path(self.temp_dir.name))
        
        log_content = """Tue Jan 15 10:00:00 2024 /tmp/malware.exe FOUND Win.Trojan.abc
Tue Jan 15 10:00:01 2024 /home/virus.zip FOUND Email.Worm.bcd"""

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".log"
        ) as f:
            f.write(log_content)
            log_path = f.name

        try:
            with patch.object(service, "CLAM_LOG_PATHS", [log_path]):
                result = service.get_threats_from_log()

            self.assertEqual(len(result), 2)
            # Verify threats were found
            self.assertTrue(any("malware" in r["file"] for r in result))
        finally:
            os.unlink(log_path)

    def test_get_threats_from_log_none(self):
        log_content = """Tue Jan 15 10:00:00 2024 Scanning /home
"""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".log"
        ) as f:
            f.write(log_content)
            log_path = f.name

        try:
            with patch(
                "linuxav.services.log_service.LogService.CLAM_LOG_PATHS",
                [log_path],
            ):
                result = self.service.get_threats_from_log()

            self.assertEqual(len(result), 0)
        finally:
            os.unlink(log_path)

    def test_write_app_log(self):
        message = "Test log message"
        self.service.write_app_log(message, "INFO")

        log_file = Path(self.temp_dir.name) / "linuxav.log"
        self.assertTrue(log_file.exists())

        content = log_file.read_text()
        self.assertIn(message, content)

    def test_read_app_log(self):
        log_file = Path(self.temp_dir.name) / "linuxav.log"
        log_file.write_text(
            "2024-01-15 10:00:00 - INFO - Test message 1\n"
            "2024-01-15 10:00:01 - INFO - Test message 2\n"
        )

        result = self.service.read_app_log()

        self.assertGreaterEqual(len(result), 2)

    def test_read_app_log_limited_lines(self):
        log_file = Path(self.temp_dir.name) / "linuxav.log"
        lines = "\n".join([f"Line {i}" for i in range(10)])
        log_file.write_text(lines)

        result = self.service.read_app_log(lines=3)

        self.assertEqual(len(result), 3)

    def test_read_app_log_no_file(self):
        result = self.service.read_app_log()
        self.assertEqual(result, [])


class TestClamLogEntry(unittest.TestCase):
    def test_clam_log_entry_creation(self):
        entry = ClamLogEntry(
            timestamp=datetime.now(),
            level="INFO",
            message="Test message",
            source="clamd",
        )

        self.assertEqual(entry.level, "INFO")
        self.assertEqual(entry.message, "Test message")
        self.assertEqual(entry.source, "clamd")


if __name__ == "__main__":
    unittest.main()
