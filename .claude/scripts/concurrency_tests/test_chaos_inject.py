"""Tests fuer chaos_inject.py (BL-195 PL-1).

3 Tests:
  1. chaos-off-default: kein Inject wenn BL195_CHAOS_ENABLED nicht gesetzt
  2. crash-injection: SystemExit wird geworfen wenn Chaos aktiv + Point passt
  3. sync-delay: time.sleep wird aufgerufen mit korrektem Wert
"""
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

# Projekt-Root ermitteln und zum sys.path hinzufuegen
_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from concurrency_tests.chaos_inject import ChaosPoint, chaos_active, maybe_inject


class TestChaosOff(unittest.TestCase):
    """Test 1: Chaos ist per default ausgeschaltet."""

    def setUp(self):
        # Sicherstellen dass Env-Vars nicht gesetzt sind
        os.environ.pop("BL195_CHAOS_ENABLED", None)
        os.environ.pop("BL195_CHAOS_POINT", None)

    def test_chaos_inactive_by_default(self):
        self.assertFalse(chaos_active())

    def test_no_inject_when_chaos_off(self):
        """maybe_inject darf keinen Effekt haben wenn Chaos aus."""
        # Kein Exception, kein Sleep
        with patch("time.sleep") as mock_sleep:
            maybe_inject(ChaosPoint.CRASH_AFTER_DISPATCH)
            maybe_inject(ChaosPoint.SYNC_DELAY, delay_s=10.0)
            mock_sleep.assert_not_called()


class TestCrashInjection(unittest.TestCase):
    """Test 2: SystemExit wenn CRASH_AFTER_DISPATCH aktiv."""

    def setUp(self):
        os.environ["BL195_CHAOS_ENABLED"] = "1"
        os.environ["BL195_CHAOS_POINT"] = ChaosPoint.CRASH_AFTER_DISPATCH.value

    def tearDown(self):
        os.environ.pop("BL195_CHAOS_ENABLED", None)
        os.environ.pop("BL195_CHAOS_POINT", None)

    def test_crash_injection_raises_system_exit(self):
        with self.assertRaises(SystemExit) as ctx:
            maybe_inject(ChaosPoint.CRASH_AFTER_DISPATCH)
        self.assertIn("crash-after-dispatch", str(ctx.exception))

    def test_wrong_point_no_crash(self):
        """Anderer Punkt: kein Crash."""
        maybe_inject(ChaosPoint.SYNC_DELAY, delay_s=0.0)  # darf nicht raisen


class TestSyncDelay(unittest.TestCase):
    """Test 3: time.sleep wird aufgerufen wenn SYNC_DELAY aktiv."""

    def setUp(self):
        os.environ["BL195_CHAOS_ENABLED"] = "1"
        os.environ["BL195_CHAOS_POINT"] = ChaosPoint.SYNC_DELAY.value

    def tearDown(self):
        os.environ.pop("BL195_CHAOS_ENABLED", None)
        os.environ.pop("BL195_CHAOS_POINT", None)

    def test_sync_delay_calls_sleep(self):
        with patch("concurrency_tests.chaos_inject.time.sleep") as mock_sleep:
            maybe_inject(ChaosPoint.SYNC_DELAY, delay_s=5.0)
            mock_sleep.assert_called_once_with(5.0)

    def test_sync_delay_zero_still_calls_sleep(self):
        with patch("concurrency_tests.chaos_inject.time.sleep") as mock_sleep:
            maybe_inject(ChaosPoint.SYNC_DELAY, delay_s=0.0)
            mock_sleep.assert_called_once_with(0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
