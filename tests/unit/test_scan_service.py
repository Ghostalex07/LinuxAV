import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from linuxav.services.scan_service import ScanService
from linuxav.domain.enums import ScanStatus
from linuxav.adapters.clamav_adapter import ScanResponse


class TestScanService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        try:
            os.rmdir(self.temp_dir)
        except:
            pass

    def test_scan_directory_invalid_path(self):
        service = ScanService()
        result = service.scan_directory("/nonexistent/path/12345")

        self.assertEqual(result.status, ScanStatus.ERROR)
        self.assertIsNotNone(result.error_message)

    def test_scan_directory_already_scanning(self):
        service = ScanService()
        service._is_scanning = True

        result = service.scan_directory(self.temp_dir)

        self.assertEqual(result.status, ScanStatus.ERROR)
        self.assertIn("already in progress", result.error_message)

    def test_stop_scan(self):
        service = ScanService()
        service._is_scanning = True
        service.stop_scan()
        self.assertTrue(service._should_stop)

    def test_add_progress_callback(self):
        service = ScanService()
        callback_called = []

        def callback(event):
            callback_called.append(event)

        service.add_progress_callback(callback)
        self.assertIn(callback, service._progress_callbacks)

    def test_remove_progress_callback(self):
        service = ScanService()

        def callback(event):
            pass

        service.add_progress_callback(callback)
        service.remove_progress_callback(callback)
        self.assertNotIn(callback, service._progress_callbacks)

    def test_add_threat_callback(self):
        service = ScanService()
        callback_called = []

        def callback(file_path, threat_name):
            callback_called.append((file_path, threat_name))

        service.add_threat_callback(callback)
        self.assertIn(callback, service._threat_callbacks)

    def test_set_complete_callback(self):
        service = ScanService()

        def callback(result):
            pass

        service.set_complete_callback(callback)
        self.assertEqual(service._on_complete_callback, callback)


class TestScanServiceWithMock(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        try:
            os.rmdir(self.temp_dir)
        except:
            pass

    @patch("linuxav.services.scan_service.ClamAVAdapter")
    def test_scan_success(self, mock_class):
        mock_adapter = Mock()
        mock_class.return_value = mock_adapter
        mock_adapter.scan.return_value = ScanResponse(
            status=ScanStatus.CLEAN,
            scanned_files=100,
            threats_found=0,
            threats=[],
        )

        service = ScanService()
        result = service.scan_directory(self.temp_dir)

        self.assertEqual(result.status, ScanStatus.CLEAN)

    @patch("linuxav.services.scan_service.ClamAVAdapter")
    def test_scan_infected(self, mock_class):
        mock_adapter = Mock()
        mock_class.return_value = mock_adapter
        mock_adapter.scan.return_value = ScanResponse(
            status=ScanStatus.INFECTED,
            scanned_files=50,
            threats_found=2,
            threats=[("/tmp/virus", "Trojan")],
        )

        service = ScanService()
        result = service.scan_directory(self.temp_dir)

        self.assertEqual(result.status, ScanStatus.INFECTED)
        self.assertEqual(result.threats_found, 2)


if __name__ == "__main__":
    unittest.main()
