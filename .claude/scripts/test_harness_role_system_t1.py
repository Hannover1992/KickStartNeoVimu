#!/usr/bin/env python3
"""test_harness_role_system_t1.py — BL-227 Sub-Batch C-5 (AK-14): Traeger/Harness-Test (T1/F12).

Verifiziert die EPISTEMISCHE Kern-Unbekannte von BL-227 (srs=100, W-TRAEGER-2 / OQ-4):
**Kommt die Hook-`additionalContext`-Ausgabe tatsaechlich als mid-conversation
{role:system} `<system-reminder>` beim Agenten an — und traegt damit die
Step-Adherence-Praeventions-Schicht (L3)?**

Traeger-Entscheidung (siehe pileOfMud/BL-227-traeger-decision-hook.md + 2_Model/
adherence_research.md): Der Reminder ist ein **PreToolUse:Skill-Hook**, KEIN Skill-
Berater. Begruendung (3 unabhaengige Belege):
  1. Live-Observation: mid-conv `<system-reminder>`-Bloecke werden vom Harness/Hooks
     injiziert. Ein Skill-Berater kann KEINE system-message einschiessen — nur Hooks
     (`additionalContext` aus PreToolUse) koennen das (W-TRAEGER-1).
  2. C-1-OBSERVE1: die Lese-/Wirk-Seite (System-Block wird prioritaer gelesen) ist
     live belegt; T1 (C-5) verifiziert die Schreib-Seite (Hook-Output-Format).
  3. geist9/9b/post-gap-Praezedenz: PreToolUse-Hooks im selben Repo geben genau
     `{"continue": true, "additionalContext": ...}` aus → der Harness rendert das
     als mid-conv system-reminder (vgl. guard_post_gap_sequence.py:331-336).

DAHER ist die T1-Verifikation der **Output-Format-/Schreib-Pfad-Test** des Hooks:
  - Stage 1 (Unit): der Hook-Output hat das korrekte Injektions-Schema fuer den
    system-reminder-Kanal — `additionalContext` vorhanden, NIE-Block, der getragene
    Inhalt ist ein wohlgeformter, sandwiched `<step-reminder>`-Block (system-reminder-
    tauglich: durchnummeriert, ACK-pflichtig, keine Prosa).
  - Stage 3 (Integration): die Injektions-Mechanik end-zu-end via echtem Hook-
    Subprozess (wie der Harness ihn aufruft) — PreToolUse:Skill-Event mit toggle=on +
    modus=M3 → `additionalContext` mit `<step-reminder>` kommt zurueck = der Traeger
    funktioniert.

INVARIANTE "Reminder != Enforcement" (AK-12): der Traeger darf NIE blocken
(continue != false, exit 0) — auch das ist Teil des korrekten system-reminder-
Format-Vertrags (ein Reminder, kein Gate).

Test-First: erst RED (Hook/Format existiert noch nicht in dieser Form), dann GREEN.

Befehl: py -3 -m pytest test_harness_role_system_t1.py -q
"""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.absolute()
HOOK = SCRIPT_DIR / "guard_step_adherence_reminder.py"


def _vault_root():
    """Kanonische Vault-Root via resolve_vault_root.py (BL-NEW-30/43, _TDD_red SCHRITT 0).

    Die frueher fragile `.parent.parent.parent.parent / "OmniCommand"`-Kette zeigte auf
    `Documents/Projekt/OmniCommand/Backlog` statt die KANONISCHE Vault-Root
    `Documents/OmniCommand` (siehe MEMORY: kanonische OmniCommand-Backlog-Pfade =
    `Documents\\OmniCommand\\`, NICHT `Projekt\\...\\OmniCommand`). Wir resolven daher
    deterministisch ueber das vorhandene Repo-Skript — Fail-Hard ohne stillen Fallback.
    """
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    out = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "resolve_vault_root.py")],
        capture_output=True, text=True, timeout=30,
    )
    root = out.stdout.strip()
    assert out.returncode == 0 and root, (
        f"resolve_vault_root.py lieferte keine Vault-Root (rc={out.returncode}): {out.stderr}"
    )
    return Path(root)


RESEARCH_DOC = (
    _vault_root()
    / "Backlog"
    / "BL-227-workflow-param-handschuhwechsel-reminder-berater"
    / "2_Model"
    / "adherence_research.md"
)

ON_M3 = {"OMNI_SAR_TEST_TOGGLE": "on", "OMNI_SAR_TEST_MODUS": "M3"}


