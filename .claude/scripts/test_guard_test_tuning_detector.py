#!/usr/bin/env python3
"""Tests fuer guard_test_tuning_detector.py (BL-404 AK-4/AK-5/AK-6).

PreToolUse-Hook auf Edit/Write zu Test-Dateien.
Kern-Funktion: detect_test_tuning(tool_name, tool_input, batch_type=None)
  -> (is_violation: bool, hint: str | None)

Kat-A (Korrektheits-Tuning, VERBOTEN): Edit auf Test-Datei verschiebt
  einen VERHALTENS-Assert-Token (Output/State/Error-Code/Ops-Reihenfolge/
  Exception-Art/Return-Value in einem assert).
  -> (True, "Kat-A Verhaltens-Assert verschoben -> Korrektheit: Code fixen,
       Test unangetastet (INV-PROCESS-STRICT-2)")

Kat-B (Form-Kopplung, konditionell erlaubt):
  - batch_type=="refactor" + reiner Form-Edit MIT Report-Marker -> (False, None)
  - batch_type=="refactor" + Form-Edit OHNE Report-Marker -> flag (Report-Pflicht)
  - batch_type!="refactor" + Form-Edit -> strenger behandelt (True/flag)

AK-6 Heuristik-Grenze: Token-getarnter Behavior-Edit kann durchrutschen
  (dokumentierte Restluecke, Reviewer-Pflicht).

ALLE TESTS MUESSEN FAILEN — guard_test_tuning_detector.py existiert noch nicht.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_test_tuning_detector.py"

# --- Importversuch: guard gegen fehlende Datei (RED-Beweis via Assertion in Tests) ---
import importlib.util

_GUARD_MODULE = None
try:
    _spec = importlib.util.spec_from_file_location(
        "guard_test_tuning_detector", str(GUARD_SCRIPT)
    )
    if _spec is not None and _spec.loader is not None:
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _GUARD_MODULE = _mod
except (FileNotFoundError, ModuleNotFoundError):
    _GUARD_MODULE = None


def detect_test_tuning(tool_name, tool_input, batch_type=None):
    """Proxy zu guard_test_tuning_detector.detect_test_tuning.
    Raist AssertionError wenn Modul fehlt — jeder Test der diese Funktion
    aufruft wird mit klarer Fehlermeldung failen (RED-Zustand)."""
    assert _GUARD_MODULE is not None, (
        "guard_test_tuning_detector.py existiert nicht — RED-Zustand erwartet. "
        "GREEN-Worker muss die Datei anlegen."
    )
    return _GUARD_MODULE.detect_test_tuning(tool_name, tool_input, batch_type=batch_type)


# ─────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen fuer subprocess-basierte main()-Tests
# ─────────────────────────────────────────────────────────────────────────────

def _build_edit_event(file_path: str, old_string: str, new_string: str) -> dict:
    return {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": file_path,
            "old_string": old_string,
            "new_string": new_string,
        },
    }


def _run_guard(event: dict, enforce: bool = True,
               batch_type: str | None = None,
               audit_path: str | None = None) -> tuple:
    """Schreibt synthetisches _session_params.md (enforce) + optionalen
    OMNI_AUDIT_JSONL_OVERRIDE, setzt Env-Vars und ruft den Guard via
    subprocess. Gibt (proc, verdict_dict) zurueck."""
    env = os.environ.copy()

    # enforce-Gate via OMNI_SESSION_PARAMS
    sp = tempfile.NamedTemporaryFile(
        mode="w", suffix="_session_params.md", delete=False, encoding="utf-8"
    )
    sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
    sp.close()
    env["OMNI_SESSION_PARAMS"] = sp.name

    # batch_type via Env-Override (Guard liest OMNI_BATCH_TYPE)
    if batch_type is not None:
        env["OMNI_BATCH_TYPE"] = batch_type
    else:
        env.pop("OMNI_BATCH_TYPE", None)

    # audit redirect
    _tmp_audit = None
    if audit_path is not None:
        env["OMNI_AUDIT_JSONL_OVERRIDE"] = audit_path
    else:
        _tmp_audit = tempfile.NamedTemporaryFile(
            mode="w", suffix="_audit.jsonl", delete=False, encoding="utf-8"
        )
        _tmp_audit.close()
        env["OMNI_AUDIT_JSONL_OVERRIDE"] = _tmp_audit.name

    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env=env,
    )

    Path(sp.name).unlink(missing_ok=True)
    if _tmp_audit is not None:
        Path(_tmp_audit.name).unlink(missing_ok=True)

    verdict = (
        json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    )
    return proc, verdict


# ─────────────────────────────────────────────────────────────────────────────
# T-ak5-kat-a-blocked
# Kat-A: Verhaltens-Assert-Edit auf eine Test-Datei -> (True, hint)
# ─────────────────────────────────────────────────────────────────────────────

def test_kat_a_behavior_assert_edit_detected():
    """T-ak5-kat-a-blocked: Edit auf test_foo.py verschiebt einen Wert in
    einem assertEqual -> Kat-A-Verdacht, detect_test_tuning gibt (True, hint).
    MUSS FAILEN — Modul fehlt."""
    tool_input = {
        "file_path": "test_foo.py",
        "old_string": 'assertEqual(out, "X")',
        "new_string": 'assertEqual(out, "Y")',
    }
    is_violation, hint = detect_test_tuning("Edit", tool_input, batch_type=None)
    assert is_violation is True, (
        f"Kat-A Verhaltens-Assert-Edit muss als Violation erkannt werden, war {is_violation}"
    )
    assert hint is not None, "hint darf bei Violation nicht None sein"
    assert "INV-PROCESS-STRICT-2" in hint, (
        f"hint muss INV-PROCESS-STRICT-2 enthalten, war: {hint!r}"
    )


def test_kat_a_assert_return_value_change_detected():
    """Kat-A: Return-Value in assert-Statement veraendert -> Violation.
    MUSS FAILEN — Modul fehlt."""
    tool_input = {
        "file_path": "tests/test_service.py",
        "old_string": "assert result == 5",
        "new_string": "assert result == 7",
    }
    is_violation, hint = detect_test_tuning("Edit", tool_input, batch_type=None)
    assert is_violation is True, (
        f"Aenderung von Return-Value (5->7) in assert muss Kat-A sein, war {is_violation}"
    )


def test_kat_a_error_code_change_detected():
    """Kat-A: Error-Code-Wert in Assertion veraendert -> Violation.
    MUSS FAILEN — Modul fehlt."""
    tool_input = {
        "file_path": "test_handler.py",
        "old_string": "assert response.status_code == 200",
        "new_string": "assert response.status_code == 404",
    }
    is_violation, hint = detect_test_tuning("Edit", tool_input, batch_type=None)
    assert is_violation is True, (
        f"Status-Code-Aenderung (200->404) muss Kat-A sein, war {is_violation}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T-ak4-refactor-form-pass
# batch_type=refactor + Kat-B Form-Edit (Schwellwert) MIT Report-Marker -> (False, None)
# ─────────────────────────────────────────────────────────────────────────────

def test_kat_b_form_edit_refactor_with_report_passes():
    """T-ak4-refactor-form-pass: Im Refactor-Kontext ist ein Schwellwert-Edit
    (Kat-B) MIT Report-Marker legitim -> (False, None).
    MUSS FAILEN — Modul fehlt."""
    assert detect_test_tuning is not None
    # Report-Marker: ein Kommentar oder Marker wie "# BL-404-REPORT:" signalisiert
    # dass der Bearbeiter eine Einzel-Meldung erzeugt (AK-3-Pflicht erfuellt).
    tool_input = {
        "file_path": "test_threshold.py",
        "old_string": "assert count <= 5  # BL-404-REPORT: Schwellwert 5->10 wegen OldClass-Umbenennung",
        "new_string": "assert count <= 10  # BL-404-REPORT: Schwellwert 5->10 wegen OldClass-Umbenennung",
    }
    is_violation, hint = detect_test_tuning("Edit", tool_input, batch_type="refactor")
    assert is_violation is False, (
        f"Kat-B Schwellwert-Edit + Report-Marker im Refactor-Kontext muss durchgelassen "
        f"werden (False), war {is_violation} hint={hint!r}"
    )
    assert hint is None, f"hint muss None sein bei legalem Kat-B-Edit, war {hint!r}"


# ─────────────────────────────────────────────────────────────────────────────
# T-ak4-nonrefactor-stricter
# batch_type=None + selber Form-Edit -> strenger (True/flag)
# ─────────────────────────────────────────────────────────────────────────────

def test_kat_b_form_edit_nonrefactor_stricter():
    """T-ak4-nonrefactor-stricter: Derselbe Schwellwert-Edit ausserhalb Refactor-Kontext
    (batch_type=None) -> strenger behandelt (True oder flag).
    MUSS FAILEN — Modul fehlt."""
    tool_input = {
        "file_path": "test_threshold.py",
        "old_string": "assert count <= 5  # BL-404-REPORT: Schwellwert 5->10 wegen OldClass-Umbenennung",
        "new_string": "assert count <= 10  # BL-404-REPORT: Schwellwert 5->10 wegen OldClass-Umbenennung",
    }
    is_violation, hint = detect_test_tuning("Edit", tool_input, batch_type=None)
    assert is_violation is True, (
        f"Schwellwert-Edit (Kat-B) ausserhalb Refactor (batch_type=None) muss als "
        f"Violation erkannt werden, war {is_violation}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T-ak3-form-without-report
# batch_type=refactor + Form-Edit OHNE Report-Marker -> flag (Report-Pflicht)
# ─────────────────────────────────────────────────────────────────────────────

def test_kat_b_form_edit_refactor_without_report_flagged():
    """T-ak3-form-without-report: Im Refactor-Kontext ist Kat-B ohne Report-Marker
    eine Verletzung der Einzel-Meldungs-Pflicht (AK-3).
    MUSS FAILEN — Modul fehlt."""
    tool_input = {
        "file_path": "test_threshold.py",
        "old_string": "assert count <= 5",
        "new_string": "assert count <= 10",
    }
    is_violation, hint = detect_test_tuning("Edit", tool_input, batch_type="refactor")
    assert is_violation is True, (
        f"Kat-B-Edit im Refactor-Kontext OHNE Report-Marker muss als Verletzung "
        f"(Report-Pflicht) erkannt werden, war {is_violation}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T-ak5-non-test-file-pass
# Edit auf Nicht-Test-Datei -> (False, None) — Guard nur fuer Test-Dateien
# ─────────────────────────────────────────────────────────────────────────────

def test_non_test_file_passes():
    """T-ak5-non-test-file-pass: Edit auf service.py (kein test_*.py) geht durch.
    MUSS FAILEN — Modul fehlt."""
    tool_input = {
        "file_path": "service.py",
        "old_string": 'assertEqual(out, "X")',
        "new_string": 'assertEqual(out, "Y")',
    }
    is_violation, hint = detect_test_tuning("Edit", tool_input, batch_type=None)
    assert is_violation is False, (
        f"Edit auf Nicht-Test-Datei (service.py) muss durchgelassen werden, war {is_violation}"
    )
    assert hint is None


def test_spec_file_is_test_file():
    """Edit auf foo.spec.js (Test-Datei via .spec. Pfad-Muster) wird als Test-Datei erkannt.
    MUSS FAILEN — Modul fehlt."""
    tool_input = {
        "file_path": "components/foo.spec.js",
        "old_string": "expect(result).toBe('X')",
        "new_string": "expect(result).toBe('Y')",
    }
    is_violation, hint = detect_test_tuning("Edit", tool_input, batch_type=None)
    assert is_violation is True, (
        f".spec.-Datei muss als Test-Datei erkannt werden und Kat-A blocken, war {is_violation}"
    )


def test_suffix_test_py_is_test_file():
    """foo_test.py (*_test.py-Muster) wird als Test-Datei erkannt.
    MUSS FAILEN — Modul fehlt."""
    tool_input = {
        "file_path": "bar_test.py",
        "old_string": "assert result == 5",
        "new_string": "assert result == 9",
    }
    is_violation, hint = detect_test_tuning("Edit", tool_input, batch_type=None)
    assert is_violation is True, (
        f"*_test.py muss als Test-Datei erkannt werden, war {is_violation}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# T-ak6-camouflage-slips
# Getarnter Behavior-Edit (Form-Vokabular) rutscht durch -> (False, None)
# Dokumentierte Restluecke (AK-6 Heuristik-Grenze, Reviewer-Pflicht)
# ─────────────────────────────────────────────────────────────────────────────

def test_camouflaged_behavior_edit_slips_through():
    """T-ak6-camouflage-slips: Behavior-Edit mit reinem Form-Vokabular (kein
    Verhaltens-Token-Match) rutscht durch den heuristischen Guard.
    Dies ist die DOKUMENTIERTE RESTLUECKE (AK-6) — kein false-GREEN-Versteck.

    AK-6 Restluecke: ein Angreifer kann Verhaltens-Tokens mit Form-Vokabular
    umschreiben (z.B. 'OldClass' statt 'assertEqual(out, X)'). Der Guard
    erkennt das nicht. Reviewer-Pflicht bleibt bestehen.

    MUSS FAILEN — Modul fehlt."""
    assert detect_test_tuning is not None
    # "OldClass" und "NewClass" sind Kat-B-Vokabular (Klassen-Umbenennung).
    # Aber die Assertion stellt tatsaechlich ein anderes Verhalten sicher.
    # Der Guard sieht nur Form-Vokabular und laesst es durch.
    tool_input = {
        "file_path": "test_migration.py",
        "old_string": "assert isinstance(result, OldClass)",
        "new_string": "assert isinstance(result, NewClass)",
    }
    is_violation, hint = detect_test_tuning("Edit", tool_input, batch_type=None)
    # Guard laesst durch (False) — das ist die dokumentierte Luecke
    assert is_violation is False, (
        "AK-6 Restluecke: getarnter Behavior-Edit mit Form-Vokabular soll "
        "durchrutschen (False erwartet). Wenn dieser Test faengt, pruefe ob "
        "der Guard zu aggressiv ist (False-Positives bei legitimen Kat-B-Edits)."
    )
    # hint muss None sein (kein Block, kein Report-Trigger hier)
    assert hint is None


# ─────────────────────────────────────────────────────────────────────────────
# T-ak5-main-enforce-true (subprocess)
# PreToolUse Kat-A-Edit + enforce=true -> continue=false + audit TEST_TUNING_BLOCKED
# ─────────────────────────────────────────────────────────────────────────────

def test_main_enforce_true_kat_a_blocks():
    """T-ak5-main-enforce-true: main() via subprocess, Kat-A-Edit + enforce=true
    -> continue=false + Audit-Event TEST_TUNING_BLOCKED.
    MUSS FAILEN — Modul fehlt (FileNotFoundError/ModuleNotFoundError)."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_audit.jsonl", delete=False, encoding="utf-8"
    ) as af:
        audit_path = af.name

    event = _build_edit_event(
        file_path="test_foo.py",
        old_string='assertEqual(out, "X")',
        new_string='assertEqual(out, "Y")',
    )
    proc, verdict = _run_guard(event, enforce=True, batch_type=None, audit_path=audit_path)

    try:
        assert verdict.get("continue") is False, (
            f"enforce=true + Kat-A-Edit muss continue=false liefern, war {verdict}"
        )
        # Audit-Event pruefen
        audit_events = []
        with open(audit_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    audit_events.append(json.loads(line))
        event_types = [e.get("event", e.get("violation", "")) for e in audit_events]
        assert any("TEST_TUNING_BLOCKED" in t for t in event_types), (
            f"Audit-Event TEST_TUNING_BLOCKED fehlt, gefunden: {event_types}"
        )
    finally:
        Path(audit_path).unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# T-ak5-main-enforce-false
# Selbes Kat-A + enforce=false -> continue=true (WARN, kein Block)
# ─────────────────────────────────────────────────────────────────────────────

def test_main_enforce_false_kat_a_warns_only():
    """T-ak5-main-enforce-false: enforce=false -> continue=true (WARN, kein BLOCK).
    MUSS FAILEN — Modul fehlt."""
    event = _build_edit_event(
        file_path="test_foo.py",
        old_string='assertEqual(out, "X")',
        new_string='assertEqual(out, "Y")',
    )
    proc, verdict = _run_guard(event, enforce=False, batch_type=None)
    assert verdict.get("continue") is True, (
        f"enforce=false + Kat-A-Edit muss continue=true (WARN) liefern, war {verdict}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# fail-open: Exception im Guard -> continue=true (kein crash-Block)
# ─────────────────────────────────────────────────────────────────────────────

def test_fail_open_on_broken_input():
    """Kaputtes JSON-Event -> Guard faellt OPEN (continue=true).
    MUSS FAILEN — guard_test_tuning_detector.py existiert nicht."""
    assert GUARD_SCRIPT.exists(), (
        f"guard_test_tuning_detector.py existiert nicht — RED-Zustand. "
        f"GREEN-Worker muss {GUARD_SCRIPT} anlegen."
    )
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input="NOT_VALID_JSON",
        capture_output=True,
        text=True,
    )
    # fail-open: entweder exit 0 mit continue=true oder zumindest kein exit != 0 + block
    if proc.stdout.strip():
        verdict = json.loads(proc.stdout.strip())
        assert verdict.get("continue") is True, (
            f"fail-open erwartet (continue=true bei Exception), war {verdict}"
        )
    # kein harter Crash ohne Ausgabe erwartet
