#!/usr/bin/env python3
"""Tests fuer guard_geist9b_sdf_post_inline.py."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_geist9b_sdf_post_inline.py"


def run_guard(file_path, new_text, audit_lines, warn_optout=False):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for line in audit_lines:
            f.write(json.dumps(line) + "\n")
        audit_path = f.name
    # Deterministisch enforceProcess=true (Gate aktiv) — sonst koennte ein false-Repo-Param
    # den Guard frueh durchlassen. BLOCK ist seit 2026-05-29 Default sobald der Gate aktiv ist.
    with tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8") as sp:
        sp.write("**enforceProcess:** true\n")
        sp_path = sp.name
    env = os.environ.copy()
    env["OMNI_GEIST9B_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    if warn_optout:
        env["OMNI_GEIST9B_ENFORCE"] = "0"   # expliziter Debug-Opt-out -> WARN statt BLOCK
    event = {"tool_name": "Edit", "tool_input": {"file_path": file_path, "new_string": new_text}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}


def test_pl_done_inline_blocked():
    """PL [ ]→[x] nach I-Pipeline OHNE _SDF_orchestrate_post → BLOCK (enforce)."""
    audit = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]
    r = run_guard("/x/6_PL/parking-lot.md", "### [x] PL-FE-FOLLOWUP-UJ-FOO DONE\n", audit)
    assert r["continue"] is False
    assert "GEIST9B" in r.get("message", "")


def test_pl_done_with_post_allowed():
    """PL [x] nach I-Pipeline + _SDF_orchestrate_post lief → ALLOW (legit Phase 3)."""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
    ]
    r = run_guard("/x/6_PL/parking-lot.md", "### [x] PL-FE-FOLLOWUP-UJ-FOO DONE\n", audit)
    assert r["continue"] is True


def test_completed_batches_inline_blocked():
    """completed_round16_batches Append ohne _SDF_orchestrate_post → BLOCK."""
    audit = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]
    r = run_guard("/x/_manifest.md", "completed_round16_batches: [B1_build_green]\n", audit)
    assert r["continue"] is False


def test_no_i_pipeline_passthrough():
    """Keine I-Pipeline gelaufen → PL-Edit legit (z.B. IDF schreibt PLs)."""
    audit = [{"event": "SKILL_LOAD", "skill_name": "_IDF_orchestrate"}]
    r = run_guard("/x/6_PL/parking-lot.md", "### [x] PL-FOO\n", audit)
    assert r["continue"] is True


def test_non_completion_pl_edit_passthrough():
    """PL-Edit ohne [x]-Transition (z.B. neues [ ] Item) → ALLOW."""
    audit = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]
    r = run_guard("/x/6_PL/parking-lot.md", "### [ ] PL-NEW-ITEM offen\n", audit)
    assert r["continue"] is True


def test_explicit_warn_optout():
    """OMNI_GEIST9B_ENFORCE=0 (Debug-Opt-out) → WARN (continue:true mit message)."""
    audit = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]
    r = run_guard("/x/6_PL/parking-lot.md", "### [x] PL-FOO DONE\n", audit, warn_optout=True)
    assert r["continue"] is True
    assert "WARNED" in r.get("message", "")


def test_block_is_default_under_enforce():
    """NEU 2026-05-29: ohne Opt-out → BLOCK (enforceProcess=true ist Default-Enforcement)."""
    audit = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]
    r = run_guard("/x/6_PL/parking-lot.md", "### [x] PL-FOO DONE\n", audit)
    assert r["continue"] is False
    assert "RUECK-HANDSCHUH" in r.get("message", "")


def test_other_file_passthrough():
    audit = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]
    r = run_guard("/x/random.md", "### [x] PL-FOO\n", audit)
    assert r["continue"] is True


if __name__ == "__main__":
    tests = [test_pl_done_inline_blocked, test_pl_done_with_post_allowed,
             test_completed_batches_inline_blocked, test_no_i_pipeline_passthrough,
             test_non_completion_pl_edit_passthrough, test_explicit_warn_optout,
             test_block_is_default_under_enforce, test_other_file_passthrough]
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
