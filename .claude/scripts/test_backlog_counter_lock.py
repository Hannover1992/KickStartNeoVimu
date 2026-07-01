"""
test_backlog_counter_lock.py — Counter-Lock (Multi-Lane-Filing-Race, P2)

Tests for backlog_counter_lock.py::allocate_next_bl_id()

Contract:
    allocate_next_bl_id(
        vault_root,
        *,
        read_counter,
        write_counter,
        lock_scope="backlog_counter",
    ) -> int

    acquire(scope=lock_scope, vault_root) → cur = read_counter()
    → new = cur + 1 → write_counter(new) → release → return new.

    The lock bracket makes read-increment-write atomic:
    N concurrent callers deliver N DISTINCT consecutive numbers,
    final state == start + N (no lost-update, no duplicate).

Run: py -3 -m pytest .claude/scripts/test_backlog_counter_lock.py -v
"""

import sys
import threading
from pathlib import Path

import pytest

# Add scripts dir to path so local imports work.
sys.path.insert(0, str(Path(__file__).parent))

# TARGET MODULE — does NOT exist yet.  All tests must FAIL (RED).
from backlog_counter_lock import allocate_next_bl_id  # noqa: E402


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_vault(tmp_path):
    """Isolated vault root for each test — no shared lock files."""
    return tmp_path


@pytest.fixture
def counter_store():
    """Shared mutable counter with DI read/write closures (NO own locking).

    This is the race-surface.  allocate_next_bl_id's internal lock must be the
    SOLE serialisation mechanism — if it isn't, T2 will expose the bug.
    """
    store = {"value": 0}

    def read():
        return store["value"]

    def write(new_val):
        store["value"] = new_val

    return store, read, write


# ─── T1: single allocate — basic contract ─────────────────────────────────────

def test_single_allocate_returns_next_and_writes(tmp_vault, counter_store):
    """T1: counter start=41 → allocate returns 42, write_counter called with 42."""
    store, read, write = counter_store
    store["value"] = 41

    result = allocate_next_bl_id(tmp_vault, read_counter=read, write_counter=write)

    assert result == 42, f"Expected 42, got {result}"
    assert store["value"] == 42, f"Expected store to be 42, got {store['value']}"


# ─── T2: KERN-Race — N concurrent threads, zero duplicates, correct end state ─

def test_concurrent_allocations_are_distinct_and_sequential(tmp_vault, counter_store):
    """T2 (KERN): N=8 concurrent allocations under shared counter-store.

    All 8 returned IDs must be pairwise distinct.
    Final counter value must equal start + 8.

    No own locking in counter_store — the serialisation MUST come exclusively
    from allocate_next_bl_id's internal lock bracket (INV-LOCK-3).
    A naive no-lock implementation would race here → this is the RED proof.
    """
    N = 8
    store, read, write = counter_store
    start = 100
    store["value"] = start

    results = []
    lock = threading.Lock()  # only to collect results safely — NOT in counter_store

    def worker():
        bl_id = allocate_next_bl_id(tmp_vault, read_counter=read, write_counter=write)
        with lock:
            results.append(bl_id)

    threads = [threading.Thread(target=worker) for _ in range(N)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == N, f"Expected {N} results, got {len(results)}"

    # All IDs must be distinct (no duplicate BL numbers)
    assert len(set(results)) == N, (
        f"Duplicate BL IDs detected: {sorted(results)} — lost-update or duplicate (race!)"
    )

    # IDs must be exactly start+1 … start+N
    assert set(results) == set(range(start + 1, start + N + 1)), (
        f"Expected IDs {set(range(start+1, start+N+1))}, got {set(results)}"
    )

    # Final counter must be start + N
    assert store["value"] == start + N, (
        f"Expected final counter {start + N}, got {store['value']} — lost-update?"
    )


# ─── T3: lock acquire+release bracketing ──────────────────────────────────────

def test_lock_is_acquired_and_released(tmp_vault, counter_store):
    """T3: allocate_next_bl_id acquires and releases the factory lock.

    Strategy: wrap factory_lock.acquire / factory_lock.release with spies
    via monkeypatching the module that backlog_counter_lock imports, then
    verify acquire was called with the correct scope AND release was called
    exactly once afterwards.

    Alternative (if DI-style): pass acquire/release callables — but the
    contract names lock_scope as a keyword param, so factory_lock is the
    expected dependency.  We spy on the module-level functions.
    """
    import backlog_counter_lock as bcl  # noqa — module must exist for spy
    import factory_lock as fl

    acquire_calls = []
    release_calls = []

    original_acquire = fl.acquire
    original_release = fl.release

    def spy_acquire(**kwargs):
        acquire_calls.append(kwargs)
        return original_acquire(**kwargs)

    def spy_release(**kwargs):
        release_calls.append(kwargs)
        return original_release(**kwargs)

    # Patch at the backlog_counter_lock module level (wherever it imported from)
    bcl.acquire = spy_acquire
    bcl.release = spy_release

    store, read, write = counter_store
    store["value"] = 10

    try:
        result = allocate_next_bl_id(
            tmp_vault,
            read_counter=read,
            write_counter=write,
            lock_scope="backlog_counter",
        )
    finally:
        bcl.acquire = original_acquire
        bcl.release = original_release

    assert result == 11

    assert len(acquire_calls) >= 1, "acquire() was never called"
    assert len(release_calls) >= 1, "release() was never called"

    # The scope used for the lock must match the parameter
    acquired_scopes = [c.get("scope", "") for c in acquire_calls]
    assert any("backlog_counter" in s for s in acquired_scopes), (
        f"acquire() not called with scope='backlog_counter', got: {acquired_scopes}"
    )


# ─── T4 (optional): busy lock → defined behaviour (documented expectation) ────

def test_busy_lock_raises_or_retries(tmp_vault, counter_store):
    """T4: when the lock cannot be acquired (held by another worker), allocate_next_bl_id
    either retries until success OR raises a clear exception (LockTimeoutError or similar).

    GREEN-Worker expectation: define and raise a LockTimeoutError (or use a
    timeout parameter with a default) so callers can distinguish 'lock busy'
    from other failures.  The test verifies that the module exports
    LockTimeoutError (or a documented exception type) when the lock is held
    and a very short timeout is used.

    This test documents the expected interface — GREEN-Worker decides the
    exact retry/raise strategy and must make T4 pass.
    """
    import backlog_counter_lock as bcl

    # Verify that the module defines a timeout-related exception
    assert hasattr(bcl, "LockTimeoutError"), (
        "backlog_counter_lock must expose LockTimeoutError for callers "
        "to handle a busy lock (documented expectation for GREEN-Worker)"
    )
