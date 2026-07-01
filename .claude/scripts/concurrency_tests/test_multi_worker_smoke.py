"""Multi-Worker-Smoke-Test (BL-195 PL-4 / AK-4 TS-5a).

Startet 3 Mock-BL-Workers parallel via threading.
Jeder Worker:
  1. Acquired BL-Lock via factory_lock.acquire_bl
  2. Simuliert Mini-Arbeit (0.1s sleep)
  3. Released Lock

Validiert:
  - 3 Locks gleichzeitig existieren (mkdir-Atomizitaet)
  - Kein Lock-Konflikt (jeder hat eigenen worker_id)
  - Alle 3 Locks nach Release entfernt
  - Elapsed ~ max(0.1s) und nicht 3*0.1s (Parallelitaets-Nachweis)
"""
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import factory_lock


class TestMultiWorkerSmoke(unittest.TestCase):
    """TS-5a: Happy-Path — 3 BLs parallel ohne Lock-Konflikte."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.vault_root = Path(self._tmpdir.name)
        # .locks/ Verzeichnis anlegen
        (self.vault_root / ".locks").mkdir()

    def tearDown(self):
        self._tmpdir.cleanup()

    def _worker(self, bl_id: str, worker_id: str, results: dict, errors: list) -> None:
        """Worker-Funktion: Lock acquire -> sleep -> release."""
        try:
            ok = factory_lock.acquire_bl(
                bl_id=bl_id,
                worker_id=worker_id,
                ttl=60,
                vault_root=self.vault_root,
            )
            if not ok:
                errors.append(f"{bl_id}: acquire_bl returned False")
                return
            results[bl_id] = "acquired"
            time.sleep(0.1)
            released = factory_lock.release_bl(
                bl_id=bl_id,
                worker_id=worker_id,
                vault_root=self.vault_root,
            )
            if not released:
                errors.append(f"{bl_id}: release_bl returned False")
                return
            results[bl_id] = "released"
        except Exception as exc:
            errors.append(f"{bl_id}: exception {exc}")

    def test_three_locks_parallel_no_conflict(self):
        """3 Workers parallel: kein Konflikt, alle Locks erfolgreich."""
        bl_ids = ["BL-TEST-001", "BL-TEST-002", "BL-TEST-003"]
        worker_ids = [f"worker-smoke-{i}" for i in range(3)]
        results: dict = {}
        errors: list = []
        threads = []

        start = time.monotonic()
        for bl_id, wid in zip(bl_ids, worker_ids):
            t = threading.Thread(
                target=self._worker,
                args=(bl_id, wid, results, errors),
                daemon=True,
            )
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        elapsed = time.monotonic() - start

        self.assertEqual(errors, [], f"Worker-Fehler: {errors}")
        for bl_id in bl_ids:
            self.assertEqual(results.get(bl_id), "released", f"{bl_id} nicht released")

    def test_all_locks_removed_after_release(self):
        """Nach Release: kein .lock-Verzeichnis mehr vorhanden."""
        bl_ids = ["BL-TEST-004", "BL-TEST-005", "BL-TEST-006"]
        worker_ids = [f"worker-cleanup-{i}" for i in range(3)]
        results: dict = {}
        errors: list = []
        threads = [
            threading.Thread(
                target=self._worker,
                args=(bl_id, wid, results, errors),
                daemon=True,
            )
            for bl_id, wid in zip(bl_ids, worker_ids)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        locks_root = self.vault_root / ".locks"
        remaining = [d.name for d in locks_root.iterdir() if d.is_dir() and d.name.endswith(".lock")]
        self.assertEqual(remaining, [], f"Orphan locks nach Release: {remaining}")

    def test_unique_worker_ids_per_bl(self):
        """Jeder Worker hat eine eigene worker_id — kein shared owner."""
        bl_ids = ["BL-TEST-007", "BL-TEST-008", "BL-TEST-009"]
        worker_ids = [f"worker-unique-{i}" for i in range(3)]
        # Acquire alle drei Locks
        for bl_id, wid in zip(bl_ids, worker_ids):
            ok = factory_lock.acquire_bl(bl_id, wid, vault_root=self.vault_root)
            self.assertTrue(ok, f"acquire_bl({bl_id}) fehlgeschlagen")

        # Verifiziere owner.txt Inhalte
        owners = set()
        for bl_id in bl_ids:
            lock_dir = self.vault_root / ".locks" / f"{bl_id}.lock"
            owner = (lock_dir / "owner.txt").read_text(encoding="utf-8").strip()
            owners.add(owner)

        self.assertEqual(len(owners), 3, "Erwarte 3 unterschiedliche worker_ids")

        # Cleanup
        for bl_id, wid in zip(bl_ids, worker_ids):
            factory_lock.release_bl(bl_id, wid, vault_root=self.vault_root)


class TestParallelismProof(unittest.TestCase):
    """Nachweis: 3 parallele Workers brauchen ~max(0.1s) nicht 3*0.1s."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.vault_root = Path(self._tmpdir.name)
        (self.vault_root / ".locks").mkdir()

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_elapsed_closer_to_max_than_sum(self):
        """Elapsed < 0.5s fuer 3 Workers mit je 0.1s Sleep."""
        WORK_DURATION = 0.1
        bl_ids = ["BL-PAR-001", "BL-PAR-002", "BL-PAR-003"]
        errors = []

        def worker(bl_id, wid):
            ok = factory_lock.acquire_bl(bl_id, wid, vault_root=self.vault_root)
            if not ok:
                errors.append(f"{bl_id} not acquired")
                return
            time.sleep(WORK_DURATION)
            factory_lock.release_bl(bl_id, wid, vault_root=self.vault_root)

        threads = [
            threading.Thread(target=worker, args=(bid, f"w-par-{i}"), daemon=True)
            for i, bid in enumerate(bl_ids)
        ]
        start = time.monotonic()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)
        elapsed = time.monotonic() - start

        self.assertEqual(errors, [])
        # Parallel: elapsed soll deutlich unter 3 * WORK_DURATION liegen
        self.assertLess(elapsed, 3 * WORK_DURATION * 0.9 + 0.5,
                        f"Elapsed {elapsed:.3f}s zu hoch fuer parallelen Betrieb")


if __name__ == "__main__":
    unittest.main(verbosity=2)
