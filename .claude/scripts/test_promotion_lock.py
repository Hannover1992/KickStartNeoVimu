"""
test_promotion_lock.py — BL-320 batch_PL1: RED tests for the PT/SL Promotion-Mutex.

GOLD-Contract (PL-320-1 Code-Portion + PL-320-3 Stale-Recovery):
  A thin promotion-lock wrapper that REUSES factory_lock's mkdir-mechanic
  (acquire_bl/release_bl on BL_PT_PROMOTION_LOCK_DIR / bl_id="_pt_promotion") so that
  two parallel batches never promote into the same Library simultaneously, and a
  dead worker's lock is reclaimed via is_bl_stale (no dead-lock).

Expected GREEN API (in factory_lock.py — additive, factory_lock is CONSUMED not changed):
  - acquire_promotion_lock(worker_id, ttl=600, vault_root=None, phase="promote") -> bool
        Reuses acquire_bl(bl_id="_pt_promotion", ...). True on success, False if held (non-stale).
  - release_promotion_lock(worker_id, vault_root=None) -> bool
        Reuses release_bl(bl_id="_pt_promotion", ...). True if released, False if not owner.
  - promotion_lock(worker_id, ttl=600, vault_root=None, phase="promote")  [context manager]
        acquire on __enter__ / release on __exit__ (convenience for the skill-seam).

These tests are RED until the wrapper exists (greenfield import -> AttributeError / no wrapper).
factory_lock.py is CONSUMED, NOT modified -> test_factory_lock.py stays green.

Run: py -3 -m pytest .claude/scripts/test_promotion_lock.py -q
"""

import sys
import time
import threading
from pathlib import Path

import pytest

# Add scripts dir to path (mirror test_factory_lock.py)
sys.path.insert(0, str(Path(__file__).parent))

import factory_lock as fl


# ─── Fixtures (mirror test_factory_lock.py isolation) ─────────────────────────

@pytest.fixture
def tmp_vault(tmp_path):
    """Provide a temporary vault root for isolation (no real .locks/ IO)."""
    return tmp_path


@pytest.fixture(autouse=True)
def patch_vault(tmp_vault, monkeypatch):
    """Patch VAULT_ROOT to tmp dir + no-op _emit_audit to avoid audit side effects."""
    monkeypatch.setattr(fl, "VAULT_ROOT", tmp_vault)
    monkeypatch.setattr(fl, "_emit_audit", lambda *a, **kw: None)
    yield


# ─── Test 1: exclusive — second acquire blocked while held ────────────────────

def test_promotion_lock_exclusive(tmp_vault):
    """acquire by w1 -> second acquire (w2) while held is rejected (mutex holds)."""
    ok1 = fl.acquire_promotion_lock(worker_id="pt-w1", vault_root=tmp_vault)
    assert ok1 is True

    ok2 = fl.acquire_promotion_lock(worker_id="sl-w2", vault_root=tmp_vault)
    assert ok2 is False, "Second concurrent promotion acquired the lock — mutex violated"


# ─── Test 2: release then re-acquirable ───────────────────────────────────────

def test_promotion_lock_release_reacquirable(tmp_vault):
    """acquire -> release -> re-acquire succeeds (lock fully freed)."""
    assert fl.acquire_promotion_lock(worker_id="pt-w1", vault_root=tmp_vault) is True
    assert fl.release_promotion_lock(worker_id="pt-w1", vault_root=tmp_vault) is True

    ok = fl.acquire_promotion_lock(worker_id="sl-w2", vault_root=tmp_vault)
    assert ok is True, "Lock not re-acquirable after release"
    # cleanup
    fl.release_promotion_lock(worker_id="sl-w2", vault_root=tmp_vault)


# ─── Test 3: stale lock reclaimed (AK-3 in promotion context) ─────────────────

def test_promotion_lock_stale_reclaimed(tmp_vault):
    """A stale promotion-lock (heartbeat older than BL_LOCK_STALE_SECONDS) is reclaimed
    by the next acquire (rmtree + remkdir) — no dead-lock on worker death."""
    # First worker grabs the promotion lock.
    assert fl.acquire_promotion_lock(worker_id="dead-pt-w1", vault_root=tmp_vault) is True

    # Simulate worker death: backdate the heartbeat far beyond the stale threshold.
    lock_dir = fl._bl_lock_dir("_pt_promotion", vault_root=tmp_vault)
    assert lock_dir.exists(), "Promotion lock dir not created on acquire"
    hb = lock_dir / "heartbeat.txt"
    stale_ts = fl._now_iso()  # placeholder; overwritten below with backdated value
    from datetime import datetime, timezone, timedelta
    old = datetime.now(timezone.utc) - timedelta(seconds=fl.BL_LOCK_STALE_SECONDS + 60)
    hb.write_text(old.strftime("%Y-%m-%dT%H:%M:%SZ"), encoding="utf-8")
    assert stale_ts  # silence lints; not load-bearing

    # The promotion lock is now stale -> a fresh acquire must reclaim it.
    ok = fl.acquire_promotion_lock(worker_id="live-sl-w2", vault_root=tmp_vault)
    assert ok is True, "Stale promotion lock was not reclaimed -> dead-lock"
    # New owner owns it.
    owner = (lock_dir / "owner.txt").read_text(encoding="utf-8").strip()
    assert owner == "live-sl-w2"
    fl.release_promotion_lock(worker_id="live-sl-w2", vault_root=tmp_vault)


