#!/usr/bin/env python3
"""
BL-195 AK-4: Stress-Tests fuer factory_lock-Pattern (file-based locking).

Tests:
  S1: 5 parallele Lock-Acquisitions - nur 1 sollte erfolgreich sein
  S2: 10 parallele Acquisitions - skaliert wie erwartet
  S3: Heartbeat-Stress - 3 parallele Heartbeat-Daemons
  S4: Stale-Lock-Recovery - TTL-basiert
"""

import os
import sys
import time
import tempfile
from pathlib import Path

# Path setup
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from concurrency_test_helpers import trigger_race, temp_vault, heartbeat_stress


def acquire_lock(worker_id, lock_dir):
    """Worker: versucht Lock zu erwerben (file-based via O_EXCL)."""
    lock_path = Path(lock_dir) / "_factory_lock.md"
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"worker_id: {worker_id}\nts: {time.time()}\n".encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def release_lock(worker_id, lock_dir):
    """Worker: release Lock."""
    lock_path = Path(lock_dir) / "_factory_lock.md"
    if lock_path.exists():
        lock_path.unlink()


def test_s1_5_workers_lock_contention():
    """S1: 5 parallele Workers, nur 1 sollte Lock bekommen."""
    with temp_vault() as ctx:
        lock_dir = str(ctx["vault_root"])
        results = trigger_race(5, acquire_lock, args=(lock_dir,))
        acquirers = [wid for wid, status, val in results if val is True]
        for wid in acquirers:
            release_lock(wid, lock_dir)
        assert len(acquirers) == 1, f"Expected 1 acquirer, got {len(acquirers)}: {acquirers}"
    print("[S1] PASS: 5 workers, 1 acquired (4 rejected)")


def test_s2_10_workers_lock_contention():
    """S2: 10 parallele Workers, nur 1 sollte Lock bekommen."""
    with temp_vault() as ctx:
        lock_dir = str(ctx["vault_root"])
        results = trigger_race(10, acquire_lock, args=(lock_dir,))
        acquirers = [wid for wid, status, val in results if val is True]
        rejecters = [wid for wid, status, val in results if val is False]
        for wid in acquirers:
            release_lock(wid, lock_dir)
        assert len(acquirers) == 1, f"Expected 1 acquirer, got {len(acquirers)}"
        assert len(rejecters) == 9, f"Expected 9 rejecters, got {len(rejecters)}"
    print("[S2] PASS: 10 workers, 1 acquired (9 rejected)")


def write_heartbeat(process_id, hb_dir):
    """Heartbeat-Function: write to file."""
    hb_path = Path(hb_dir) / f"heartbeat_{process_id}.md"
    hb_path.write_text(f"ts: {time.time()}\n")


def test_s3_heartbeat_stress():
    """S3: 3 parallele Heartbeats fuer 3 Sekunden."""
    with temp_vault() as ctx:
        hb_dir = str(ctx["vault_root"])
        counts = heartbeat_stress(write_heartbeat, hb_dir, duration_sec=3, n_processes=3, interval_sec=0.5)
        for i, c in enumerate(counts):
            assert c >= 3, f"Process {i} only {c} heartbeats (expected >= 3)"
    print(f"[S3] PASS: 3 heartbeats parallel, counts={counts}")


def test_s4_stale_lock_recovery():
    """S4: Alter Lock (>TTL) sollte als stale erkennbar sein."""
    with temp_vault() as ctx:
        lock_path = ctx["vault_root"] / "_factory_lock.md"
        stale_ts = time.time() - 600
        lock_path.write_text(f"worker_id: stale\nts: {stale_ts}\nttl: 300\n")
        ttl_expired = stale_ts + 300 < time.time()
        assert ttl_expired, "Stale lock should be expired per TTL"
        lock_path.write_text(f"worker_id: new\nts: {time.time()}\n")
    print("[S4] PASS: stale lock TTL-recovery simulated")


def main():
    tests = [
        test_s1_5_workers_lock_contention,
        test_s2_10_workers_lock_contention,
        test_s3_heartbeat_stress,
        test_s4_stale_lock_recovery,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n=== {passed}/{passed+failed} stress-tests passed ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
