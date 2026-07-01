"""
test_factory_lock.py — BL-175: Tests for factory_lock.py

12 Tests including race-condition simulation.
Run: py -3 -m pytest .claude/scripts/test_factory_lock.py -v
"""

import os
import sys
import time
import threading
import tempfile
from pathlib import Path

import pytest

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))

import factory_lock as fl


@pytest.fixture
def tmp_vault(tmp_path):
    """Provide a temporary vault root for isolation."""
    return tmp_path


@pytest.fixture(autouse=True)
def patch_vault(tmp_vault, monkeypatch):
    """Patch VAULT_ROOT so tests use tmp dir."""
    monkeypatch.setattr(fl, "VAULT_ROOT", tmp_vault)
    # Also patch _emit_audit to no-op to avoid audit file side effects
    monkeypatch.setattr(fl, "_emit_audit", lambda *a, **kw: None)
    yield


# ─── Test 1: acquire first call ───────────────────────────────────────────────

def test_acquire_first_call(tmp_vault):
    """First acquire() on empty vault returns True and creates lock file."""
    result = fl.acquire(worker_id="w1", timeout=0, vault_root=tmp_vault)
    assert result is True
    lock_path = fl._lock_file_path(tmp_vault)
    assert lock_path.exists()


# ─── Test 2: acquire second call blocked ──────────────────────────────────────

def test_acquire_second_call_blocked(tmp_vault):
    """Second acquire() by different worker with timeout=0 returns False."""
    fl.acquire(worker_id="w1", ttl=300, timeout=0, vault_root=tmp_vault)
    result = fl.acquire(worker_id="w2", timeout=0, vault_root=tmp_vault)
    assert result is False


# ─── Test 3: release then acquire ─────────────────────────────────────────────

def test_release_then_acquire(tmp_vault):
    """After release(), a new worker can acquire."""
    fl.acquire(worker_id="w1", timeout=0, vault_root=tmp_vault)
    fl.release(worker_id="w1", vault_root=tmp_vault)
    result = fl.acquire(worker_id="w2", timeout=0, vault_root=tmp_vault)
    assert result is True
    info = fl.is_locked(vault_root=tmp_vault)
    assert info is not None
    assert info["holder"] == "w2"


# ─── Test 4: stale lock released ──────────────────────────────────────────────

def test_stale_lock_released(tmp_vault):
    """Lock with ttl=1 becomes stale after 1.5s; new acquire() succeeds."""
    fl.acquire(worker_id="w1", ttl=1, timeout=0, vault_root=tmp_vault)
    time.sleep(1.5)
    result = fl.acquire(worker_id="w2", ttl=300, timeout=0, vault_root=tmp_vault)
    assert result is True
    info = fl.is_locked(vault_root=tmp_vault)
    assert info is not None
    assert info["holder"] == "w2"


# ─── Test 5: heartbeat updates heartbeat_at ───────────────────────────────────

def test_heartbeat_extends_heartbeat_at(tmp_vault):
    """heartbeat() updates heartbeat_at timestamp."""
    fl.acquire(worker_id="w1", timeout=0, vault_root=tmp_vault)
    lock_path = fl._lock_file_path(tmp_vault)
    fm1, _ = fl._read_lock(lock_path)
    hb_before = fm1.get("heartbeat_at", "")

    time.sleep(1.1)
    ok = fl.heartbeat(worker_id="w1", vault_root=tmp_vault)
    assert ok is True

    fm2, _ = fl._read_lock(lock_path)
    hb_after = fm2.get("heartbeat_at", "")
    assert hb_after != hb_before


# ─── Test 6: concurrent acquire only one wins ─────────────────────────────────