# ─── Test 4: PT + SL share ONE promotion lock (serialize against each other) ───

def test_pt_sl_share_one_lock(tmp_vault):
    """Node: 'two parallel batches never promote into the same Library' -> ONE shared lock.
    A PT-promoter and an SL-promoter must serialize against each other (same lock dir)."""
    # PT acquires.
    assert fl.acquire_promotion_lock(worker_id="PT-promoter", vault_root=tmp_vault) is True
    # SL (different worker / different library) must be blocked by the same lock.
    ok_sl = fl.acquire_promotion_lock(worker_id="SL-promoter", vault_root=tmp_vault)
    assert ok_sl is False, "PT and SL did not share one lock — they could promote concurrently"

    # The lock dir is the single canonical promotion lock (_pt_promotion).
    expected = fl._bl_lock_dir("_pt_promotion", vault_root=tmp_vault)
    assert expected.exists()
    fl.release_promotion_lock(worker_id="PT-promoter", vault_root=tmp_vault)


# ─── Test 5: context-manager convenience (skill-seam shape) ───────────────────

def test_promotion_lock_context_manager(tmp_vault):
    """promotion_lock(...) context manager acquires on enter, releases on exit —
    the shape the _PT_/_SL_promoteFromPL Phase 1/8 skill-seam will call."""
    with fl.promotion_lock(worker_id="ctx-w1", vault_root=tmp_vault):
        # Inside the block the lock is held -> a competing acquire is rejected.
        assert fl.acquire_promotion_lock(worker_id="other-w2", vault_root=tmp_vault) is False
    # After the block the lock is released -> re-acquirable.
    assert fl.acquire_promotion_lock(worker_id="after-w3", vault_root=tmp_vault) is True
    fl.release_promotion_lock(worker_id="after-w3", vault_root=tmp_vault)


# ─── AK-4: Forward-Verify Concurrency-Proof ───────────────────────────────────
# The 5 tests above are SEQUENTIAL (acquire, then a second acquire) — they prove
# the try-lock semantics but NOT serialization under real competing threads.
# AK-4 demands the actual concurrency proof: 2+ simultaneous promotions must
# serialize (0 lost updates, mutual exclusion held throughout).

# Concurrency-test knobs (sleep window + retry/backoff + wall-clock guard).
_AK4_N_THREADS = 8
_AK4_SECTION_SLEEP = 0.005   # widen the interleaving window inside the crit-section
_AK4_RETRY_SLEEP = 0.002     # base backoff between failed (non-blocking) acquires
_AK4_WALL_CLOCK_TIMEOUT = 10.0  # per-test wall-clock guard so a bug can't hang forever


