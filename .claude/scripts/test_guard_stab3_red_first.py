#!/usr/bin/env python3
"""Tests fuer guard_stab3_red_first.py."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_stab3_red_first.py"


def run_hook(file_path, state, modus="M3", pragmatik=False):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(state, f)
        sf = f.name
    env = os.environ.copy()
    env["OMNI_ENFORCE_STAB3_GUARD"] = "1"
    env["OMNI_STAB3_STATE_FILE"] = sf
    env["OMNI_STAB3_MODUS_OVERRIDE"] = modus
    if pragmatik:
        env["OMNI_STAB3_PRAGMATIK"] = "1"
    event = {"tool_name": "Edit", "tool_input": {"file_path": file_path, "new_string": "code"}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    Path(sf).unlink(missing_ok=True)
    return result


def test_m3_with_recent_test_edit_passes():
    state = {"recent_edits": [{"path": "/x/foo.spec.ts"}, {"path": "/x/bar.ts"}]}
    r = run_hook("/x/foo.ts", state, "M3")
    assert r["continue"] is True


def test_m3_without_test_edit_blocks():
    state = {"recent_edits": [{"path": "/x/a.ts"}, {"path": "/x/b.ts"}]}
    r = run_hook("/x/foo.ts", state, "M3")
    assert r["continue"] is False
    assert "STAB3" in r.get("message", "")


def test_m2_skips_check():
    state = {"recent_edits": []}
    r = run_hook("/x/foo.ts", state, "M2")
    assert r["continue"] is True


def test_markdown_edit_passes():
    state = {"recent_edits": []}
    r = run_hook("/x/foo.md", state, "M3")
    assert r["continue"] is True


def test_pragmatik_override_warn():
    state = {"recent_edits": [{"path": "/x/a.ts"}]}
    r = run_hook("/x/foo.ts", state, "M3", pragmatik=True)
    assert r["continue"] is True


def test_test_file_edit_passes():
    """Edit auf spec.ts selbst soll nicht blocken (Test wird gerade geschrieben)."""
    state = {"recent_edits": []}
    r = run_hook("/x/foo.spec.ts", state, "M3")
    assert r["continue"] is True


if __name__ == "__main__":
    tests = [test_m3_with_recent_test_edit_passes, test_m3_without_test_edit_blocks,
             test_m2_skips_check, test_markdown_edit_passes, test_pragmatik_override_warn,
             test_test_file_edit_passes]
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
    print(f"\n=== {passed}/{passed+failed} ===")
    sys.exit(0 if failed == 0 else 1)
