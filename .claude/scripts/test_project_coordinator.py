#!/usr/bin/env python3
"""
BL-194: Tests fuer project_coordinator.py (Default BCCD).
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from concurrency_test_helpers import temp_vault


def run_pc(args):
    """Helper: run project_coordinator.py with args."""
    cmd = [sys.executable, str(SCRIPT_DIR / "project_coordinator.py")] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def test_t1_register():
    """T1: register worktree."""
    with temp_vault() as ctx:
        result = run_pc(["register", "--vault-root", str(ctx["vault_root"]),
                         "--worktree", "/tmp/wt0"])
        assert result.returncode == 0, f"register failed: {result.stderr}"
        # Check state file exists
        state_file = Path(ctx["vault_root"]) / ".coordinator_state" / "coordinator.json"
        assert state_file.exists()
    print("[T1] PASS: register worktree")


def test_t2_allocate():
    """T2: allocate BL to worktree."""
    with temp_vault() as ctx:
        run_pc(["register", "--vault-root", str(ctx["vault_root"]), "--worktree", "/tmp/wt0"])
        result = run_pc(["allocate", "--vault-root", str(ctx["vault_root"]),
                         "--bl-id", "BL-194", "--worktree", "/tmp/wt0"])
        assert result.returncode == 0, f"allocate failed: {result.stderr}"
    print("[T2] PASS: allocate BL")


def test_t3_status():
    """T3: status command."""
    with temp_vault() as ctx:
        run_pc(["register", "--vault-root", str(ctx["vault_root"]), "--worktree", "/tmp/wt0"])
        run_pc(["allocate", "--vault-root", str(ctx["vault_root"]),
                "--bl-id", "BL-194", "--worktree", "/tmp/wt0"])
        result = run_pc(["status", "--vault-root", str(ctx["vault_root"])])
        assert result.returncode == 0
        assert "BL-194" in result.stdout
        assert "Worktrees (1)" in result.stdout
    print("[T3] PASS: status command")


def test_t4_daemon_one_iter():
    """T4: daemon mit max-iter=1 (kein Endlos-Loop)."""
    with temp_vault() as ctx:
        result = run_pc(["daemon", "--vault-root", str(ctx["vault_root"]), "--max-iter", "1"])
        # daemon liest state, machte 1 iteration, exit 0
        assert result.returncode == 0, f"daemon failed: {result.stderr}"
    print("[T4] PASS: daemon one-iter")


def main():
    tests = [test_t1_register, test_t2_allocate, test_t3_status, test_t4_daemon_one_iter]
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
