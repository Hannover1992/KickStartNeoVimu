"""Tests fuer sync_delay_wrapper.py (BL-195 PL-3).

3 Tests:
  1. delay-off-default: kein Sleep wenn BL195_SYNC_DELAY_ENABLED nicht gesetzt
  2. instant-vs-typical: INSTANT=0 kein Sleep, ONEDRIVE_TYPICAL=30 -> Sleep(30)
  3. delayed-mkdir-still-creates: Verzeichnis wird erstellt (auch mit Mock-Sleep)
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from concurrency_tests.sync_delay_wrapper import (
    SyncDelayProfile,
    delayed_mkdir,
    delayed_write,
    get_delay_s,
)


class TestDelayOffDefault(unittest.TestCase):
    """Test 1: kein Delay wenn Env-Var nicht gesetzt."""

    def setUp(self):
        os.environ.pop("BL195_SYNC_DELAY_ENABLED", None)
        os.environ.pop("BL195_SYNC_PROFILE", None)

    def test_get_delay_zero_by_default(self):
        self.assertEqual(get_delay_s(), 0.0)

    def test_delayed_write_no_sleep(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.txt"
            with patch("concurrency_tests.sync_delay_wrapper.time.sleep") as mock_sleep:
                delayed_write(p, "hello")
                mock_sleep.assert_not_called()
            self.assertEqual(p.read_text(encoding="utf-8"), "hello")


class TestInstantVsTypical(unittest.TestCase):
    """Test 2: INSTANT kein Sleep, ONEDRIVE_TYPICAL ruft sleep(30) auf."""

    def tearDown(self):
        os.environ.pop("BL195_SYNC_DELAY_ENABLED", None)
        os.environ.pop("BL195_SYNC_PROFILE", None)

    def test_instant_profile_no_sleep(self):
        os.environ["BL195_SYNC_DELAY_ENABLED"] = "1"
        os.environ["BL195_SYNC_PROFILE"] = "INSTANT"
        with patch("concurrency_tests.sync_delay_wrapper.time.sleep") as mock_sleep:
            with tempfile.TemporaryDirectory() as d:
                delayed_write(Path(d) / "f.txt", "x")
            mock_sleep.assert_not_called()

    def test_typical_profile_sleep_30(self):
        os.environ["BL195_SYNC_DELAY_ENABLED"] = "1"
        os.environ["BL195_SYNC_PROFILE"] = "ONEDRIVE_TYPICAL"
        self.assertEqual(get_delay_s(), float(SyncDelayProfile.ONEDRIVE_TYPICAL))
        with patch("concurrency_tests.sync_delay_wrapper.time.sleep") as mock_sleep:
            with tempfile.TemporaryDirectory() as d:
                delayed_write(Path(d) / "f.txt", "x")
            mock_sleep.assert_called_once_with(30.0)


class TestDelayedMkdirStillCreates(unittest.TestCase):
    """Test 3: Verzeichnis wird erstellt auch wenn Sleep gemockt ist."""

    def setUp(self):
        os.environ.pop("BL195_SYNC_DELAY_ENABLED", None)
        os.environ.pop("BL195_SYNC_PROFILE", None)

    def test_mkdir_creates_directory(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "sub" / "dir"
            with patch("concurrency_tests.sync_delay_wrapper.time.sleep"):
                delayed_mkdir(target)
            self.assertTrue(target.is_dir())

    def test_mkdir_idempotent(self):
        """exist_ok=True: zweimal aufrufen darf keinen Fehler werfen."""
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "sub"
            delayed_mkdir(target)
            delayed_mkdir(target)  # darf nicht raisen
            self.assertTrue(target.is_dir())


if __name__ == "__main__":
    unittest.main(verbosity=2)
