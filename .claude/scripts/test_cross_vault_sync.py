#!/usr/bin/env python3
"""BL-196: Tests fuer cross_vault_sync.py (Skeleton-Level)."""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


def run_cv(args):
    cmd = [sys.executable, str(SCRIPT_DIR / "cross_vault_sync.py")] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def test_t1_register_two_vaults():
    """T1: zwei Vaults registrieren in shared sync_root."""
    with tempfile.TemporaryDirectory() as sync_root:
        r1 = run_cv(["register", "--sync-root", sync_root,
                     "--vault-id", "vault-A", "--vault-path", "/tmp/vault-A"])
        r2 = run_cv(["register", "--sync-root", sync_root,
                     "--vault-id", "vault-B", "--vault-path", "/tmp/vault-B"])
        assert r1.returncode == 0
        assert r2.returncode == 0
        assert (Path(sync_root) / "cross_vault_index.json").exists()
    print("[T1] PASS: register two vaults")


def test_t2_acquire_bl_lock():
    """T2: Vault A acquire BL-Lock."""
    with tempfile.TemporaryDirectory() as sync_root:
        run_cv(["register", "--sync-root", sync_root, "--vault-id", "A", "--vault-path", "/tmp/a"])
        r = run_cv(["acquire-bl", "--sync-root", sync_root, "--bl-id", "BL-196", "--vault-id", "A"])
        assert r.returncode == 0
        lock_file = Path(sync_root) / "locks" / "BL-196.lock"
        assert lock_file.exists()
    print("[T2] PASS: acquire bl lock")


def test_t3_conflict_detection():
    """T3: Vault B kann nicht acquiren wenn Vault A haelt."""
    with tempfile.TemporaryDirectory() as sync_root:
        run_cv(["register", "--sync-root", sync_root, "--vault-id", "A", "--vault-path", "/tmp/a"])
        run_cv(["register", "--sync-root", sync_root, "--vault-id", "B", "--vault-path", "/tmp/b"])
        run_cv(["acquire-bl", "--sync-root", sync_root, "--bl-id", "BL-196", "--vault-id", "A"])
        r = run_cv(["acquire-bl", "--sync-root", sync_root, "--bl-id", "BL-196", "--vault-id", "B"])
        assert r.returncode == 2, f"Expected conflict (rc=2), got {r.returncode}"
        assert "CONFLICT" in r.stderr or "CONFLICT" in r.stdout
    print("[T3] PASS: conflict detection")


def test_t4_release_then_reacquire():
    """T4: Vault A released, Vault B kann acquiren."""
    with tempfile.TemporaryDirectory() as sync_root:
        run_cv(["register", "--sync-root", sync_root, "--vault-id", "A", "--vault-path", "/tmp/a"])
        run_cv(["register", "--sync-root", sync_root, "--vault-id", "B", "--vault-path", "/tmp/b"])
        run_cv(["acquire-bl", "--sync-root", sync_root, "--bl-id", "BL-196", "--vault-id", "A"])
        r1 = run_cv(["release-bl", "--sync-root", sync_root, "--bl-id", "BL-196", "--vault-id", "A"])
        assert r1.returncode == 0
        r2 = run_cv(["acquire-bl", "--sync-root", sync_root, "--bl-id", "BL-196", "--vault-id", "B"])
        assert r2.returncode == 0
    print("[T4] PASS: release then reacquire")


def test_t5_release_foreign_lock_refused():
    """T5: Vault B kann nicht Vault A's Lock releasen."""
    with tempfile.TemporaryDirectory() as sync_root:
        run_cv(["register", "--sync-root", sync_root, "--vault-id", "A", "--vault-path", "/tmp/a"])
        run_cv(["register", "--sync-root", sync_root, "--vault-id", "B", "--vault-path", "/tmp/b"])
        run_cv(["acquire-bl", "--sync-root", sync_root, "--bl-id", "BL-196", "--vault-id", "A"])
        r = run_cv(["release-bl", "--sync-root", sync_root, "--bl-id", "BL-196", "--vault-id", "B"])
        assert r.returncode == 3, f"Expected refuse (rc=3), got {r.returncode}"
    print("[T5] PASS: foreign release refused")


def main():
    tests = [test_t1_register_two_vaults, test_t2_acquire_bl_lock,
             test_t3_conflict_detection, test_t4_release_then_reacquire,
             test_t5_release_foreign_lock_refused]
    passed = failed = 0
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
    print(f"\n=== {passed}/{passed+failed} tests passed ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