def _run(event, env_extra=None):
    """Fuehre den Hook als echten Subprozess aus (wie der Harness es tut).

    Returns (returncode, parsed_stdout_or_None, raw_stdout).
    """
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
    try:
        parsed = json.loads(out) if out else None
    except json.JSONDecodeError:
        parsed = None
    return proc.returncode, parsed, out


def _skill_event(skill_name):
    return {"tool_name": "Skill", "tool_input": {"skill": skill_name}}


# ===========================================================================
# STAGE 1 (Unit) — Injektions-FORMAT/-SCHEMA fuer den system-reminder-Kanal.
# Der Hook-Output MUSS das Schema haben, das der Harness als mid-conv
# {role:system} <system-reminder> rendert: additionalContext-Feld, NIE-Block,
# system-reminder-tauglicher (sandwiched, getaggter, ACK-pflichtiger) Inhalt.
# ===========================================================================

@pytest.mark.testtyp_unit
def test_hook_exists():
    """Der Traeger (PreToolUse-Hook) existiert als Datei."""
    assert HOOK.exists(), f"Traeger-Hook fehlt: {HOOK}"


@pytest.mark.testtyp_unit
def test_output_carries_additionalcontext_field():
    """T1-Schreib-Pfad: der Hook gibt das `additionalContext`-Feld aus.

    `additionalContext` aus PreToolUse ist der EINZIGE Kanal, ueber den ein Hook
    einen mid-conv {role:system}-Block einschiessen kann (W-TRAEGER-1). Ohne dieses
    Feld kaeme der Reminder NICHT als system-reminder an → Traeger waere unwirksam.
    """
    rc, parsed, _ = _run(_skill_event("_IDF_orchestrate"), ON_M3)
    assert isinstance(parsed, dict), "Hook-Output ist kein JSON-Objekt"
    assert "additionalContext" in parsed, (
        "additionalContext fehlt — der system-reminder-Kanal wird nicht bedient"
    )
    assert isinstance(parsed["additionalContext"], str) and parsed["additionalContext"]


@pytest.mark.testtyp_unit
def test_output_schema_is_system_reminder_suitable():
    """Stage 1: der getragene Inhalt ist system-reminder-tauglich (AK-3-Schema).

    system-reminder-tauglich = strukturiert (XML-getaggt, kein Prosa-Freitext),
    durchnummeriert (step-id), ACK-pflichtig. Genau das, was Opus 4.8 als literale
    System-Instruktion prioritaer befolgt (W-REM-3).
    """
    rc, parsed, _ = _run(_skill_event("_IDF_orchestrate"), ON_M3)
    ac = parsed.get("additionalContext", "")
    assert "<step-reminder" in ac, "kein XML-getaggter step-reminder (Prosa statt Schema?)"
    assert "step-id=" in ac, "keine durchnummerierte Step-ID (AK-3)"
    assert 'required="true"' in ac, "kein ACK-Pflichtfeld (AK-3)"


@pytest.mark.testtyp_unit
def test_output_is_sandwiched_recency():
    """Stage 1: Sandwiching (AK-3) — der Step erscheint VOR und NACH dem Handoff-
    Block. Recency + Lost-in-the-Middle-Gegenmittel; im system-reminder-Kanal
    landet der Step damit am Kontext-Ende (prioritaer gelesen)."""
    rc, parsed, _ = _run(_skill_event("_IDF_orchestrate"), ON_M3)
    ac = parsed.get("additionalContext", "")
    assert ac.count("<step-reminder") >= 2, "Sandwiching fehlt (Step nur einmal)"


@pytest.mark.testtyp_unit
def test_traeger_never_blocks_format_invariant():
    """Stage 1 / AK-12: ein system-REMINDER-Format darf NIE ein Block-/Gate-Format
    sein. continue != false, exit 0 — auch im fire-Fall. (Reminder != Enforcement.)"""
    rc, parsed, _ = _run(_skill_event("_IDF_orchestrate"), ON_M3)
    assert rc == 0
    assert parsed.get("continue") is not False


@pytest.mark.testtyp_unit
def test_traeger_decision_is_hook_not_skill_berater():
    """Stage 1 / AK-14-Traeger-Begruendung: der Traeger ist statisch ein PreToolUse-
    Hook (gibt additionalContext via stdout-JSON aus), KEIN Skill-Berater.

    Beleg im Code selbst: der Hook liest ein PreToolUse-Event (stdin) und emittiert
    `additionalContext`. Ein Skill-Berater haette diesen Schreib-Pfad NICHT
    (er kann keine system-message einschiessen) — genau darum traegt nur der Hook."""
    src = HOOK.read_text(encoding="utf-8")
    tree = ast.parse(src)
    str_consts = {
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }
    joined = " ".join(str_consts)
    assert "additionalContext" in joined, "Hook emittiert keinen additionalContext-Kanal"


