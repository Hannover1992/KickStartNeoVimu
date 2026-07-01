#!/usr/bin/env python3
"""Tests fuer guard_geist7c_done_claim_proof.py."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_geist7c_done_claim_proof.py"


def run_guard(new_text, audit_lines, enforce=True, fp="/x/6_PL/parking-lot.md"):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for line in audit_lines:
            f.write(json.dumps(line) + "\n")
        audit_path = f.name
    env = os.environ.copy()
    env["OMNI_GEIST7C_AUDIT"] = audit_path
    if enforce:
        env["OMNI_GEIST7C_ENFORCE"] = "1"
    event = {"tool_name": "Edit", "tool_input": {"file_path": fp, "new_string": new_text}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    Path(audit_path).unlink(missing_ok=True)
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}


def test_done_with_numbers_allowed():
    """[x] mit '813/813' → ALLOW (Text-Beweis)."""
    r = run_guard("### [x] PL-FOO DONE: Karma 813/813 passed\n", [])
    assert r["continue"] is True


def test_done_with_keyword_proof_allowed():
    """[x] mit 'nx build gruen' → ALLOW (Keyword-Beweis)."""
    r = run_guard("### [x] PL-FOO DONE: nx build gruen, keine Errors\n", [])
    assert r["continue"] is True


def test_done_without_proof_blocked():
    """[x] ohne Zahlen/Keywords + kein audit-Test → BLOCK (enforce)."""
    audit = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]
    r = run_guard("### [x] PL-FOO DONE: erledigt\n", audit)
    assert r["continue"] is False
    assert "GEIST7C" in r.get("message", "")


def test_done_with_audit_verify_allowed():
    """[x] ohne Text-Beweis ABER _I_verify im audit → ALLOW."""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        {"event": "SKILL_LOAD", "skill_name": "_I_verify"},
    ]
    r = run_guard("### [x] PL-FOO DONE\n", audit)
    assert r["continue"] is True


def test_done_with_tdd_execute_allowed():
    """[x] + _TDD_execute im audit → ALLOW."""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        {"event": "SKILL_LOAD", "skill_name": "_TDD_execute"},
    ]
    r = run_guard("### [x] PL-FOO DONE\n", audit)
    assert r["continue"] is True


def test_open_item_passthrough():
    """[ ] Item (keine DONE-Transition) → ALLOW."""
    r = run_guard("### [ ] PL-FOO offen\n", [])
    assert r["continue"] is True


def test_warn_mode_default():
    """Ohne enforce → WARN (continue:true)."""
    audit = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]
    r = run_guard("### [x] PL-FOO DONE\n", audit, enforce=False)
    assert r["continue"] is True
    assert "WARNED" in r.get("message", "")


def test_other_file_passthrough():
    r = run_guard("### [x] PL-FOO DONE\n", [], fp="/x/random.md")
    assert r["continue"] is True


if __name__ == "__main__":
    tests = [test_done_with_numbers_allowed, test_done_with_keyword_proof_allowed,
             test_done_without_proof_blocked, test_done_with_audit_verify_allowed,
             test_done_with_tdd_execute_allowed, test_open_item_passthrough,
             test_warn_mode_default, test_other_file_passthrough]
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
