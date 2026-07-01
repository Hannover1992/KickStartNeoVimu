#!/usr/bin/env python3
"""
Claude Code Hook — Test-Tuning-Detector (Guard-Enforcement BL-404 AK-4/AK-5/AK-6).

PreToolUse-Hook auf Edit/Write zu Test-Dateien. Faengt das false-GREEN-Muster
"Test an den Code anpassen statt Code an den Test" (INV-PROCESS-STRICT-2).

Kern-Funktion: detect_test_tuning(tool_name, tool_input, batch_type=None)
  -> (is_violation: bool, hint: str | None)

Kat-A (Korrektheits-Tuning, VERBOTEN):
  Edit auf eine Test-Datei verschiebt einen VERHALTENS-Assert-Token (Output/State/
  Error-Code/Return-Value/Exception-Art in einem assert). z.B. assertEqual(out,"X")
  -> assertEqual(out,"Y"), assert result == 5 -> 7, status_code == 200 -> 404.
  -> (True, "Kat-A Verhaltens-Assert verschoben -> ... (INV-PROCESS-STRICT-2)")

Kat-B (Form-Kopplung, konditionell erlaubt):
  reiner Form-Token-Edit (Schwellwert-Zahl, OldClass/NewClass, isinstance) OHNE
  Verhaltens-Token.
    - batch_type=="refactor" + Report-Marker -> (False, None)  [AK-4-Gate]
    - batch_type=="refactor" OHNE Report-Marker -> (True, ...)  [AK-3 Report-Pflicht]
    - batch_type!="refactor" -> (True, ...)  [strenger ausserhalb Refactor]

AK-6 Restluecke (BEWUSST dokumentiert):
  Ein getarnter Behavior-Edit der NUR Form-Vokabular nutzt (reiner Identifier-Swap
  isinstance(OldClass)->isinstance(NewClass), keine Schwellwert-Zahl, kein Verhaltens-
  Token) rutscht durch -> (False, None). Token-Tarnung kann durchrutschen,
  Reviewer-Pflicht bleibt (kein false-GREEN-Versteck).

enforceProcess=true (Default): Kat-A -> continue=false + Audit TEST_TUNING_BLOCKED.
enforceProcess=false: nur WARN (continue=true).
Exception -> fail-open (continue=true).
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
LOG_FILE = ROOT_DIR / ".hook_debug.log"

# Test-Datei-Muster: test_*.py / *_test.py / *.spec.* (auch .spec.js/.spec.ts)
_TEST_FILE_RE = re.compile(
    r'(^|[\\/])test_[^\\/]*\.py$'
    r'|_test\.py$'
    r'|\.spec\.',
    re.IGNORECASE,
)

# Verhaltens-Assert-Token (Kat-A): Gleichheits-/Output-/Error-Semantik im assert.
# isinstance ist NICHT hier (siehe AK-6 Restluecke — Form-Token, suppress Kat-A).
_BEHAVIOR_TOKEN_RES = [
    re.compile(r'\bassertEqual\b', re.IGNORECASE),
    re.compile(r'\bassertNotEqual\b', re.IGNORECASE),
    re.compile(r'\bassertRaises\b', re.IGNORECASE),
    re.compile(r'\bassert\b.*[!=]=', re.IGNORECASE),   # assert x == / != y
    re.compile(r'\bstatus_code\b', re.IGNORECASE),
    re.compile(r'\.toBe\b', re.IGNORECASE),
    re.compile(r'\.toEqual\b', re.IGNORECASE),
]
# Form-Token (Kat-B / Tarnung): Typ-/Klassen-/Schwellwert-Vokabular ohne Verhaltens-Semantik.
_ISINSTANCE_RE = re.compile(r'\bisinstance\b', re.IGNORECASE)
# Schwellwert-Vergleich (<=, >=, <, > mit Zahl) — flaggbare Kat-B-Form (kein == Verhalten).
_THRESHOLD_RE = re.compile(r'(<=|>=|<|>)\s*\d', re.IGNORECASE)
# Report-Marker (AK-3): signalisiert Einzel-Meldung erzeugt.
_REPORT_MARKER_RE = re.compile(r'#\s*(BL-404-REPORT|FORM-REPORT)\s*:', re.IGNORECASE)

_KAT_A_HINT = (
    "Kat-A Verhaltens-Assert verschoben -> Korrektheit: Code fixen, "
    "Test unangetastet (INV-PROCESS-STRICT-2)"
)
_KAT_B_HINT = (
    "Kat-B Form-Edit an Test ohne Report -> AK-3 Einzel-Meldungs-Pflicht "
    "(# BL-404-REPORT: / # FORM-REPORT:), nur im Refactor-Kontext legitim"
)


def _is_test_file(file_path):
    """True wenn der Pfad ein Test-Datei-Muster matcht (test_*.py / *_test.py / *.spec.*)."""
    if not file_path:
        return False
    return bool(_TEST_FILE_RE.search(str(file_path)))


def _has_behavior_token(text):
    """True wenn der Text einen Verhaltens-Assert-Token enthaelt (Kat-A-Signal)."""
    if not text:
        return False
    return any(r.search(text) for r in _BEHAVIOR_TOKEN_RES)


def detect_test_tuning(tool_name, tool_input, batch_type=None):
    """Erkennt Test-Tuning (Korrektheits-Verschiebung am Test statt Code-Fix).

    Returns (is_violation: bool, hint: str | None).

    Kat-A: Verhaltens-Assert verschoben -> immer Violation.
    Kat-B: reiner Form-Edit -> refactor+Report -> OK; sonst Violation.
    AK-6 Restluecke: getarnter Identifier-Swap (isinstance(OldClass)->NewClass,
      keine Schwellwert-Zahl, kein Verhaltens-Token) rutscht durch -> (False, None).
      DOKUMENTIERTE HEURISTIK-RESTLUECKE — Token-Tarnung kann durchrutschen,
      Reviewer-Pflicht (kein false-GREEN-Versteck).
    """
    if not isinstance(tool_input, dict):
        return (False, None)

    file_path = tool_input.get("file_path", "")
    if not _is_test_file(file_path):
        return (False, None)

    old_string = tool_input.get("old_string") or ""
    new_string = tool_input.get("new_string") or ""
    # Write-Tool: kein old/new, sondern content. Dann ganzen content als new betrachten.
    if not old_string and not new_string:
        content = tool_input.get("content") or ""
        new_string = content
    combined = old_string + "\n" + new_string

    # Kein effektiver Inhaltswechsel -> nichts zu pruefen.
    if old_string and new_string and old_string == new_string:
        return (False, None)

    has_behavior = _has_behavior_token(combined)
    has_isinstance = bool(_ISINSTANCE_RE.search(combined))
    has_threshold = bool(_THRESHOLD_RE.search(combined))
    has_report = bool(_REPORT_MARKER_RE.search(combined))

    # --- Kat-A: Verhaltens-Assert verschoben (VERBOTEN) ---
    # isinstance suppress: ein reiner isinstance-Edit ist Form-Token (AK-6 Tarnung),
    # selbst wenn es in einem assert steht (assert isinstance(...) hat kein ==).
    if has_behavior and not has_isinstance:
        return (True, _KAT_A_HINT)

    # --- AK-6 Restluecke: getarnter Identifier-Swap ---
    # isinstance(OldClass) -> isinstance(NewClass): Form-Vokabular, keine Schwellwert-
    # Zahl, kein Verhaltens-Token -> rutscht durch.
    # AK-6 dokumentierte Heuristik-Restluecke — Token-Tarnung kann durchrutschen,
    # Reviewer-Pflicht (kein false-GREEN-Versteck).
    if has_isinstance and not has_threshold:
        return (False, None)

    # --- Kat-B: reiner Form-Edit (Schwellwert-Zahl) ---
    if has_threshold:
        if batch_type == "refactor":
            if has_report:
                return (False, None)          # AK-4-Gate: refactor + Report -> legitim
            return (True, _KAT_B_HINT)          # AK-3: refactor ohne Report -> Report-Pflicht
        # Ausserhalb Refactor strenger: Form-Edit am Test ist Verdacht.
        return (True, _KAT_B_HINT)

    # Kein Verhaltens-Token, kein Form-Signal -> kein Tuning erkennbar.
    return (False, None)


def read_enforce_process():
    """Liest enforceProcess aus _session_params.md. Default: true.

    Aufloesung: OMNI_SESSION_PARAMS (Test-Override) > vault-resolved > Default true.
    """
    _enforce_re = re.compile(r'\*\*enforceProcess:\*\*\s*(true|false)', re.IGNORECASE)
    sp = os.environ.get("OMNI_SESSION_PARAMS")
    if sp and Path(sp).exists():
        try:
            content = Path(sp).read_text(encoding="utf-8", errors="replace")
            m = _enforce_re.search(content)
            if m:
                return m.group(1).lower() == "true"
        except Exception:
            pass
        return True  # Temp-file vorhanden aber kein Match -> konservativ enforce
    # Fallback: lokaler Session-Params-Pfad
    fallback = ROOT_DIR / ".claude" / "analysis" / "_session_params.md"
    try:
        if fallback.exists():
            content = fallback.read_text(encoding="utf-8", errors="replace")
            m = _enforce_re.search(content)
            if m:
                return m.group(1).lower() == "true"
    except Exception:
        pass
    return True  # Default: enforce


def append_guard_log(violation_type, details, blocked):
    """Appende Violation an GUARD_LOG-Datei (best-effort)."""
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = f"- [{timestamp}] **{violation_type}** [{action}]: {details}\n"
        with open(GUARD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def append_audit_event(event_name, details, blocked):
    """Schreibt ein Audit-Event (TEST_TUNING_BLOCKED / TEST_TUNING_WARNED).

    OMNI_AUDIT_JSONL_OVERRIDE (Test-Override) leitet die Zeile in einen isolierten
    temp-Pfad um, sonst .claude/audit/audit.jsonl.
    """
    try:
        event = {
            "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "event": event_name,
            "level": "BLOCK" if blocked else "WARN",
            "violation": event_name,
            "details": details,
            "ctx": {"guard": "test_tuning_detector"},
        }
        override = os.environ.get("OMNI_AUDIT_JSONL_OVERRIDE")
        if override:
            audit_path = Path(override)
        else:
            audit_dir = ROOT_DIR / ".claude" / "audit"
            audit_dir.mkdir(parents=True, exist_ok=True)
            audit_path = audit_dir / "audit.jsonl"
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass


def main():
    # Globaler Owner-Kill-Switch (BL-223): OMNI_ENFORCE_ALL_OFF -> Guard aus.
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(json.dumps({"continue": True}))
        return
    try:
        hook_data = json.loads(sys.stdin.read())
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        if tool_name not in ("Edit", "Write"):
            print(json.dumps({"continue": True}))
            return

        # batch_type-Override via Env (Tests / Motor setzen OMNI_BATCH_TYPE).
        batch_type = os.environ.get("OMNI_BATCH_TYPE") or None

        is_violation, hint = detect_test_tuning(tool_name, tool_input, batch_type=batch_type)
        if not is_violation:
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()
        details = hint or "Test-Tuning erkannt"
        if enforce:
            append_guard_log("TEST_TUNING_BLOCKED", details, True)
            append_audit_event("TEST_TUNING_BLOCKED", details, True)
            warning = (
                "[GUARD-VIOLATION] TEST_TUNING_BLOCKED: Test an den Code angepasst "
                "statt Code an den Test.\n  -> FIX: " + details
                + ". BLOCKIERT (enforceProcess=true)."
            )
            print(json.dumps({"continue": False, "message": warning}))
        else:
            append_guard_log("TEST_TUNING_WARNED", details, False)
            append_audit_event("TEST_TUNING_WARNED", details, False)
            warning = (
                "[GUARD-WARN] TEST_TUNING: " + details
                + ". WARNED (enforceProcess=false Opt-out)."
            )
            print(json.dumps({"continue": True, "message": warning}))

    except Exception as e:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_test_tuning_detector Error: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))  # fail-open


if __name__ == "__main__":
    main()
