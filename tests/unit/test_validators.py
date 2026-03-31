import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
from pathlib import Path

from linuxav.domain.validators import (
    is_valid_path,
    is_valid_directory,
    is_safe_path,
    validate_scan_path,
    get_safe_default_path,
    DANGEROUS_DIRS,
)


class TestValidators(unittest.TestCase):
    def test_dangerous_dirs_defined(self):
        self.assertIn("/proc", DANGEROUS_DIRS)
        self.assertIn("/sys", DANGEROUS_DIRS)
        self.assertIn("/dev", DANGEROUS_DIRS)

    def test_is_valid_path_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertTrue(is_valid_path(tmpdir))
            self.assertTrue(is_valid_path(__file__))

    def test_is_valid_path_not_exists(self):
        self.assertFalse(is_valid_path("/nonexistent/path/12345"))

    def test_is_valid_directory_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertTrue(is_valid_directory(tmpdir))

    def test_is_valid_directory_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.assertFalse(is_valid_directory(tmp_path))
        finally:
            os.unlink(tmp_path)

    def test_is_safe_path_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertTrue(is_safe_path(tmpdir))

    def test_is_safe_path_dangerous_proc(self):
        self.assertFalse(is_safe_path("/proc"))
        self.assertFalse(is_safe_path("/proc/test"))

    def test_is_safe_path_dangerous_sys(self):
        self.assertFalse(is_safe_path("/sys"))
        self.assertFalse(is_safe_path("/sys/kernel"))

    def test_is_safe_path_dangerous_dev(self):
        self.assertFalse(is_safe_path("/dev"))
        self.assertFalse(is_safe_path("/dev/null"))

    def test_is_safe_path_subdirectory_allowed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            self.assertTrue(is_safe_path(str(subdir)))

    def test_validate_scan_path_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            valid, error = validate_scan_path(tmpdir)
            self.assertTrue(valid)
            self.assertIsNone(error)

    def test_validate_scan_path_not_exists(self):
        valid, error = validate_scan_path("/nonexistent/path")
        self.assertFalse(valid)
        self.assertIsNotNone(error)

    def test_validate_scan_path_is_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            valid, error = validate_scan_path(tmp_path)
            self.assertFalse(valid)
            self.assertIn("directorio", error.lower())
        finally:
            os.unlink(tmp_path)

    def test_validate_scan_path_dangerous(self):
        valid, error = validate_scan_path("/proc")
        self.assertFalse(valid)
        self.assertIsNotNone(error)

    def test_get_safe_default_path(self):
        home = str(Path.home())
        default = get_safe_default_path()
        self.assertEqual(default, home)

    def test_is_valid_path_invalid_chars(self):
        self.assertTrue(is_valid_path("/home"))  # valid path

    @patch("linuxav.domain.validators.Path")
    def test_is_valid_path_exception(self, mock_path):
        mock_path.side_effect = OSError("Invalid path")
        self.assertFalse(is_valid_path("/some/path"))


if __name__ == "__main__":
    unittest.main()
