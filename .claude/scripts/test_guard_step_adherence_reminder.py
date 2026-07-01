#!/usr/bin/env python3
"""Tests fuer den C-4 Step-Adherence-Reminder-Hook (BL-227 Sub-Batch C-4).

SUT: guard_step_adherence_reminder.py — PreToolUse:Skill-Hook der bei Load eines
nicht-motorisierten `_X_orchestrate`-Ziel-Orchestrators (A->IDF / IDF->SDF /
SC->Post / I->SDF_post) den Handschuhwechsel-Reminder injiziert.

Verdrahtung der fertigen Bausteine:
  C-1  handover_reminder_core.build_reminder(target, next_step, handoff_block)
  C-2  session_params_resolver.resolve_param("step_adherence_reminder")
  C-3  handover_reminder_gate.modus_gate(modus, toggle)

AK-Abdeckung:
  AK-4   Hook kennt alle betroffenen Ziel-Orchestratoren (Trigger-Liste vollstaendig).
  AK-11  Scope-Gate: NUR nicht-motorisierte Pfade; non-orchestrator-Skill -> nichts;
         next_step (k+1)-Ableitung; nicht ableitbar -> fail-open.
  AK-12  FAIL-OPEN PFLICHT: Reminder != Enforcement. NIE Block, NIE exit!=0,
         NIE {"continue": false}. Exception/fehlender State -> still nichts, exit 0.
  AK-13  dispatch_implement.js + guard_geist9* BLEIBEN UNVERAENDERT (Diff-Disziplin).

Hook-Vertrag (stdin = PreToolUse-Event JSON, stdout = JSON):
  - Kein Skill-Tool / Nicht-Trigger-Skill / toggle=off / Modus no-fire / kein State
      -> {"continue": true}  OHNE additionalContext.
  - fire (toggle=on + M3 + Trigger-Skill + ableitbarer next_step)
      -> {"continue": true, "additionalContext": "<step-reminder ...>...</step-reminder>..."}.
  - JEDER Fehler -> {"continue": true}, exit 0.

Befehl: py -3 -m pytest test_guard_step_adherence_reminder.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.absolute()
HOOK = SCRIPT_DIR / "guard_step_adherence_reminder.py"
ROOT_DIR = SCRIPT_DIR.parent.parent


def _run(event, env_extra=None):
    """Fuehre den Hook als echten Subprozess (wie der Harness) aus.

    Returns (returncode, parsed_stdout_or_None, raw_stdout).
    """
    import os
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    out = proc.stdout.strip()
    parsed = None
    try:
        parsed = json.loads(out) if out else None
    except json.JSONDecodeError:
        parsed = None
    return proc.returncode, parsed, out


def _skill_event(skill_name):
    return {"tool_name": "Skill", "tool_input": {"skill": skill_name}}


# Test-Hooks ueber Env: Toggle + Modus deterministisch setzen (kein Vault-Read).
# Der Hook MUSS diese Test-Overrides honorieren (sonst nicht unit-testbar).
ON_M3 = {"OMNI_SAR_TEST_TOGGLE": "on", "OMNI_SAR_TEST_MODUS": "M3"}
ON_M1 = {"OMNI_SAR_TEST_TOGGLE": "on", "OMNI_SAR_TEST_MODUS": "M1"}
OFF_M3 = {"OMNI_SAR_TEST_TOGGLE": "off", "OMNI_SAR_TEST_MODUS": "M3"}
ON_M2 = {"OMNI_SAR_TEST_TOGGLE": "on", "OMNI_SAR_TEST_MODUS": "M2"}


# ---------------------------------------------------------------------------
# Ring 0 — Sicherheits-Kanarienvogel: FAIL-OPEN (AK-12)
# ---------------------------------------------------------------------------

def test_exists():
    """Der Hook-Datei existiert."""
    assert HOOK.exists(), f"Hook fehlt: {HOOK}"


def test_failopen_garbage_stdin_exit0_no_block():
    """AK-12: kaputter stdin -> exit 0, {"continue": true}, kein Block."""
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input="}{ NOT JSON",
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, f"exit != 0 bei garbage: {proc.returncode}"
    parsed = json.loads(proc.stdout.strip())
    assert parsed.get("continue") is not False, "Hook hat geblockt (continue=false)!"


def test_failopen_empty_stdin_exit0():
    """AK-12: leerer stdin -> exit 0, kein Block."""
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input="", capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0
    parsed = json.loads(proc.stdout.strip())
    assert parsed.get("continue") is not False


def test_never_emits_block_even_when_firing():
    """AK-12: selbst im fire-Fall NIE continue=false / exit!=0."""
    rc, parsed, _ = _run(_skill_event("_IDF_orchestrate"), ON_M3)
    assert rc == 0
    assert parsed.get("continue") is not False


# ---------------------------------------------------------------------------
# Scope-Gate (AK-11): non-orchestrator / nicht-Skill -> nichts
# ---------------------------------------------------------------------------

def test_non_skill_tool_passthrough():
    """Nicht-Skill-Tool -> {"continue": true}, kein additionalContext."""
    rc, parsed, _ = _run({"tool_name": "Read", "tool_input": {"file_path": "x"}}, ON_M3)
    assert rc == 0
    assert "additionalContext" not in parsed


def test_non_orchestrator_skill_no_fire():
    """AK-11: Nicht-Orchestrator-Skill (Berater) -> kein Reminder."""
    rc, parsed, _ = _run(_skill_event("_SDF_berater_modusEntscheidung"), ON_M3)
    assert "additionalContext" not in parsed


def test_motorized_path_not_triggered():
    """AK-11: dispatch_implement-interner Pfad ist KEIN Skill-Load eines Ziel-
    Orchestrators -> kein Reminder (Motor-Pfad ausgeschlossen)."""
    rc, parsed, _ = _run(_skill_event("dispatch_implement"), ON_M3)
    assert "additionalContext" not in parsed


# ---------------------------------------------------------------------------
# Toggle-Gate (AK-5 via C-2) + Modus-Gate (AK-9 via C-3)
# ---------------------------------------------------------------------------

def test_toggle_off_no_fire():
    """toggle=off -> KEIN Reminder, auch bei M3 + Trigger-Skill."""
    rc, parsed, _ = _run(_skill_event("_IDF_orchestrate"), OFF_M3)
    assert "additionalContext" not in parsed


def test_modus_m1_no_fire():
    """AK-9: M1 -> kein Reminder, auch bei toggle=on + Trigger-Skill."""
    rc, parsed, _ = _run(_skill_event("_IDF_orchestrate"), ON_M1)
    assert "additionalContext" not in parsed


# ---------------------------------------------------------------------------
# Fire-Fall (AK-4 + AK-11): alle Trigger-Orchestratoren feuern bei on+M3
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("skill", [
    "_IDF_orchestrate",
    "_SDF_orchestrate",
    "_Post_orchestrate",
    "_SDF_orchestrate_post",
])
def test_fire_injects_reminder_all_targets(skill):
    """AK-4/AK-11: jeder nicht-motorisierte Ziel-Orchestrator feuert bei on+M3.

    Injektion ist XML-step-reminder (C-1-Format) + Sandwiching + ACK-Feld.
    """
    rc, parsed, _ = _run(_skill_event(skill), ON_M3)
    assert rc == 0
    ac = parsed.get("additionalContext")
    assert ac, f"kein additionalContext fuer {skill}"
    assert "<step-reminder" in ac
    assert 'required="true"' in ac  # ACK-Pflichtfeld (AK-3)
    # Sandwiching (AK-3): step-reminder erscheint mind. zweimal.
    assert ac.count("<step-reminder") >= 2, "Sandwiching fehlt"


def test_fire_progressive_disclosure_single_step():
    """AK-2/AK-11: GENAU 1 Step (k+1) — nicht die volle Liste.

    Jeder der beiden Sandwich-Bloecke kapselt denselben einzelnen Step.
    Es gibt also genau 2 step-reminder-Bloecke (vor + nach), nicht n>1 verschiedene.
    """
    rc, parsed, _ = _run(_skill_event("_IDF_orchestrate"), ON_M3)
    ac = parsed["additionalContext"]
    assert ac.count("<step-reminder") == 2  # genau Sandwich-Doppel eines Steps


# ---------------------------------------------------------------------------
# next_step (k+1)-Ableitung nicht moeglich -> fail-open (AK-11/AK-12)
# ---------------------------------------------------------------------------

def test_modus_not_derivable_fail_open():
    """AK-11/AK-12: kein Modus ableitbar (kein Test-Override, kein State)
    -> fail-open, kein Reminder, kein Block."""
    # toggle on, aber Modus bewusst leer -> Hook muss aus State lesen; im Test
    # ohne Vault/Manifest ist nichts ableitbar -> no-fire.
    rc, parsed, _ = _run(
        _skill_event("_IDF_orchestrate"),
        {"OMNI_SAR_TEST_TOGGLE": "on", "OMNI_SAR_TEST_MODUS": ""},
    )
    assert rc == 0
    assert parsed.get("continue") is not False
    assert "additionalContext" not in parsed


# ---------------------------------------------------------------------------
# AK-13: Motor + Hooks unveraendert (Diff-Disziplin)
# ---------------------------------------------------------------------------

def test_dispatch_and_geist9_files_present_unmodified_by_hook():
    """AK-13: der Hook importiert/aendert weder dispatch_implement.js noch geist9*.

    Statische Pruefung: der Hook-Quelltext referenziert diese Dateien NICHT
    schreibend (kein Edit/Write-Pfad). Read-only Import von C-1/C-2/C-3 erlaubt.
    """
    src = HOOK.read_text(encoding="utf-8")
    # Doku-Erwaehnung im Docstring ist erlaubt (markiert die Diff-Disziplin);
    # verboten ist ein WRITE-/EXEC-Pfad auf diese Dateien. Pruefe daher auf
    # gefaehrliche Muster, nicht auf das blosse Vorkommen des Strings.
    forbidden = ["dispatch_implement", "subprocess", "guard_geist9"]
    # AST: sammle alle Identifier (Imports, Namen, Attribute, Call-Targets) — also
    # den AUSFUEHRBAREN Bezug. Docstrings/Kommentare sind String-Konstanten und
    # zaehlen NICHT (deren blosse Mention = erlaubte Diff-Disziplin-Doku).
    import ast
    tree = ast.parse(src)
    idents = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                idents.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            idents.add(node.module or "")
            for a in node.names:
                idents.add(a.name)
        elif isinstance(node, ast.Name):
            idents.add(node.id)
        elif isinstance(node, ast.Attribute):
            idents.add(node.attr)
    joined = " ".join(idents)
    for pat in forbidden:
        assert pat not in joined, f"Hook hat verbotenen Write/Exec-Pfad: {pat}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
