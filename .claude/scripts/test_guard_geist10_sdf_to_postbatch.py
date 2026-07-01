#!/usr/bin/env python3
"""Tests fuer guard_geist10_sdf_to_postbatch.py."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_geist10_sdf_to_postbatch.py"


def run_hook(event, state_file):
    env = os.environ.copy()
    env["OMNI_ENFORCE_GEIST10_GUARD"] = "1"
    env["OMNI_GEIST10_STATE_FILE"] = str(state_file)
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}


def test_arm_on_terminate_write():
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "state.json"
        r = run_hook({"tool_name": "Edit", "tool_input": {"file_path": "/tmp/_manifest.md",
                                                          "new_string": "loopDecision: TERMINATE\n"}}, sf)
        assert r["continue"] is True
        state = json.loads(sf.read_text())
        assert state["expected_postbatch"] is True


def test_postbatch_resets_state():
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "state.json"
        sf.write_text(json.dumps({"expected_postbatch": True, "tool_call_count": 1}))
        r = run_hook({"tool_name": "Skill", "tool_input": {"skill": "_PostBatch_orchestrate"}}, sf)
        assert r["continue"] is True
        state = json.loads(sf.read_text())
        assert state["expected_postbatch"] is False


def test_blocks_after_too_many_tool_calls():
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "state.json"
        sf.write_text(json.dumps({"expected_postbatch": True, "tool_call_count": 2}))
        r = run_hook({"tool_name": "Skill", "tool_input": {"skill": "_BDF_orchestrate"}}, sf)
        assert r["continue"] is False
        assert "GEIST10" in r.get("message", "")


def test_passes_when_not_armed():
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "state.json"
        r = run_hook({"tool_name": "Skill", "tool_input": {"skill": "_IDF_orchestrate"}}, sf)
        assert r["continue"] is True


def test_count_increments():
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "state.json"
        sf.write_text(json.dumps({"expected_postbatch": True, "tool_call_count": 0}))
        r = run_hook({"tool_name": "Skill", "tool_input": {"skill": "_BDF_orchestrate"}}, sf)
        assert r["continue"] is True  # 1 ist noch unter 2
        state = json.loads(sf.read_text())
        assert state["tool_call_count"] == 1


if __name__ == "__main__":
    tests = [test_arm_on_terminate_write, test_postbatch_resets_state, test_blocks_after_too_many_tool_calls,
             test_passes_when_not_armed, test_count_increments]
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
