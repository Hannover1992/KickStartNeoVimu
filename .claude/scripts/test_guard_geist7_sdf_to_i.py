"""
pytest tests fuer guard_geist7_sdf_to_i.py (BL-219 Skip-Detector).

Test-Pattern (analog test_guard_modus_writer.py):
  - Subprocess-Aufruf des Guards mit synthetischem stdin
  - Env-Override OMNI_ENFORCE_GEIST7=1 erzwingt enforce=true
  - Env-Override OMNI_GEIST7_AUDIT_PATH / _MANIFEST_PATH fuer Isolation
  - Jeder Test baut tmp audit.jsonl + manifest auf, ruft Guard, prueft JSON.

8 Test-Cases:
  T1: M2 slicing=false mit 5 Skills -> continue:true (pass)
  T2: M2 slicing=false mit 3 Skills -> continue:false ("min 5")
  T3: M3 slicing=false mit 10 Skills (5 BP + 5 TDD) -> continue:true (pass)
  T4: M3 slicing=false mit 4 Skills (Mega-Worker) -> continue:false ("min 10")
  T5: M3 mit pragmatik_reason + 4 Skills -> continue:true (warn-only)
  T6: _I_orchestrate noch laufend (next_skill ist _I_step) -> continue:true (passthrough)
  T7: Kein _I_orchestrate-Event in audit -> continue:true (passthrough)
  T8: M2 slicing=true mit 8 Skills -> continue:true (pass)
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_geist7_sdf_to_i.py"


# ------------- Test-Helpers -------------

def _make_skill_load_event(skill_name, ts=None):
    """Baut ein audit.jsonl-Event im echten Format."""
    return {
        "ts": ts or datetime.now().isoformat(timespec="seconds"),
        "event": "SKILL_LOAD",
        "skill_name": skill_name,
        "load_method": "skill",
        "vertrag_bound": True,
        "ctx": {"feature": "test"},
    }


def _write_audit(audit_path, events):
    """Schreibt Events als JSONL."""
    with open(audit_path, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def _write_manifest(manifest_path, modus="M2", slicing=False, pragmatik=False):
    """Schreibt synthetisches Manifest mit Modus/Slicing/Pragmatik."""
    parts = [
        "## DF_BATCH_STATE (test)",
        f"modus: {modus}",
        f"slicing: {str(slicing).lower()}",
        "modus_set_by: _SDF_berater_modusEntscheidung",
    ]
    if pragmatik:
        parts.append("pragmatik_reason: Test-Case mit explizitem Pragmatik-Override fuer M3 Klein-Batch")
    Path(manifest_path).write_text("\n".join(parts) + "\n", encoding="utf-8")


def run_guard(tool_name, tool_input, audit_events, manifest_modus="M2",
              manifest_slicing=False, manifest_pragmatik=False,
              session_enforce="true", with_manifest=True):
    """Ruft guard_geist7_sdf_to_i.py mit isoliertem Env auf.

    Returns dict (parsed JSON-Output) oder raises RuntimeError.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        audit_file = tmp_path / "audit.jsonl"
        manifest_file = tmp_path / "_manifest.md"
        session_file = tmp_path / "_session_params.md"

        _write_audit(audit_file, audit_events)
        session_file.write_text(
            f"# Session Params\n**enforceProcess:** {session_enforce}\n",
            encoding="utf-8"
        )

        if with_manifest:
            _write_manifest(
                manifest_file,
                modus=manifest_modus,
                slicing=manifest_slicing,
                pragmatik=manifest_pragmatik,
            )

        env = os.environ.copy()
        env["OMNI_ENFORCE_GEIST7"] = "1" if session_enforce == "true" else "0"
        env["OMNI_GEIST7_AUDIT_PATH"] = str(audit_file)
        env["OMNI_GEIST7_SESSION_PARAMS"] = str(session_file)
        if with_manifest:
            env["OMNI_GEIST7_MANIFEST_PATH"] = str(manifest_file)

        hook_data = {"tool_name": tool_name, "tool_input": tool_input}
        proc = subprocess.run(
            [sys.executable, str(GUARD_SCRIPT)],
            input=json.dumps(hook_data),
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        out = proc.stdout.strip()
        if not out:
            raise RuntimeError(f"empty stdout, stderr={proc.stderr!r}")
        # Bei mehrzeiligem Output letzte JSON-Zeile nehmen
        last_line = out.splitlines()[-1]
        return json.loads(last_line)


# ------------- Tests -------------

def test_m2_5_skills_passes():
    """T1: M2 slicing=false mit genau 5 distinct _I_-Skills -> pass."""
    events = [
        _make_skill_load_event("_I_orchestrate"),
        _make_skill_load_event("_I_requirementCheck"),
        _make_skill_load_event("_I_goldDefine"),
        _make_skill_load_event("_I_blueprintQG"),
        _make_skill_load_event("_I_verify"),
        _make_skill_load_event("_I_diffAudit"),  # 5. distinct step
    ]
    # next-tool: Skill(_SDF_orchestrate_post) -> Skill-Wechsel raus
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_SDF_orchestrate_post"},
        audit_events=events,
        manifest_modus="M2",
        manifest_slicing=False,
    )
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_m2_3_skills_blocks():
    """T2: M2 slicing=false mit nur 3 Skills -> block 'min 5'."""
    events = [
        _make_skill_load_event("_I_orchestrate"),
        _make_skill_load_event("_I_requirementCheck"),
        _make_skill_load_event("_I_goldDefine"),
        _make_skill_load_event("_I_verify"),  # nur 3 distinct
    ]
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_SDF_orchestrate_post"},
        audit_events=events,
        manifest_modus="M2",
        manifest_slicing=False,
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    msg = result.get("message", "")
    assert "PROCESS_BYPASS_DETECTED" in msg or "min=5" in msg, f"Expected min-5-message, got: {msg}"
    assert "M2" in msg


