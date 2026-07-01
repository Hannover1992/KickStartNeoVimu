"""Test-Runner: alle BL-195 Concurrency-Test-Suites.

Orchestriert PL-1 bis PL-4 und reportet Pass/Fail.

Usage:
  py -3 run_all_concurrency_tests.py
"""
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

TEST_MODULES = [
    "concurrency_tests.test_chaos_inject",
    "concurrency_tests.test_lock_steal_simulator",
    "concurrency_tests.test_sync_delay_wrapper",
    "concurrency_tests.test_multi_worker_smoke",
]

SUITE_NAMES = [
    "PL-1: chaos_inject",
    "PL-2: lock_steal_simulator",
    "PL-3: sync_delay_wrapper",
    "PL-4: test_multi_worker_smoke",
]


def run_all() -> int:
    """Fuehrt alle Test-Suites aus. Gibt Anzahl Fehler zurueck."""
    loader = unittest.TestLoader()
    total_run = 0
    total_errors = 0
    total_failures = 0

    print("=" * 60)
    print("BL-195 Concurrency-Test-Infrastructure — Test-Runner")
    print("=" * 60)

    for module_name, suite_name in zip(TEST_MODULES, SUITE_NAMES):
        try:
            suite = loader.loadTestsFromName(module_name)
        except Exception as exc:
            print(f"\n[LOAD-ERROR] {suite_name}: {exc}")
            total_errors += 1
            continue

        runner = unittest.TextTestRunner(verbosity=1, stream=sys.stdout)
        print(f"\n--- {suite_name} ---")
        result = runner.run(suite)
        total_run += result.testsRun
        total_errors += len(result.errors)
        total_failures += len(result.failures)

    print("\n" + "=" * 60)
    total_pass = total_run - total_errors - total_failures
    print(f"GESAMT: {total_run} Tests | PASS: {total_pass} | FAIL: {total_failures} | ERROR: {total_errors}")
    if total_errors + total_failures == 0:
        print("RESULT: ALL PASS")
    else:
        print("RESULT: FAIL")
    print("=" * 60)

    return total_errors + total_failures


if __name__ == "__main__":
    exit_code = run_all()
    sys.exit(0 if exit_code == 0 else 1)
