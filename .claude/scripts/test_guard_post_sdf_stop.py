#!/usr/bin/env python3
"""Tests fuer guard_post_sdf_stop.py (BL-427, FEUER-Mechanismus — Stop-Hook).

TDD Stage 1 (Atomic). Vorbild: test_guard_sdf_post_handoff.py (BL-427 PreToolUse-Guard).

Stop-Hook-Komplement: waehrend der PreToolUse-Guard (guard_sdf_post_handoff.py) den
naechsten SDF-Load blockt, schliesst dieser Stop-Hook den TERMINAL-GAP — wenn der Flow
nach einem I/SC-Build einfach endet ohne _SDF_orchestrate_post zu laden.

hook_event=Stop: laeuft bei Turn-Ende / Goal-Termination.

Soll-Semantik (VIOLATION + enforceProcess=true -> BLOCK-STOP):
  1. Scanne audit.jsonl rueckwaerts.
  2. Wenn juengste Orchestrator-Level-Aktion ein Build-Caller ist
     (_I_orchestrate / _SC_orchestrate, SKILL_LOAD)
  3. UND seitdem KEIN _SDF_orchestrate_post-Load UND kein _SDF_orchestrate-Resume
     (kein Weiter-Ringen mit SDF, das den Post haette nachholen koennen)
  4. -> VIOLATION.
  5. VIOLATION + enforceProcess=true -> {"continue": false} + Block-Reason.
  6. VIOLATION + enforceProcess=false -> WARN + {"continue": true}.
  7. Kein Build-Caller als juengste Aktion / Post bereits gefeuert -> {"continue": true}.
  8. Off-Switches: OMNI_ENFORCE_ALL_OFF=1 + OMNI_POST_SDF_STOP_OFF=1 -> {"continue": true}.
  9. Kein audit.jsonl -> fail-open -> {"continue": true}.

Test-Override: OMNI_POST_SDF_STOP_AUDIT (audit-Pfad).
Globaler Off-Switch: OMNI_ENFORCE_ALL_OFF=1.
Lokaler Off-Switch: OMNI_POST_SDF_STOP_OFF=1.

RED-State: guard_post_sdf_stop.py existiert noch nicht -> alle Tests FAILEN
  mit FileNotFoundError (importlib) oder fehlendem Subprocess-Exit (subprocess).

Tests:
  T1  test_terminal_build_without_post_blocks   — I-Build + kein Post + enforce=true -> block-stop
  T2  test_post_fired_passes                    — I-Build -> Post-SDF -> Stop -> continue:true
  T3  test_no_build_caller_passes               — juengste Aktion kein Build-Caller -> continue:true
  T4  test_enforce_false_warn                   — VIOLATION + enforce=false -> WARN + continue:true
  T5  test_off_switch_global                    — OMNI_ENFORCE_ALL_OFF=1 -> continue:true
  T6  test_off_switch_local                     — OMNI_POST_SDF_STOP_OFF=1 -> continue:true
  T7  test_no_audit_failopen                    — kein audit.jsonl -> continue:true (fail-open)
  T8  test_importable                           — guard_post_sdf_stop importierbar + Kern-Symbole
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_post_sdf_stop.py"


# ---------------------------------------------------------------------------
# Hilfs-Fixtures
# ---------------------------------------------------------------------------

def _make_audit_file(audit_lines):
    """Schreibt audit_lines als JSONL in eine Tempfile, gibt Pfad zurueck."""
    af = tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    )
    for line in audit_lines:
        af.write(json.dumps(line) + "\n")
    af.close()
    return af.name


def _make_session_params(enforce):
    """Schreibt eine _session_params.md Tempfile, gibt Pfad zurueck."""
    sp = tempfile.NamedTemporaryFile(
        mode="w", suffix="_session_params.md", delete=False, encoding="utf-8"
    )
    sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
    sp.close()
    return sp.name


def _run_stop_hook(audit_lines, enforce=True, extra_env=None):
    """Simuliert Stop-Event und gibt (proc, result) zurueck.

    Stop-Hook liest Stop-Event von stdin (JSON), scannt audit.jsonl.
    """
    audit_path = _make_audit_file(audit_lines)
    sp_path = _make_session_params(enforce)
    env = os.environ.copy()
    env["OMNI_POST_SDF_STOP_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    if extra_env:
        env.update(extra_env)

    # Stop-Hook-Input (hook_event=Stop — analog process_audit_stop_hook.py)
    stop_event = {"hook_event": "Stop", "reason": "turn_end"}

    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(stop_event),
        capture_output=True,
        text=True,
        env=env,
    )
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc, result


# ---------------------------------------------------------------------------
# T1: terminal_build_without_post_blocks
# ---------------------------------------------------------------------------

def test_terminal_build_without_post_blocks():
    """T1 (Kern-RED-Test): _I_orchestrate ist juengste Aktion, kein _SDF_orchestrate_post
    danach (TERMINAL-GAP) + enforceProcess=true -> BLOCK-STOP.

    Stop-Hook-Soll: continue=false + Reason 'Skill(_SDF_orchestrate_post) muss am
    I/SC-Ende gefeuert werden (BL-427 FEUER-Mechanismus)'.

    RED: guard_post_sdf_stop.py existiert nicht -> FileNotFoundError / exit != 0.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        # Kein _SDF_orchestrate_post danach -> TERMINAL-GAP
    ]
    proc, r = _run_stop_hook(audit, enforce=True)
    assert r.get("continue") is False, (
        f"T1 terminal-build-without-post-blocks: juengste Aktion = _I_orchestrate, kein Post-SDF "
        f"+ enforce=true -> continue:false (BLOCK-STOP) erwartet. War: {r}. "
        f"guard_post_sdf_stop.py existiert vermutlich noch nicht (RED erwartet)."
    )
    msg = r.get("message", "") + proc.stderr
    assert (
        "_SDF_orchestrate_post" in msg
        or "BL-427" in msg
        or "FEUER" in msg
        or "Post" in msg
    ), (
        "T1: Block-Message muss _SDF_orchestrate_post / BL-427 / FEUER / Post erwaehnen. "
        f"War: '{msg}'"
    )


