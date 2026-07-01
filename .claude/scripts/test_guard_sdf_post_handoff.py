#!/usr/bin/env python3
"""Tests fuer guard_sdf_post_handoff.py (BL-427, AK-1..6).

TDD Stage 1 (Atomic). Vorbild: test_guard_a_idf_handoff.py (BL-350).
Der Guard blockt den naechsten SDF-Resume-Skill-Load (_SDF_orchestrate) wenn
seit dem letzten I/SC-Build (_I_orchestrate / _SC_orchestrate) KEIN
_SDF_orchestrate_post SKILL_LOAD sichtbar ist (audit.jsonl-Rueckwaerts-Scan).
Enforce-AFTER-write-Pattern (analog BL-350 AK-2): Write auf _manifest.md wird
IMMER durchgelassen; Enforcement liegt am Folge-Schritt (TRIGGER A: SDF-Resume-Load).

RED-State: guard_sdf_post_handoff.py existiert noch nicht -> alle Tests FAILEN
mit ImportError (T-a* via importlib) oder dem falschen exit-code/continue-Wert
(T-b* via subprocess).

Tests (T1-T10):
  T1  test_happy_path_post_sdf_present          — Post-SDF vor SDF-Resume -> pass
  T2  test_bypass_detect_no_post_sdf            — I-Load + kein Post-SDF -> BLOCK
  T3  test_terminate_no_fp                      — kein I/SC seit letztem Post-SDF -> pass
  T4  test_m1_no_fp                             — Post-SDF vorhanden (M1 kein Off-Switch) -> pass
  T5  test_off_switch_global                    — OMNI_ENFORCE_ALL_OFF=1 -> pass
  T6  test_off_switch_local                     — OMNI_SDF_POST_HANDOFF_OFF=1 -> pass
  T7  test_trigger_b_passthrough                — Edit _manifest.md -> immer pass
  T8  test_audit_missing_fail_open              — kein audit.jsonl -> fail-open (pass)
  T9  test_sc_orchestrate_detected              — SC-Build-Caller als Seam-Start erkannt
  T10 test_enforce_false_warn                   — enforceProcess=false -> WARN + pass
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_sdf_post_handoff.py"


# ---------------------------------------------------------------------------
# Hilfs-Fixtures
# ---------------------------------------------------------------------------

def _run_guard_skill_load(skill_name, audit_lines, enforce=True, extra_env=None):
    """Simuliert PreToolUse-Skill-Load-Event (TRIGGER A) und gibt (proc, result) zurueck."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as af:
        for line in audit_lines:
            af.write(json.dumps(line) + "\n")
        audit_path = af.name
    with tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8") as sp:
        sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
        sp_path = sp.name
    env = os.environ.copy()
    env["OMNI_SDF_POST_HANDOFF_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    if extra_env:
        env.update(extra_env)
    event = {
        "tool_name": "mcp__claude_ai__execute_skill",
        "tool_input": {"skill_name": skill_name},
    }
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(event),
        capture_output=True, text=True, env=env,
    )
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc, result


def _run_guard_edit(file_path_stub, new_text, audit_lines, enforce=True, extra_env=None):
    """Simuliert PreToolUse-Edit-Event (TRIGGER B) auf _manifest.md."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as af:
        for line in audit_lines:
            af.write(json.dumps(line) + "\n")
        audit_path = af.name
    with tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8") as sp:
        sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
        sp_path = sp.name
    env = os.environ.copy()
    env["OMNI_SDF_POST_HANDOFF_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    if extra_env:
        env.update(extra_env)
    event = {
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path_stub, "new_string": new_text},
    }
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(event),
        capture_output=True, text=True, env=env,
    )
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc, result


# ---------------------------------------------------------------------------
# T1: happy_path — Post-SDF-SKILL_LOAD nach I-Build, dann SDF-Resume -> pass
# ---------------------------------------------------------------------------

def test_happy_path_post_sdf_present():
    """T1 (AK-2 happy-path): _I_orchestrate-Load -> _SDF_orchestrate_post-Load
    -> _SDF_orchestrate-Resume-Load. Post-SDF ist vorhanden -> Guard passt durch
    (continue=True, exit 0).

    RED: guard_sdf_post_handoff.py existiert nicht -> FileNotFoundError oder exit != 0.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
        # _SDF_orchestrate-Resume folgt jetzt als PreToolUse-Event
    ]
    proc, r = _run_guard_skill_load("_SDF_orchestrate", audit, enforce=True)
    assert proc.returncode == 0, (
        f"T1 happy-path: Post-SDF vorhanden -> Guard passt durch (exit 0), "
        f"war exit {proc.returncode}. Guard existiert vermutlich noch nicht."
    )
    assert r.get("continue") is True, (
        "T1 happy-path: continue=True erwartet wenn Post-SDF vor SDF-Resume sichtbar."
    )


