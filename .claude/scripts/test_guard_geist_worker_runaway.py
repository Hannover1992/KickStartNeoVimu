#!/usr/bin/env python3
"""Tests fuer guard_geist_worker_runaway.py — 3 adversarielle Lenses inline.
LENS1 catch-runaway, LENS2 no-false-positive, LENS3 cross-platform.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_geist_worker_runaway.py"


def run(agent_name, new_content, file_path="/x/_manifest.md", tool="Write", off=False):
    env = os.environ.copy()
    env["OMNI_ENFORCE_WORKER_RUNAWAY"] = "1"
    if agent_name is None:
        env.pop("OMNI_AGENT_NAME", None)
    else:
        env["OMNI_AGENT_NAME"] = agent_name
    if off:
        env["OMNI_WORKER_RUNAWAY_OFF"] = "1"
    ti = {"file_path": file_path}
    ti["content" if tool == "Write" else "new_string"] = new_content
    ev = {"tool_name": tool, "tool_input": ti}
    p = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(ev),
                       capture_output=True, text=True, env=env)
    return json.loads(p.stdout.strip()) if p.stdout.strip() else {}


# ── LENS 1: catch-runaway (der echte Round-17-Drift) ──
def test_resumeguard_writes_batchplan_blocked():
    r = run("idf-resumeGuard-r17", "## BERATER_OUTPUTS_batchPlan_round17\nexit_code: 0\n")
    assert r["continue"] is False, r

def test_resumeguard_writes_finalsummary_blocked():
    r = run("idf-resumeGuard-r17", "## BERATER_OUTPUTS_finalSummary_round17\nexit_code: 0\n")
    assert r["continue"] is False, r

def test_resumeguard_writes_stageplanner_blocked():
    r = run("idf-resumeGuard-r17", "## BERATER_OUTPUTS_stagePlanner_round17\n")
    assert r["continue"] is False, r

def test_runaway_multiblock_one_foreign_blocked():
    c = "## BERATER_OUTPUTS_resumeGuard_round17\nok\n## BERATER_OUTPUTS_metricPlanner_round17\nok\n"
    r = run("idf-resumeGuard-r17", c)
    assert r["continue"] is False, r


# ── LENS 2: no-false-positive (legitime Worker) ──
def test_resumeguard_writes_own_phase_allowed():
    r = run("idf-resumeGuard-r17", "## BERATER_OUTPUTS_resumeGuard_round17\nexit_code: 0\n")
    assert r["continue"] is True, r

def test_validator_writes_validator_allowed():
    r = run("idf-validator-r17", "## BERATER_OUTPUTS_validator_round17\nexit_code: 1\n")
    assert r["continue"] is True, r

def test_batchplan_worker_writes_batchplan_allowed():
    r = run("idf-batchPlan-r17", "## BERATER_OUTPUTS_batchPlan_round17\n")
    assert r["continue"] is True, r

def test_team_lead_no_agent_name_allowed():
    r = run(None, "## BERATER_OUTPUTS_finalSummary_round17\n")
    assert r["continue"] is True, r

def test_modelsync_dot_variant_allowed():
    r = run("idf-modelSync-r17", "## BERATER_OUTPUTS.modelSync\nok\n")
    assert r["continue"] is True, r

def test_no_substring_collision_blocks():
    # role 'postItem' schreibt 'post_sc_pl_resync' → normalize: 'postitem' vs 'postscplresync'
    # weder enthaelt den anderen → BLOCK (kein false-allow durch Teilstring)
    r = run("sdf-postItem", "## BERATER_OUTPUTS_post_sc_pl_resync_round17\n")
    assert r["continue"] is False, r


# ── LENS 3 + Struktur: passthrough + override ──
def test_manifest_non_berater_passthrough():
    r = run("idf-resumeGuard-r17", "## DF_BATCH_STATE\nbatch_items: [x]\n")
    assert r["continue"] is True, r

def test_other_file_passthrough():
    r = run("idf-resumeGuard-r17", "## BERATER_OUTPUTS_batchPlan_round17\n", file_path="/x/random.md")
    assert r["continue"] is True, r

def test_override_off_allows_runaway():
    r = run("idf-resumeGuard-r17", "## BERATER_OUTPUTS_batchPlan_round17\n", off=True)
    assert r["continue"] is True, r

def test_non_edit_tool_passthrough():
    p = subprocess.run([sys.executable, str(GUARD)],
                       input=json.dumps({"tool_name": "Skill", "tool_input": {}}),
                       capture_output=True, text=True)
    assert json.loads(p.stdout.strip())["continue"] is True


if __name__ == "__main__":
    import inspect
    tests = [obj for name, obj in sorted(globals().items())
             if name.startswith("test_") and callable(obj)]
    passed = failed = 0
    for t in tests:
        try:
            t(); print(f"[PASS] {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}"); failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}"); failed += 1
    print(f"\n=== {passed}/{passed+failed} ===")
    sys.exit(0 if failed == 0 else 1)
