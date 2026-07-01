"""Tests fuer lock_steal_simulator.py (BL-195 PL-2).

3 Tests:
  1. force-stale-creates-old-ts: Timestamp ist age_seconds in der Vergangenheit
  2. restore-fresh-current: Timestamp ist aktuell (< 2s alt)
  3. missing-heartbeat-error: FileNotFoundError wenn heartbeat.txt fehlt
"""
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from concurrency_tests.lock_steal_simulator import force_stale, restore_fresh


class TestForceStale(unittest.TestCase):
    """Test 1: force_stale schreibt einen alten Timestamp."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.lock_dir = Path(self._tmpdir.name)
        # heartbeat.txt mit aktuellem Timestamp anlegen
        (self.lock_dir / "heartbeat.txt").write_text(
            datetime.now(timezone.utc).isoformat() + "\n", encoding="utf-8"
        )

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_force_stale_creates_old_timestamp(self):
        age = 600
        ts = force_stale(self.lock_dir, age_seconds=age)
        # Timestamp muss aelter als 590s sein
        age_actual = (datetime.now(timezone.utc) - ts).total_seconds()
        self.assertGreater(age_actual, age - 10, "Timestamp ist nicht alt genug")
        self.assertLess(age_actual, age + 10, "Timestamp ist zu alt")

    def test_force_stale_file_content_matches(self):
        ts = force_stale(self.lock_dir, age_seconds=300)
        content = (self.lock_dir / "heartbeat.txt").read_text(encoding="utf-8").strip()
        self.assertIn(ts.year.__str__(), content)


class TestRestoreFresh(unittest.TestCase):
    """Test 2: restore_fresh schreibt einen aktuellen Timestamp."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.lock_dir = Path(self._tmpdir.name)
        # Zuerst stale machen, dann wieder frisch
        (self.lock_dir / "heartbeat.txt").write_text(
            (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat() + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_restore_fresh_is_current(self):
        ts = restore_fresh(self.lock_dir)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        self.assertLess(age, 2.0, "Timestamp soll frisch sein (< 2s alt)")


class TestMissingHeartbeat(unittest.TestCase):
    """Test 3: FileNotFoundError wenn heartbeat.txt fehlt."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.lock_dir = Path(self._tmpdir.name)
        # Kein heartbeat.txt anlegen

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_force_stale_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            force_stale(self.lock_dir)

    def test_restore_fresh_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            restore_fresh(self.lock_dir)


if __name__ == "__main__":
    unittest.main(verbosity=2)