# ---------------------------------------------------------------------------
# T2: bypass_detect — I-Load sichtbar, KEIN Post-SDF, dann SDF-Resume -> BLOCK
# ---------------------------------------------------------------------------

def test_bypass_detect_no_post_sdf():
    """T2 (AK-2 bypass-detect, Kern-RED-Test): _I_orchestrate-Load sichtbar im Audit,
    KEIN _SDF_orchestrate_post danach, direkt _SDF_orchestrate-Resume-Load ->
    VIOLATION -> BLOCK (exit 2, enforceProcess=true).

    Das ist die Kern-Luecke (BL-427): Lead schlaegt _SDF_orchestrate an ohne vorher
    _SDF_orchestrate_post zu rufen (INV-HANDOVER-1 verletzt).

    RED: guard_sdf_post_handoff.py existiert nicht -> Subprocess-Error statt exit 2.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        # KEIN _SDF_orchestrate_post -> Verletzung
    ]
    proc, r = _run_guard_skill_load("_SDF_orchestrate", audit, enforce=True)
    assert proc.returncode == 2, (
        f"T2 bypass-detect: I-Load + kein Post-SDF + SDF-Resume -> BLOCK erwartet "
        f"(exit 2, enforceProcess=true), war exit {proc.returncode}. "
        f"Guard blockt nicht oder existiert nicht."
    )
    msg = r.get("message", "") + proc.stderr
    assert "_SDF_orchestrate_post" in msg or "Rufe Skill" in msg, (
        "T2: Recovery-Hint mit '_SDF_orchestrate_post' oder 'Rufe Skill' fehlt im Block-Msg."
    )


# ---------------------------------------------------------------------------
# T3: terminate_no_fp — kein I/SC seit letztem Post-SDF (TERMINATE-Pfad) -> pass
# ---------------------------------------------------------------------------

def test_terminate_no_fp():
    """T3 (AK-4 terminate-no-fp): Im Audit ist Post-SDF das juengste relevante Event,
    danach KEIN neuer I/SC-Build-Load. _SDF_orchestrate-Load ist der erste nach TERMINATE
    -> kein I/SC-Kontext aktiv -> Guard passt durch (kein False-Positive).

    TERMINATE-Pfad: SDF endet mit df_status=DONE, kein I-Build mehr. Der naechste
    SDF-Skill-Load (falls doch) wuerde keinen Build-Kontext haben.

    RED: guard_sdf_post_handoff.py existiert nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
        # Kein _I_orchestrate oder _SC_orchestrate NACH diesem Post-SDF-Event
    ]
    proc, r = _run_guard_skill_load("_SDF_orchestrate", audit, enforce=True)
    assert proc.returncode == 0, (
        f"T3 terminate-no-fp: kein I/SC seit letztem Post-SDF -> kein Block erwartet "
        f"(exit 0), war exit {proc.returncode}. False-Positive im TERMINATE-Pfad."
    )
    assert r.get("continue") is True, (
        "T3 terminate-no-fp: continue=True erwartet (kein I/SC-Kontext aktiv)."
    )


# ---------------------------------------------------------------------------
# T4: m1_no_fp — M1-Modus, Post-SDF vorhanden -> pass (M1 kein Off-Switch)
# ---------------------------------------------------------------------------