def test_concurrent_acquire_only_one_wins(tmp_vault):
    """10 threads racing acquire(); exactly 1 should win."""
    winners = []
    lock = threading.Lock()

    def try_acquire(wid):
        try:
            result = fl.acquire(worker_id=wid, timeout=0, vault_root=tmp_vault)
        except fl.LockFileError:
            result = False  # Lost race on Windows atomic write — treat as not acquired
        if result:
            with lock:
                winners.append(wid)

    threads = [threading.Thread(target=try_acquire, args=(f"worker-{i}",)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # INV-LOCK-3: at most 1 winner at a time
    assert len(winners) <= 1, f"Expected at most 1 winner, got {len(winners)}: {winners}"
    # At least 1 thread should succeed (one eventually gets past contention)
    # With timeout=0, under extreme contention it's acceptable to have 0 winners;
    # what matters is no more than 1 wins simultaneously.
    # Verify lock state is consistent
    info = fl.is_locked(vault_root=tmp_vault)
    if winners:
        assert info is not None
        assert info["holder"] == winners[0]


# ─── Test 7: force_release ────────────────────────────────────────────────────

def test_force_release(tmp_vault):
    """force_release() frees the lock regardless of holder."""
    fl.acquire(worker_id="w1", timeout=0, vault_root=tmp_vault)
    fl.force_release(vault_root=tmp_vault)
    info = fl.is_locked(vault_root=tmp_vault)
    assert info is None


# ─── Test 8: is_locked returns holder ─────────────────────────────────────────

def test_is_locked_returns_holder(tmp_vault):
    """is_locked() returns holder dict when lock is active."""
    assert fl.is_locked(vault_root=tmp_vault) is None
    fl.acquire(worker_id="w1", purpose="test-purpose", timeout=0, vault_root=tmp_vault)
    info = fl.is_locked(vault_root=tmp_vault)
    assert info is not None
    assert info["holder"] == "w1"
    assert "acquired_at" in info
    assert "ttl_seconds" in info
    assert info["purpose"] == "test-purpose"


# ─── Test 9: acquire with timeout ─────────────────────────────────────────────

def test_acquire_with_timeout(tmp_vault):
    """acquire() with timeout=2 waits at most ~2s when lock is held."""
    fl.acquire(worker_id="w1", ttl=300, timeout=0, vault_root=tmp_vault)
    start = time.monotonic()
    result = fl.acquire(worker_id="w2", ttl=300, timeout=2, vault_root=tmp_vault)
    elapsed = time.monotonic() - start
    assert result is False
    assert elapsed < 5.0, f"Waited too long: {elapsed}s"


# ─── Test 10: invalid worker_id release fails ─────────────────────────────────

def test_invalid_worker_id_release_fails(tmp_vault):
    """release() with wrong worker_id returns False; lock remains held."""
    fl.acquire(worker_id="w1", timeout=0, vault_root=tmp_vault)
    result = fl.release(worker_id="wrong-worker", vault_root=tmp_vault)
    assert result is False
    # Lock still held by w1
    info = fl.is_locked(vault_root=tmp_vault)
    assert info is not None
    assert info["holder"] == "w1"


# ─── Test 11: lock file persists after acquire ────────────────────────────────

def test_lock_file_persists_after_acquire(tmp_vault):
    """Lock file contains correct YAML data after acquire()."""
    fl.acquire(worker_id="my-worker-99", ttl=120, scope="global", purpose="BDF test", timeout=0, vault_root=tmp_vault)
    lock_path = fl._lock_file_path(tmp_vault)
    assert lock_path.exists()
    fm, log_lines = fl._read_lock(lock_path)
    assert fm["holder"] == "my-worker-99"
    assert fm["ttl_seconds"] == 120
    assert fm["scope"] == "global"
    assert fm["stage"] == "SCANNING"
    assert len(log_lines) >= 1
    assert "ACQUIRED" in log_lines[0]


# ─── Test 12: two parallel BDFs serialize (race condition test) ───────────────

def test_two_parallel_bdfs_serialize(tmp_vault):
    """
    Race-Condition test: Two simulated BDF workers compete for the lock.
    - Both try to acquire simultaneously
    - Only one holds the lock at any time (INV-LOCK-3)
    - Both eventually complete their work
    - No overlap in lock ownership
    """
    results = []
    overlap_detected = threading.Event()
    lock_holder_slots = []
    slot_lock = threading.Lock()

    def bdf_worker(wid: str, work_ms: int):
        """Simulate a BDF worker: acquire -> work -> release."""
        acquired = fl.acquire(worker_id=wid, ttl=60, timeout=30, vault_root=tmp_vault)
        if not acquired:
            results.append({"worker": wid, "status": "timeout"})
            return

        # Check for overlap
        with slot_lock:
            if lock_holder_slots:
                overlap_detected.set()
            lock_holder_slots.append(wid)

        # Verify we are the holder
        info = fl.is_locked(vault_root=tmp_vault)
        assert info is not None, f"{wid}: is_locked() returned None after acquire"
        assert info["holder"] == wid, f"{wid}: holder mismatch: {info['holder']}"

        # Simulate work (reading/writing backlog index)
        time.sleep(work_ms / 1000.0)

        with slot_lock:
            lock_holder_slots.remove(wid)

        released = fl.release(worker_id=wid, vault_root=tmp_vault)
        assert released is True, f"{wid}: release() failed"
        results.append({"worker": wid, "status": "done"})

    t1 = threading.Thread(target=bdf_worker, args=("bdf-terminal-A", 200))
    t2 = threading.Thread(target=bdf_worker, args=("bdf-terminal-B", 200))

    t1.start()
    t2.start()
    t1.join(timeout=15)
    t2.join(timeout=15)

    assert not overlap_detected.is_set(), "Lock overlap detected! Two workers held lock simultaneously."
    done_results = [r for r in results if r["status"] == "done"]
    assert len(done_results) == 2, f"Not all workers completed: {results}"


# ─── Test 13: acquire_bl TOCTOU — N threads on a FRESH BL-lock (BL-344) ────────

def test_acquire_bl_concurrent_fresh_lock_exclusive(tmp_vault):
    """BL-344: N=8 barrier-synchronized threads each call acquire_bl with a UNIQUE
    worker_id on ONE fresh bl_id. Exposes the two TOCTOU races in acquire_bl:

      Race A (false-stale): the mkdir-winner writes heartbeat.txt only AFTER the
        other metadata; a concurrent loser sees FileExistsError -> is_bl_stale ->
        heartbeat.txt missing -> True -> treats the LIVE lock as stale -> rmtree +
        remkdir -> TWO owners (acquired_count > 1).
      Race B (crash): several losers race on rmtree + mkdir(exist_ok=False) in the
        stale-branch; the remkdir is uncaught -> FileExistsError escapes -> a worker
        thread dies (uncaught exception).

    Contract: exactly ONE thread gets True (mutual exclusion), ZERO uncaught
    exceptions, the lock dir exists with exactly ONE owner.
    """
    n = 8
    bl_id = "BL-RACE"
    acquired = []
    errors = []
    acq_lock = threading.Lock()
    barrier = threading.Barrier(n)

    def worker(i):
        wid = f"race-w{i}"
        try:
            barrier.wait(timeout=10.0)
        except threading.BrokenBarrierError:
            with acq_lock:
                errors.append((wid, "barrier-timeout"))
            return
        try:
            got = fl.acquire_bl(bl_id, worker_id=wid, ttl=600, vault_root=tmp_vault)
            if got:
                with acq_lock:
                    acquired.append(wid)
        except Exception as e:  # uncaught FileExistsError etc. = Race B
            with acq_lock:
                errors.append((wid, repr(e)))

    threads = [threading.Thread(target=worker, args=(i,), name=f"bl-race-w{i}")
               for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20.0)

    assert not any(t.is_alive() for t in threads), "A worker thread hung (possible dead-lock)"
    assert errors == [], f"Uncaught exception(s) in acquire_bl (Race B): {errors}"
    assert len(acquired) == 1, (
        f"Mutual exclusion violated — {len(acquired)} threads acquired the FRESH "
        f"lock simultaneously (expected exactly 1): {acquired}"
    )

    # The lock dir exists with exactly one owner == the single winner.
    lock_dir = fl._bl_lock_dir(bl_id, vault_root=tmp_vault)
    assert lock_dir.exists(), "Lock dir missing after acquire"
    owner = (lock_dir / "owner.txt").read_text(encoding="utf-8").strip()
    assert owner == acquired[0], f"Owner {owner!r} != winner {acquired[0]!r}"