def _run_promotion_workers(acquire_fn, release_fn, vault_root, n=_AK4_N_THREADS):
    """Drive `n` threads, each performing exactly ONE promotion (a read-modify-write
    on a shared counter) guarded by the supplied acquire/release functions.

    Returns dict with:
      counter        — final value of the shared counter (== n iff 0 lost updates)
      results        — list of per-thread post-increment snapshots (len == n iff all ran)
      max_concurrent — peak observed simultaneous occupancy of the critical section
      errors         — list of (worker_id, exception-repr) for any thread that blew up
      timed_out      — True if any thread hit the wall-clock guard without promoting

    Designed so the SAME body runs with the real mutex and with a no-op lock — the
    only difference being which acquire/release is injected (discriminating proof).
    """
    shared = {"counter": 0}          # the simulated Library-write
    results = []
    occupancy = {"current": 0, "max": 0}
    errors = []
    timed_out = threading.Event()

    # Plain (unprotected) state guards — these are NOT the promotion mutex.
    # They only make our *measurement* of occupancy/results thread-safe, so that a
    # broken promotion-mutex shows up as max_concurrent>1 / lost-updates rather than
    # as a corrupt measurement. The Library-write itself stays unprotected on purpose.
    occ_lock = threading.Lock()
    res_lock = threading.Lock()

    barrier = threading.Barrier(n)   # release all threads at once -> real contention

    def worker(i):
        wid = f"w{i}"
        try:
            barrier.wait(timeout=_AK4_WALL_CLOCK_TIMEOUT)
        except threading.BrokenBarrierError:
            timed_out.set()
            return

        deadline = time.monotonic() + _AK4_WALL_CLOCK_TIMEOUT
        attempt = 0
        while True:
            if time.monotonic() > deadline:
                timed_out.set()
                return
            got = acquire_fn(worker_id=wid, vault_root=vault_root)
            if got:
                break
            # Non-blocking try-lock: loser backs off and retries -> demonstrates
            # SERIALIZATION (waiters eventually get their turn).
            attempt += 1
            time.sleep(_AK4_RETRY_SLEEP * (1 + (attempt % 5)))

        try:
            # ── critical section: simulated Library read-modify-write ──
            with occ_lock:
                occupancy["current"] += 1
                if occupancy["current"] > occupancy["max"]:
                    occupancy["max"] = occupancy["current"]

            local = shared["counter"]          # READ
            time.sleep(_AK4_SECTION_SLEEP)      # widen lost-update window
            shared["counter"] = local + 1       # MODIFY-WRITE
            with res_lock:
                results.append(shared["counter"])

            with occ_lock:
                occupancy["current"] -= 1
            # ── end critical section ──
        finally:
            release_fn(worker_id=wid, vault_root=vault_root)

    threads = [threading.Thread(target=worker, args=(i,), name=f"ak4-w{i}")
               for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=_AK4_WALL_CLOCK_TIMEOUT + 5.0)

    # Any still-alive thread means we hung — surface it as a timeout.
    if any(t.is_alive() for t in threads):
        timed_out.set()

    return {
        "counter": shared["counter"],
        "results": results,
        "max_concurrent": occupancy["max"],
        "errors": errors,
        "timed_out": timed_out.is_set(),
    }


def test_concurrent_promotions_serialize_zero_lost_updates(tmp_vault):
    """N real threads each do ONE guarded promotion concurrently. The promotion
    mutex must serialize them: mutual exclusion holds (max_concurrent == 1) and no
    read-modify-write is lost (final counter == N, all N results recorded)."""
    out = _run_promotion_workers(
        fl.acquire_promotion_lock,
        fl.release_promotion_lock,
        vault_root=tmp_vault,
        n=_AK4_N_THREADS,
    )

    assert not out["timed_out"], (
        "Concurrency test hit the wall-clock guard — a thread never promoted "
        "(possible dead-lock / serialization bug)"
    )
    assert out["errors"] == [], f"Worker(s) raised: {out['errors']}"
    assert out["max_concurrent"] == 1, (
        f"Mutual exclusion violated — {out['max_concurrent']} workers were inside the "
        f"critical section simultaneously (expected exactly 1)"
    )
    assert out["counter"] == _AK4_N_THREADS, (
        f"Lost update — final counter {out['counter']} != {_AK4_N_THREADS} "
        f"(a read-modify-write was clobbered)"
    )
    assert len(out["results"]) == _AK4_N_THREADS, (
        f"Only {len(out['results'])}/{_AK4_N_THREADS} promotions recorded"
    )


def test_concurrency_test_is_discriminating(tmp_vault, monkeypatch):
    """RED-capability proof: if the mutex is bypassed (no-op lock), the SAME body
    MUST lose serialization — either max_concurrent>1 or lost-updates appear.

    This guarantees the green run above is meaningful (the mutex actually does the
    work) and not tautological (the body would pass even without a lock).

    The interleaving is timing-dependent, so we run several rounds and assert that
    AT LEAST ONE round exhibits a mutex-property violation."""
    noop_acquire = lambda *a, **k: True
    noop_release = lambda *a, **k: True

    rounds = 5
    violations = []
    for r in range(rounds):
        out = _run_promotion_workers(
            noop_acquire,
            noop_release,
            vault_root=tmp_vault,
            n=_AK4_N_THREADS,
        )
        mutual_exclusion_broke = out["max_concurrent"] > 1
        lost_update = out["counter"] != _AK4_N_THREADS
        if mutual_exclusion_broke or lost_update:
            violations.append({
                "round": r,
                "max_concurrent": out["max_concurrent"],
                "counter": out["counter"],
                "lost_updates": _AK4_N_THREADS - out["counter"],
            })

    assert violations, (
        f"Discriminating-test FAILED: across {rounds} rounds with a NO-OP lock, "
        f"serialization never broke (no max_concurrent>1, no lost-updates). "
        f"The concurrency test would pass even without a real mutex -> tautological."
    )
    # We deliberately do NOT use monkeypatch on the module functions (we inject the
    # no-op directly), so this fixture param is unused — referenced to silence lints.
    _ = monkeypatch