def test_m1_no_fp():
    """T4 (AK-5 m1-no-fp): M1-Modus im Audit sichtbar. Post-SDF MUSS trotzdem vorhanden
    sein (M1 ist kein Off-Switch fuer Post-SDF, nur Inhalts-Skips intern). Wenn Post-SDF
    vorhanden -> Guard passt durch.

    Das ist ein True-Negative-Test: M1 macht KEINEN False-Block wenn Post-SDF laeuft.
    Komplementaer: M1 ohne Post-SDF -> BLOCK (wie T2) — das ist bewusst korrekt.

    RED: guard_sdf_post_handoff.py existiert nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
        # M1-Kontext: Post-SDF lief trotzdem
    ]
    proc, r = _run_guard_skill_load("_SDF_orchestrate", audit, enforce=True)
    assert proc.returncode == 0, (
        f"T4 m1-no-fp: Post-SDF vorhanden (M1) -> Guard passt durch (exit 0), "
        f"war exit {proc.returncode}. M1 darf kein False-Positive erzeugen wenn Post-SDF vorhanden."
    )
    assert r.get("continue") is True, (
        "T4 m1-no-fp: continue=True erwartet wenn Post-SDF vor SDF-Resume (auch M1)."
    )


# ---------------------------------------------------------------------------
# T5: off_switch_global — OMNI_ENFORCE_ALL_OFF=1 -> immer pass
# ---------------------------------------------------------------------------

def test_off_switch_global():
    """T5 (AK-6 off-switch-global): OMNI_ENFORCE_ALL_OFF=1 deaktiviert den Guard global.
    Auch mit klarer Verletzung (I-Load ohne Post-SDF) -> continue=True, exit 0.

    RED: guard_sdf_post_handoff.py existiert nicht oder kennt OMNI_ENFORCE_ALL_OFF nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        # kein Post-SDF -> eigentlich Verletzung, aber ENFORCE_ALL_OFF=1 ueberschreibt
    ]
    proc, r = _run_guard_skill_load(
        "_SDF_orchestrate", audit, enforce=True,
        extra_env={"OMNI_ENFORCE_ALL_OFF": "1"}
    )
    assert proc.returncode == 0, (
        f"T5 off-switch-global: OMNI_ENFORCE_ALL_OFF=1 -> kein Block (exit 0), "
        f"war exit {proc.returncode}."
    )
    assert r.get("continue") is True, (
        "T5 off-switch-global: OMNI_ENFORCE_ALL_OFF=1 muss continue=True liefern."
    )


# ---------------------------------------------------------------------------
# T6: off_switch_local — OMNI_SDF_POST_HANDOFF_OFF=1 -> immer pass
# ---------------------------------------------------------------------------

