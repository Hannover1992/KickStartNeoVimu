#!/usr/bin/env python3
"""Tests fuer guard_stab2_phase_order.py."""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_stab2_phase_order.py"


def run_hook(file_path, new_string):
    env = os.environ.copy()
    env["OMNI_ENFORCE_STAB2_GUARD"] = "1"
    event = {"tool_name": "Edit", "tool_input": {"file_path": file_path, "new_string": new_string}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}


def test_correct_sequence_passes():
    content = """phase_3_1_recalibrate: DONE
phase_3_2_postBatch: DONE
phase_3_3_statusTransition: DONE
phase_3_5_modelSync: DONE
"""
    r = run_hook("/tmp/_manifest.md", content)
    assert r["continue"] is True


def test_phase_35_without_31_blocks():
    content = "phase_3_5_modelSync: DONE\n"
    r = run_hook("/tmp/_manifest.md", content)
    assert r["continue"] is False
    assert "STAB2" in r.get("message", "")


def test_modelsync_skip_without_reason_blocks():
    content = """phase_3_1_recalibrate: DONE
phase_3_2_postBatch: DONE
phase_3_3_statusTransition: DONE
phase_3_5_modelSync: SKIP
"""
    r = run_hook("/tmp/_manifest.md", content)
    assert r["continue"] is False
    assert "skip_reason" in r.get("message", "")


def test_modelsync_skip_with_reason_passes():
    content = """phase_3_1_recalibrate: DONE
phase_3_2_postBatch: DONE
phase_3_3_statusTransition: DONE
phase_3_5_modelSync: SKIP
modelSync_skip_reason: twin-mirror pattern, no new model
"""
    r = run_hook("/tmp/_manifest.md", content)
    assert r["continue"] is True


def test_passes_non_manifest_file():
    r = run_hook("/tmp/other.md", "phase_3_5_modelSync: DONE\n")
    assert r["continue"] is True


def test_passes_non_edit_tool():
    proc = subprocess.run([sys.executable, str(GUARD)],
                          input=json.dumps({"tool_name": "Skill", "tool_input": {}}),
                          capture_output=True, text=True)
    r = json.loads(proc.stdout.strip())
    assert r["continue"] is True


if __name__ == "__main__":
    tests = [test_correct_sequence_passes, test_phase_35_without_31_blocks,
             test_modelsync_skip_without_reason_blocks, test_modelsync_skip_with_reason_passes,
             test_passes_non_manifest_file, test_passes_non_edit_tool]
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
