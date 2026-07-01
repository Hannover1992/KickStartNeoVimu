#!/usr/bin/env python3
"""Tests fuer guard_param_writer_identity.py + manifest_dedup.py self-test."""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_param_writer_identity.py"


def run_guard(file_path, new_text, active_skill, tool="Write"):
    env = os.environ.copy()
    env["OMNI_PARAM_ACTIVE_SKILL"] = active_skill if active_skill is not None else ""
    ti = {"file_path": file_path}
    if tool == "Write":
        ti["content"] = new_text
    else:
        ti["new_string"] = new_text
    event = {"tool_name": tool, "tool_input": ti}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}


def test_sdf_blocked_on_manifest_globals():
    """SDF-Skill aktiv + GLOBAL_CEILING-Write → BLOCK."""
    r = run_guard("/x/_manifest.md", "**GLOBAL_CEILING:** sonnet\n", "_SDF_orchestrate")
    assert r["continue"] is False
    assert "PARAM_WRITER_IDENTITY" in r.get("message", "")


def test_param_allowed_on_manifest_globals():
    """/_param aktiv + GLOBAL_CEILING-Write → ALLOW (auch Upgrade)."""
    r = run_guard("/x/_manifest.md", "**GLOBAL_CEILING:** opus\n", "_param")
    assert r["continue"] is True


def test_human_direct_allowed():
    """Kein Skill aktiv (Human-Direct) → ALLOW."""
    r = run_guard("/x/_session_params.md", "**ceiling:** opus\n", None)
    assert r["continue"] is True


def test_sdf_blocked_on_session_params():
    """SDF aktiv + _session_params.md ceiling-Write → BLOCK."""
    r = run_guard("/x/_session_params.md", "**ceiling:** sonnet\n", "_SDF_orchestrate")
    assert r["continue"] is False


def test_idf_blocked_on_global_difficulty():
    """IDF aktiv + GLOBAL_DIFFICULTY-Write → BLOCK."""
    r = run_guard("/x/_manifest.md", "**GLOBAL_DIFFICULTY:** normal\n", "_IDF_orchestrate")
    assert r["continue"] is False


def test_non_param_manifest_write_passthrough():
    """SDF aktiv aber KEIN Param-Feld (anderer Manifest-Content) → ALLOW."""
    r = run_guard("/x/_manifest.md", "## DF_BATCH_STATE\nbatch_items: [x]\n", "_SDF_orchestrate")
    assert r["continue"] is True


def test_backlog_allowed():
    """/_backlog aktiv → ALLOW (autorisierter Writer)."""
    r = run_guard("/x/_manifest.md", "**GLOBAL_FLOOR:** sonnet\n", "_backlog")
    assert r["continue"] is True


def test_other_file_passthrough():
    """SDF aktiv + GLOBAL_CEILING aber andere Datei → ALLOW (nur params-files geschuetzt)."""
    r = run_guard("/x/random.md", "**GLOBAL_CEILING:** sonnet\n", "_SDF_orchestrate")
    assert r["continue"] is True


def test_override_off():
    """OMNI_PARAM_WRITER_OFF=1 → ALLOW trotz SDF."""
    env = os.environ.copy()
    env["OMNI_PARAM_ACTIVE_SKILL"] = "_SDF_orchestrate"
    env["OMNI_PARAM_WRITER_OFF"] = "1"
    event = {"tool_name": "Write", "tool_input": {"file_path": "/x/_manifest.md", "content": "**GLOBAL_CEILING:** sonnet\n"}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    r = json.loads(proc.stdout.strip())
    assert r["continue"] is True


if __name__ == "__main__":
    tests = [test_sdf_blocked_on_manifest_globals, test_param_allowed_on_manifest_globals,
             test_human_direct_allowed, test_sdf_blocked_on_session_params,
             test_idf_blocked_on_global_difficulty, test_non_param_manifest_write_passthrough,
             test_backlog_allowed, test_other_file_passthrough, test_override_off]
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
