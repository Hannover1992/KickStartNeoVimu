#!/usr/bin/env python3
"""Tests fuer guard_geist7b_sdf_dispatch_target.py."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_geist7b_sdf_dispatch_target.py"


def run_guard(subagent_type, audit_lines, desc="batch worker"):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for line in audit_lines:
            f.write(json.dumps(line) + "\n")
        audit_path = f.name
    env = os.environ.copy()
    env["OMNI_GEIST7B_ENFORCE"] = "1"
    env["OMNI_GEIST7B_AUDIT"] = audit_path
    event = {"tool_name": "Agent", "tool_input": {"subagent_type": subagent_type, "description": desc}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    Path(audit_path).unlink(missing_ok=True)
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}


def test_sdf_direct_general_sonnet_blocked():
    """SDF-Kontext + general-sonnet OHNE _I_orchestrate → BLOCK (Round 16 Drift)."""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate"},
        {"event": "STATE_WRITE", "summary": "modusEntscheidung B1=M2 done"},
    ]
    r = run_guard("general-sonnet", audit, "B1 Build gruen")
    assert r["continue"] is False
    assert "GEIST7B" in r.get("message", "")


def test_sdf_via_i_orchestrate_allowed():
    """SDF → Skill(_I_orchestrate) → general-sonnet = legit I-Pipeline-Worker → ALLOW."""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate"},
        {"event": "STATE_WRITE", "summary": "modusEntscheidung done"},
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
    ]
    r = run_guard("general-sonnet", audit, "Step 1 cleanCodeArchitect")
    assert r["continue"] is True


def test_no_sdf_context_allowed():
    """Kein SDF-Kontext → general-sonnet legit (andere Pipeline)."""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_R_orchestrate"},
    ]
    r = run_guard("general-sonnet", audit, "review worker")
    assert r["continue"] is True


def test_non_generic_agent_passthrough():
    """Spezialisierter Agent (nicht general-*) → passthrough."""
    audit = [{"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate"}]
    r = run_guard("be-controller-specialist", audit)
    assert r["continue"] is True


def test_sc_orchestrate_also_legit():
    """SDF → Skill(_SC_orchestrate) → general-sonnet = legit SC-Worker → ALLOW."""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate"},
        {"event": "STATE_WRITE", "summary": "modusEntscheidung M5 done"},
        {"event": "SKILL_LOAD", "skill_name": "_SC_orchestrate"},
    ]
    r = run_guard("general-sonnet", audit, "SC observe worker")
    assert r["continue"] is True


def test_empty_audit_passthrough():
    """Kein audit-Trail → konservativ durchlassen."""
    r = run_guard("general-sonnet", [])
    assert r["continue"] is True


def test_override_off():
    """OMNI_GEIST7B_OFF=1 → ALLOW trotz Bypass."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write(json.dumps({"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate"}) + "\n")
        audit_path = f.name
    env = os.environ.copy()
    env["OMNI_GEIST7B_ENFORCE"] = "1"
    env["OMNI_GEIST7B_OFF"] = "1"
    env["OMNI_GEIST7B_AUDIT"] = audit_path
    event = {"tool_name": "Agent", "tool_input": {"subagent_type": "general-sonnet"}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    Path(audit_path).unlink(missing_ok=True)
    r = json.loads(proc.stdout.strip())
    assert r["continue"] is True


if __name__ == "__main__":
    tests = [test_sdf_direct_general_sonnet_blocked, test_sdf_via_i_orchestrate_allowed,
             test_no_sdf_context_allowed, test_non_generic_agent_passthrough,
             test_sc_orchestrate_also_legit, test_empty_audit_passthrough, test_override_off]
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


# ──────────────────────── BL-210: model-agnostischer Diskriminator ────────────────────────
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.absolute()))
import guard_geist7b_sdf_dispatch_target as _g7b