# ===========================================================================
# STAGE 3 (Integration) — Injektions-Mechanik end-zu-end durch den ECHTEN Hook.
# Simuliert ein PreToolUse:Skill-Event (toggle=on + M3) via Subprozess (wie der
# Harness) → der Traeger liefert additionalContext mit dem <step-reminder>-Block.
# ===========================================================================

@pytest.mark.testtyp_integration
@pytest.mark.parametrize("skill", [
    "_IDF_orchestrate",
    "_SDF_orchestrate",
    "_Post_orchestrate",
    "_SDF_orchestrate_post",
])
def test_e2e_injection_through_real_hook(skill):
    """Stage 3: end-zu-end via echtem Hook-Subprozess — der Traeger funktioniert
    fuer JEDEN nicht-motorisierten Ziel-Orchestrator. PreToolUse:Skill + on + M3
    → additionalContext mit sandwiched step-reminder (system-reminder-Inhalt)."""
    rc, parsed, raw = _run(_skill_event(skill), ON_M3)
    assert rc == 0, f"Hook-Subprozess exit != 0 fuer {skill}: {raw}"
    ac = parsed.get("additionalContext")
    assert ac, f"kein additionalContext (Traeger trug nicht) fuer {skill}"
    assert "<step-reminder" in ac and ac.count("<step-reminder") >= 2


@pytest.mark.testtyp_integration
def test_e2e_toggle_off_traeger_silent():
    """Stage 3: toggle=off → der Traeger schweigt (kein additionalContext).
    Belegt, dass der system-reminder NUR bei aktivem Param eingeschossen wird
    (Default off = kein Laerm; C-2-Gate trägt die Schreib-Entscheidung)."""
    rc, parsed, _ = _run(
        _skill_event("_IDF_orchestrate"),
        {"OMNI_SAR_TEST_TOGGLE": "off", "OMNI_SAR_TEST_MODUS": "M3"},
    )
    assert rc == 0
    assert "additionalContext" not in parsed


@pytest.mark.testtyp_integration
def test_e2e_non_orchestrator_no_injection():
    """Stage 3: ein Nicht-Ziel-Skill (Berater) loest KEINE Injektion aus —
    der Traeger feuert nur am nicht-motorisierten Handschuhwechsel (AK-11)."""
    rc, parsed, _ = _run(_skill_event("_SDF_berater_modusEntscheidung"), ON_M3)
    assert rc == 0
    assert "additionalContext" not in parsed


# ===========================================================================
# Doc-Review (AK-14): Adherence-Research + Degradations-Pfad dokumentiert.
# ===========================================================================

@pytest.mark.testtyp_integration
def test_adherence_research_doc_exists_and_grounded():
    """AK-14 Doc-Review: adherence_research.md existiert, belegt den Traeger-Mechanismus
    (system-reminder-Kanal), traegt den Degradations-Pfad (user-role) UND referenziert
    die Adherence-Belege (DCSRE-486 19->4 + externe Quellen). Backlinks zu OBSERVE/
    traeger-decision (evidenz-basiert, keine Behauptung ohne Beleg)."""
    assert RESEARCH_DOC.exists(), f"Research-Doc fehlt: {RESEARCH_DOC}"
    text = RESEARCH_DOC.read_text(encoding="utf-8")
    low = text.lower()
    assert "additionalcontext" in low, "Traeger-Mechanismus (additionalContext) nicht belegt"
    assert "system-reminder" in low, "system-reminder-Kanal nicht dokumentiert"
    assert "role" in low and "system" in low, "{role:system}-Traeger nicht benannt"
    # Degradations-Pfad (user-role) — Spec-Pflicht (AK-14b / W-TRAEGER-3).
    assert "user-role" in low or "degrad" in low, "Degradations-Pfad fehlt"
    # Adherence-Belege.
    assert "486" in text, "DCSRE-486-19->4-Beleg fehlt"
    # Backlinks (Evidenz-Verankerung).
    assert "OBSERVE" in text or "traeger-decision" in text, "Backlinks zur Evidenz fehlen"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