def test_off_switch_local():
    """T6 (AK-6 off-switch-local): OMNI_SDF_POST_HANDOFF_OFF=1 deaktiviert diesen Guard.
    Auch mit klarer Verletzung -> continue=True, exit 0.

    RED: guard_sdf_post_handoff.py existiert nicht oder kennt OMNI_SDF_POST_HANDOFF_OFF nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        # kein Post-SDF -> eigentlich Verletzung, aber lokaler Off-Switch greift
    ]
    proc, r = _run_guard_skill_load(
        "_SDF_orchestrate", audit, enforce=True,
        extra_env={"OMNI_SDF_POST_HANDOFF_OFF": "1"}
    )
    assert proc.returncode == 0, (
        f"T6 off-switch-local: OMNI_SDF_POST_HANDOFF_OFF=1 -> kein Block (exit 0), "
        f"war exit {proc.returncode}."
    )
    assert r.get("continue") is True, (
        "T6 off-switch-local: OMNI_SDF_POST_HANDOFF_OFF=1 muss continue=True liefern."
    )


# ---------------------------------------------------------------------------
# T7: trigger_b_passthrough — Edit auf _manifest.md -> IMMER pass (enforce-AFTER-write)
# ---------------------------------------------------------------------------

def test_trigger_b_passthrough():
    """T7 (AK-3 trigger-b-passthrough): Write/Edit auf _manifest.md wird IMMER
    durchgelassen (enforce-AFTER-write-Pattern). Auch wenn I-Load vorhanden und
    kein Post-SDF -> der Guard blockt den WRITE nicht (Enforcement am Folge-Schritt).

    Das ist exakt das enforce-AFTER-write-Prinzip von BL-350: der Seam-Schreiber muss
    schreiben koennen; Enforcement passiert am naechsten Skill-Load (TRIGGER A).

    RED: guard_sdf_post_handoff.py existiert nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        # kein Post-SDF -> wuerde bei Skill-Load blocken, aber NICHT beim Write
    ]
    proc, r = _run_guard_edit(
        "/some/path/_manifest.md",
        "SDF_BATCH_STATUS:\n  current_batch: batch_2\n  status: RESUME\n",
        audit, enforce=True
    )
    assert proc.returncode == 0, (
        f"T7 trigger-b-passthrough: Edit auf _manifest.md muss immer exit 0 liefern "
        f"(enforce-AFTER-write), war exit {proc.returncode}."
    )
    assert r.get("continue") is True, (
        "T7: TRIGGER B (manifest-Write) muss continue=True liefern — kein Pre-Block."
    )


# ---------------------------------------------------------------------------
# T8: audit_missing_fail_open — kein audit.jsonl -> fail-open (pass)
# ---------------------------------------------------------------------------

def test_audit_missing_fail_open():
    """T8 (A2 audit-fail-safe): audit.jsonl existiert nicht -> Guard kann nicht scannen
    -> fail-open: continue=True, exit 0.

    Fail-open ist bewusste Entscheidung (Pipeline-Liveness > False-Block-Risiko, Spec A2).

    RED: guard_sdf_post_handoff.py existiert nicht.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8") as sp:
        sp.write("**enforceProcess:** true\n")
        sp_path = sp.name
    env = os.environ.copy()
    # Zeige auf nicht-existente Audit-Datei
    env["OMNI_SDF_POST_HANDOFF_AUDIT"] = "/nonexistent/audit_xYz_99.jsonl"
    env["OMNI_SESSION_PARAMS"] = sp_path
    event = {
        "tool_name": "mcp__claude_ai__execute_skill",
        "tool_input": {"skill_name": "_SDF_orchestrate"},
    }
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(event),
        capture_output=True, text=True, env=env,
    )
    Path(sp_path).unlink(missing_ok=True)
    result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    assert proc.returncode == 0, (
        f"T8 audit-missing-fail-open: kein audit.jsonl -> fail-open (exit 0), "
        f"war exit {proc.returncode}."
    )
    assert result.get("continue") is True, (
        "T8: Fehlender audit.jsonl -> continue=True (fail-open, Pipeline-Liveness)."
    )


# ---------------------------------------------------------------------------
# T9: sc_orchestrate_detected — SC-Build-Caller als Seam-Start erkannt
# ---------------------------------------------------------------------------

def test_sc_orchestrate_detected():
    """T9 (AK-2 SC-Variante): _SC_orchestrate-Load (nicht nur _I_orchestrate) muss
    ebenfalls als Seam-Start erkannt werden. I/SC sind beide valide Build-Caller.

    Szenario: _SC_orchestrate-Load, dann kein Post-SDF, dann _SDF_orchestrate -> BLOCK.
    (Analog T2, aber mit SC statt I als Build-Caller.)

    RED: guard_sdf_post_handoff.py existiert nicht oder erkennt SC-Load nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SC_orchestrate"},
        # kein _SDF_orchestrate_post -> Verletzung mit SC als Seam-Start
    ]
    proc, r = _run_guard_skill_load("_SDF_orchestrate", audit, enforce=True)
    assert proc.returncode == 2, (
        f"T9 sc-orchestrate-detected: SC-Load + kein Post-SDF + SDF-Resume -> "
        f"BLOCK erwartet (exit 2), war exit {proc.returncode}. "
        f"Guard erkennt SC-Build-Caller nicht als Seam-Start."
    )
    msg = r.get("message", "") + proc.stderr
    assert "_SDF_orchestrate_post" in msg or "Rufe Skill" in msg, (
        "T9: Recovery-Hint fehlt beim SC-Build-Caller-Block."
    )