# ---------------------------------------------------------------------------
# T2: post_fired_passes
# ---------------------------------------------------------------------------

def test_post_fired_passes():
    """T2 (happy-path): _I_orchestrate-Load -> _SDF_orchestrate_post-Load vorhanden.
    Stop-Hook findet Post -> kein TERMINAL-GAP -> continue:true.

    RED: guard_post_sdf_stop.py existiert nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
    ]
    proc, r = _run_stop_hook(audit, enforce=True)
    assert r.get("continue") is True, (
        f"T2 post-fired-passes: _SDF_orchestrate_post vorhanden nach I-Build "
        f"-> continue:true erwartet. War: {r}."
    )
    assert proc.returncode == 0, (
        f"T2: exit 0 erwartet (kein Block), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T3: no_build_caller_passes
# ---------------------------------------------------------------------------

def test_no_build_caller_passes():
    """T3 (kein false-positive): Juengste Aktion im Audit ist KEIN Build-Caller
    (_I_orchestrate / _SC_orchestrate) -> Guard bleibt ruhig -> continue:true.

    Normaler Turn-Ende ohne Build -> KEIN Block.

    RED: guard_post_sdf_stop.py existiert nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_berater_batchPlanner"},
        {"event": "SKILL_LOAD", "skill_name": "_A_berater_specParse"},
    ]
    proc, r = _run_stop_hook(audit, enforce=True)
    assert r.get("continue") is True, (
        f"T3 no-build-caller-passes: Juengste Aktion kein Build-Caller "
        f"-> continue:true erwartet (kein False-Block). War: {r}."
    )
    assert proc.returncode == 0, (
        f"T3: exit 0 erwartet, war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T4: enforce_false_warn
# ---------------------------------------------------------------------------

def test_enforce_false_warn():
    """T4 (WARN-Modus): VIOLATION (I-Build + kein Post) + enforceProcess=false
    -> WARN + continue:true (kein BLOCK-STOP).

    Stop-Hook darf im enforce=false-Modus den Turn NICHT sperren.

    RED: guard_post_sdf_stop.py existiert nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        # Kein _SDF_orchestrate_post -> Verletzung; aber enforce=false -> nur WARN
    ]
    proc, r = _run_stop_hook(audit, enforce=False)
    assert r.get("continue") is True, (
        f"T4 enforce-false-warn: VIOLATION + enforceProcess=false "
        f"-> continue:true (WARN, kein Block) erwartet. War: {r}."
    )
    assert proc.returncode == 0, (
        f"T4: exit 0 erwartet (kein Block bei enforce=false), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T5: off_switch_global
# ---------------------------------------------------------------------------

def test_off_switch_global():
    """T5 (Off-Switch global): OMNI_ENFORCE_ALL_OFF=1 deaktiviert alle Guards.
    Auch mit klarer TERMINAL-GAP-Verletzung -> continue:true, exit 0.

    RED: guard_post_sdf_stop.py existiert nicht oder kennt OMNI_ENFORCE_ALL_OFF nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        # Keine Post-SDF -> eigentlich Verletzung
    ]
    proc, r = _run_stop_hook(
        audit, enforce=True, extra_env={"OMNI_ENFORCE_ALL_OFF": "1"}
    )
    assert r.get("continue") is True, (
        f"T5 off-switch-global: OMNI_ENFORCE_ALL_OFF=1 -> continue:true erwartet. War: {r}."
    )
    assert proc.returncode == 0, (
        f"T5: exit 0 erwartet, war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T6: off_switch_local
# ---------------------------------------------------------------------------

def test_off_switch_local():
    """T6 (Off-Switch lokal): OMNI_POST_SDF_STOP_OFF=1 deaktiviert diesen Guard.
    Auch mit klarer Verletzung -> continue:true, exit 0.

    RED: guard_post_sdf_stop.py existiert nicht oder kennt OMNI_POST_SDF_STOP_OFF nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SC_orchestrate"},
        # Keine Post-SDF -> eigentlich Verletzung, aber lokaler Off-Switch greift
    ]
    proc, r = _run_stop_hook(
        audit, enforce=True, extra_env={"OMNI_POST_SDF_STOP_OFF": "1"}
    )
    assert r.get("continue") is True, (
        f"T6 off-switch-local: OMNI_POST_SDF_STOP_OFF=1 -> continue:true erwartet. War: {r}."
    )
    assert proc.returncode == 0, (
        f"T6: exit 0 erwartet, war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T7: no_audit_failopen
# ---------------------------------------------------------------------------

def test_no_audit_failopen():
    """T7 (fail-open): kein audit.jsonl -> Guard kann nicht scannen -> fail-open
    -> continue:true, exit 0. Pipeline-Liveness > False-Block-Risiko.

    RED: guard_post_sdf_stop.py existiert nicht.
    """
    sp_path = _make_session_params(enforce=True)
    env = os.environ.copy()
    env["OMNI_POST_SDF_STOP_AUDIT"] = "/nonexistent/audit_BL427_xYz.jsonl"
    env["OMNI_SESSION_PARAMS"] = sp_path

    stop_event = {"hook_event": "Stop", "reason": "turn_end"}
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(stop_event),
        capture_output=True,
        text=True,
        env=env,
    )
    Path(sp_path).unlink(missing_ok=True)
    result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    assert result.get("continue") is True, (
        f"T7 no-audit-failopen: Fehlender audit.jsonl -> continue:true (fail-open). War: {result}."
    )
    assert proc.returncode == 0, (
        f"T7: exit 0 erwartet (fail-open), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T8: test_importable — Kern-Symbole vorhanden
# ---------------------------------------------------------------------------

def test_importable():
    """T8 (structural): guard_post_sdf_stop.py muss importierbar sein und die
    Kern-Symbole exportieren.

    Kern-Symbole (Stop-Hook-Analogon zu guard_sdf_post_handoff.py):
      - post_sdf_ran_since_i_sc (shared audit-scan-helper, per Kurzlebig-Prompt)
      - main (Entrypoint)

    Failt im RED-State mit spec=None / ImportError weil Datei fehlt.
    """
    spec = importlib.util.spec_from_file_location("guard_post_sdf_stop", str(GUARD))
    assert spec is not None, (
        "guard_post_sdf_stop.py nicht gefunden — importlib.util.spec_from_file_location "
        "gibt None zurueck. Datei existiert noch nicht (RED erwartet)."
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert hasattr(mod, "post_sdf_ran_since_i_sc"), (
        "post_sdf_ran_since_i_sc fehlt in guard_post_sdf_stop.py "
        "(Kern audit-Scan-Helper per KURZLEBIG_PROMPT — RED erwartet)."
    )
    assert hasattr(mod, "main"), (
        "main fehlt in guard_post_sdf_stop.py (Entrypoint — RED erwartet)."
    )


# ---------------------------------------------------------------------------
# __main__ runner (direkt ausfuehrbar ohne pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_terminal_build_without_post_blocks,
        test_post_fired_passes,
        test_no_build_caller_passes,
        test_enforce_false_warn,
        test_off_switch_global,
        test_off_switch_local,
        test_no_audit_failopen,
        test_importable,
    ]
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
    print(f"\n=== {passed}/{passed + failed} ===")
    sys.exit(0 if failed == 0 else 1)