def test_m3_10_skills_passes():
    """T3: M3 slicing=false mit 10 distinct Skills (5 BP + 5 TDD) -> pass."""
    events = [
        _make_skill_load_event("_I_orchestrate"),
        # 5 Blueprint-Steps
        _make_skill_load_event("_I_requirementCheck"),
        _make_skill_load_event("_I_goldDefine"),
        _make_skill_load_event("_I_patternLibrary"),
        _make_skill_load_event("_I_blueprintArchitect"),
        _make_skill_load_event("_I_blueprintQG"),
        # 5 TDD-Cycle-Steps
        _make_skill_load_event("_TDD_red"),
        _make_skill_load_event("_TDD_execute"),
        _make_skill_load_event("_TDD_green"),
        _make_skill_load_event("_TDD_refactorCode"),
        _make_skill_load_event("_TDD_check"),
    ]
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_SDF_orchestrate_post"},
        audit_events=events,
        manifest_modus="M3",
        manifest_slicing=False,
    )
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_m3_4_skills_mega_worker_blocks():
    """T4: M3 slicing=false mit 4 Skills (Mega-Worker-Drift) -> block 'min 10'."""
    events = [
        _make_skill_load_event("_I_orchestrate"),
        _make_skill_load_event("_I_requirementCheck"),
        _make_skill_load_event("_I_blueprintArchitect"),
        _make_skill_load_event("_TDD_execute"),
        _make_skill_load_event("_I_verify"),  # nur 4 distinct - massiver Mega-Worker
    ]
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_SDF_orchestrate_post"},
        audit_events=events,
        manifest_modus="M3",
        manifest_slicing=False,
    )
    assert result["continue"] is False, f"Expected block for Mega-Worker, got: {result}"
    msg = result.get("message", "")
    assert "min=10" in msg or "M3" in msg, f"Expected M3/min10 in message, got: {msg}"


def test_m3_4_skills_with_pragmatik_warns_only():
    """T5: M3 mit pragmatik_reason + nur 4 Skills -> warn-only (continue:true)."""
    events = [
        _make_skill_load_event("_I_orchestrate"),
        _make_skill_load_event("_I_requirementCheck"),
        _make_skill_load_event("_I_blueprintArchitect"),
        _make_skill_load_event("_TDD_execute"),
        _make_skill_load_event("_I_verify"),
    ]
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_SDF_orchestrate_post"},
        audit_events=events,
        manifest_modus="M3",
        manifest_slicing=False,
        manifest_pragmatik=True,
    )
    assert result["continue"] is True, f"Expected warn-pass with pragmatik, got: {result}"
    msg = result.get("message", "")
    # Bei Pragmatik-Override sollte ein Warn-Hinweis kommen, aber nicht blocken
    assert "pragmatik_reason" in msg.lower() or "warn" in msg.lower(), \
        f"Expected pragmatik-warn-mention, got: {msg}"


def test_i_pipeline_still_running_passthrough():
    """T6: next_skill ist _I_step waehrend Run aktiv -> passthrough (kein count)."""
    events = [
        _make_skill_load_event("_I_orchestrate"),
        _make_skill_load_event("_I_requirementCheck"),
    ]
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_I_blueprintArchitect"},  # noch I-Step
        audit_events=events,
        manifest_modus="M3",
        manifest_slicing=False,
    )
    assert result["continue"] is True, f"Expected passthrough during I-run, got: {result}"


def test_no_i_orchestrate_in_audit_passthrough():
    """T7: Audit hat keinen _I_orchestrate-Event -> passthrough."""
    events = [
        _make_skill_load_event("_BDF_orchestrate"),
        _make_skill_load_event("_SDF_orchestrate"),
    ]
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_SDF_orchestrate_post"},
        audit_events=events,
        manifest_modus="M3",
        manifest_slicing=False,
    )
    assert result["continue"] is True, f"Expected pass (no _I_orchestrate), got: {result}"


def test_m2_slicing_true_min_8():
    """T8: M2 slicing=true braucht 8 Skills."""
    events = [_make_skill_load_event("_I_orchestrate")]
    # 8 distinct I-Steps
    for s in (
        "_I_requirementCheck", "_I_goldDefine", "_I_patternLibrary",
        "_I_blueprintArchitect", "_I_blueprintQG", "_I_verify",
        "_I_diffAudit", "_I_testSearch",
    ):
        events.append(_make_skill_load_event(s))

    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_SDF_orchestrate_post"},
        audit_events=events,
        manifest_modus="M2",
        manifest_slicing=True,
    )
    assert result["continue"] is True, f"Expected pass for M2 slicing=true with 8, got: {result}"


def test_m2_slicing_true_with_7_blocks():
    """T8b (Bonus): M2 slicing=true mit 7 Skills (eins zu wenig) -> block."""
    events = [_make_skill_load_event("_I_orchestrate")]
    for s in (
        "_I_requirementCheck", "_I_goldDefine", "_I_patternLibrary",
        "_I_blueprintArchitect", "_I_blueprintQG", "_I_verify",
        "_I_diffAudit",
    ):
        events.append(_make_skill_load_event(s))

    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_SDF_orchestrate_post"},
        audit_events=events,
        manifest_modus="M2",
        manifest_slicing=True,
    )
    assert result["continue"] is False, f"Expected block for M2 slicing=true with 7, got: {result}"
    assert "min=8" in result.get("message", "") or "M2" in result.get("message", "")
