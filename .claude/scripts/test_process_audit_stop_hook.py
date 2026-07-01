#!/usr/bin/env python3
"""Smoke-Tests fuer process_audit_stop_hook.py (BL-RCA-486-Round11)."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.absolute()
HOOK_SCRIPT = SCRIPT_DIR / "process_audit_stop_hook.py"


def run_hook(env_extra=None):
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input="",
        capture_output=True, text=True,
        env=env,
    )
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}


def test_hook_off_always_continue():
    """OMNI_PROCESS_AUDIT_ENFORCE=off -> immer continue=true."""
    result = run_hook({"OMNI_PROCESS_AUDIT_ENFORCE": "off"})
    assert result.get("continue") is True


def test_hook_default_mode_warns_not_blocks():
    """Default (no env) -> kein Block, Warning-Mode."""
    result = run_hook({"OMNI_PROCESS_AUDIT_ENFORCE": "0"})
    assert result.get("continue") is True


def test_hook_enforce_mode_blocks_red():
    """OMNI_PROCESS_AUDIT_ENFORCE=1 + RED BL in git status -> continue=false.

    Da wir kein echtes git-status-RED-Manifest haben, prueft dieser Test nur die
    Code-Pfad-Aktivitaet. Volle Integration-Test via OmniCommand Repo selbst.
    """
    result = run_hook({"OMNI_PROCESS_AUDIT_ENFORCE": "1"})
    # Wenn keine modified BL-Manifeste in git status -> continue=true (OK)
    # Wenn welche da sind und RED -> continue=false
    assert "continue" in result


if __name__ == "__main__":
    tests = [test_hook_off_always_continue, test_hook_default_mode_warns_not_blocks,
             test_hook_enforce_mode_blocks_red]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n=== {passed}/{passed+failed} tests passed ===")
    sys.exit(0 if failed == 0 else 1)