def _run_g7b(ti, tool_name="Agent"):
    import json as _json, subprocess as _sp, os as _os
    env = _os.environ.copy()
    env["OMNI_GEIST7B_ENFORCE"] = "1"
    ev = {"tool_name": tool_name, "tool_input": ti}
    r = _sp.run([_sys.executable, str(_Path(__file__).parent / "guard_geist7b_sdf_dispatch_target.py")],
                input=_json.dumps(ev), capture_output=True, text=True, env=env)
    return _json.loads(r.stdout.strip())


def test_bl210_opus_custom_type_dispatch_worker_blocks():
    # model-agnostisch: Custom-Type (kein general-*) + Dispatch-Contract -> BLOCK
    ti = {"subagent_type": "be-controller-specialist",
          "description": "SDF-Phase-2-Dispatch-Worker (Opus) fuer Sub-Batch B_r17_05",
          "prompt": "VERTRAG: fuehre Skill(_I_orchestrate) fuer Sub-Batch B_r17_05 aus, Modus M2"}
    assert _run_g7b(ti)["continue"] is False


def test_bl210_single_phase_tdd_passes():
    ti = {"subagent_type": "general-sonnet", "prompt": "_TDD_green fuer test_login bis GREEN"}
    assert _run_g7b(ti)["continue"] is True


def test_bl210_blueprint_single_phase_passes():
    ti = {"subagent_type": "general-opus",
          "prompt": "_I_blueprintArchitect: fuehre die Blueprint-Analyse fuer _I_orchestrate Stage 2 aus"}
    assert _run_g7b(ti)["continue"] is True


def test_bl210_skill_tool_not_subject():
    # Lead-Handschuh-Wechsel via Skill darf NIE von geist7b beruehrt werden
    assert _run_g7b({"skill": "_I_orchestrate", "args": "--stage=2"}, tool_name="Skill")["continue"] is True


def test_bl210_is_orchestrator_exec_contract_unit():
    assert _g7b.is_orchestrator_exec_contract("run _I_orchestrate for sub-batch 3") is True
    assert _g7b.is_orchestrator_exec_contract("_TDD_red fuer test_x") is False
    assert _g7b.is_orchestrator_exec_contract("fuehre die Analyse aus") is False


def test_bl440_a_orchestrate_resets_sdf_context():
    """BL-440: nach vorigem BL (SDF-Marker) startet ein neues BL via Skill(_A_orchestrate);
    dessen A-Berater-Spawn (general-sonnet) darf NICHT als SDF->non-I geblockt werden."""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate"},
        {"event": "STATE_WRITE", "summary": "modusEntscheidung B1=M2 done"},
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
        {"event": "SKILL_LOAD", "skill_name": "_A_orchestrate"},  # neues BL: frische A-Pipeline
    ]
    r = run_guard("general-sonnet", audit, "A Phase 2.5 W_fetch BL-439")
    assert r["continue"] is True, "A-Berater nach frischem _A_orchestrate darf nicht geblockt werden"


def test_bl440_idf_orchestrate_resets_sdf_context():
    """BL-440: _IDF_orchestrate (neue Dekomposition) resettet ebenfalls den SDF-Dispatch-Kontext."""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate"},
        {"event": "STATE_WRITE", "summary": "modusEntscheidung done"},
        {"event": "SKILL_LOAD", "skill_name": "_IDF_orchestrate"},
    ]
    r = run_guard("general-sonnet", audit, "IDF Phase 4 dependencyAnalyzer")
    assert r["continue"] is True


def test_bl440_real_violation_still_blocks():
    """BL-440 Gegenprobe (KEIN Weakening): SDF-Marker, dann general-sonnet OHNE jeden
    A/IDF/I/SC-Load dazwischen -> echte SDF->non-I-Violation bleibt BLOCKIERT."""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate"},
        {"event": "STATE_WRITE", "summary": "modusEntscheidung B1=M3 done"},
    ]
    r = run_guard("general-sonnet", audit, "B1 Build komplett")
    assert r["continue"] is False, "echte SDF->non-I-Dispatch-Violation muss weiter blocken"
