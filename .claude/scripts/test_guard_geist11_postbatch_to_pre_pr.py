#!/usr/bin/env python3
"""Tests fuer guard_geist11_postbatch_to_pre_pr.py."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_geist11_postbatch_to_pre_pr.py"


def run_hook(event, state_file):
    env = os.environ.copy()
    env["OMNI_ENFORCE_GEIST11_GUARD"] = "1"
    env["OMNI_GEIST11_STATE_FILE"] = str(state_file)
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}


def test_arm_on_batch_done():
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "state.json"
        r = run_hook({"tool_name": "Edit", "tool_input": {
            "file_path": "/tmp/_manifest.md",
            "new_string": "batch_done: true\nbdf_all_items_done: true\n"}}, sf)
        assert r["continue"] is True
        state = json.loads(sf.read_text())
        assert state["expected_pre_pr"] is True


def test_pre_pr_resets_state():
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "state.json"
        sf.write_text(json.dumps({"expected_pre_pr": True, "tool_call_count": 2}))
        r = run_hook({"tool_name": "Skill", "tool_input": {"skill": "_Pre_PR_orchestrate"}}, sf)
        assert r["continue"] is True
        state = json.loads(sf.read_text())
        assert state["expected_pre_pr"] is False


def test_blocks_after_too_many_tool_calls():
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "state.json"
        sf.write_text(json.dumps({"expected_pre_pr": True, "tool_call_count": 3}))
        r = run_hook({"tool_name": "Skill", "tool_input": {"skill": "_BDF_orchestrate"}}, sf)
        assert r["continue"] is False
        assert "GEIST11" in r.get("message", "")


def test_passes_when_not_armed():
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "state.json"
        r = run_hook({"tool_name": "Skill", "tool_input": {"skill": "_IDF_orchestrate"}}, sf)
        assert r["continue"] is True


def test_only_batch_done_no_all_items_no_arm():
    with tempfile.TemporaryDirectory() as td:
        sf = Path(td) / "state.json"
        r = run_hook({"tool_name": "Edit", "tool_input": {
            "file_path": "/tmp/_manifest.md",
            "new_string": "batch_done: true\n"}}, sf)
        assert r["continue"] is True
        # State should NOT arm (need both conditions)
        if sf.exists():
            state = json.loads(sf.read_text())
            assert state.get("expected_pre_pr", False) is False


if __name__ == "__main__":
    tests = [test_arm_on_batch_done, test_pre_pr_resets_state, test_blocks_after_too_many_tool_calls,
             test_passes_when_not_armed, test_only_batch_done_no_all_items_no_arm]
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