# ---------------------------------------------------------------------------
# T10: enforce_false_warn — enforceProcess=false -> WARN + pass
# ---------------------------------------------------------------------------

def test_enforce_false_warn():
    """T10 (AK-6 enforce-false-warn): enforceProcess=false -> Guard WARNT (Meldung
    enthaelt Violation-Info) aber blockt NICHT (continue=True, exit 0).

    WARN-Modus erlaubt das Deployment mit expliziter Opt-out-Entscheidung (z.B.
    waehrend Umbau-Phase oder explizitem Bypass).

    RED: guard_sdf_post_handoff.py existiert nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        # kein Post-SDF -> Verletzung, aber enforceProcess=false -> nur WARN
    ]
    proc, r = _run_guard_skill_load("_SDF_orchestrate", audit, enforce=False)
    assert proc.returncode == 0, (
        f"T10 enforce-false-warn: enforceProcess=false -> kein Block (exit 0), "
        f"war exit {proc.returncode}. WARN-Modus darf nicht blocken."
    )
    assert r.get("continue") is True, (
        "T10: enforceProcess=false -> continue=True erwartet (WARN, kein Block)."
    )
    # Optionale Pruefung: Violation-Meldung SOLLTE trotzdem gesetzt sein
    msg = r.get("message", "")
    # Nur pruefen wenn message vorhanden (nicht alle Guards setzen message bei continue=True)
    if msg:
        assert "WARN" in msg or "SDF_POST_HANDOFF" in msg or "_SDF_orchestrate_post" in msg, (
            "T10: Wenn message gesetzt, sollte sie WARN oder Guard-Name enthalten."
        )


# ---------------------------------------------------------------------------
# Importierbarkeits-Pruefung (laeuft immer als naechstes nach file-not-found)
# ---------------------------------------------------------------------------

def test_guard_importable_and_has_core_symbols():
    """Structural check: guard_sdf_post_handoff.py muss importierbar sein und die
    Kern-Symbole aus der Spec exportieren (AK-2 Backend-Mapping).

    Failt im RED-State mit ImportError / ModuleNotFoundError weil die Datei fehlt.
    Nach GREEN: prueft ob _is_sdf_orchestrate_skill_load + post_sdf_ran_since_i_sc
    vorhanden sind (Spec §4.1, AK-2 Backend-Mapping).
    """
    spec = importlib.util.spec_from_file_location("guard_sdf_post_handoff", str(GUARD))
    assert spec is not None, (
        "guard_sdf_post_handoff.py nicht gefunden — importlib.util.spec_from_file_location "
        "gibt None zurueck. Datei existiert noch nicht (RED erwartet)."
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # loest ImportError / SyntaxError wenn Datei kaputt

    assert hasattr(mod, "_is_sdf_orchestrate_skill_load"), (
        "_is_sdf_orchestrate_skill_load fehlt in guard_sdf_post_handoff.py "
        "(Spec §4.1 TRIGGER A Detektion — RED erwartet)."
    )
    assert hasattr(mod, "post_sdf_ran_since_i_sc"), (
        "post_sdf_ran_since_i_sc fehlt in guard_sdf_post_handoff.py "
        "(Spec §4.1 Scan-Funktion, analog postroute_ran_since_a_pipeline — RED erwartet)."
    )


if __name__ == "__main__":
    tests = [
        test_happy_path_post_sdf_present,
        test_bypass_detect_no_post_sdf,
        test_terminate_no_fp,
        test_m1_no_fp,
        test_off_switch_global,
        test_off_switch_local,
        test_trigger_b_passthrough,
        test_audit_missing_fail_open,
        test_sc_orchestrate_detected,
        test_enforce_false_warn,
        test_guard_importable_and_has_core_symbols,
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
