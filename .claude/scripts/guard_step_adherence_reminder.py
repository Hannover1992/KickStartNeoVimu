#!/usr/bin/env python3
"""guard_step_adherence_reminder.py — BL-227 C-4 Step-Adherence-Reminder-Hook.

PreToolUse:Skill-Hook (L3-Praeventions-Schicht). Feuert, wenn der Team Lead an
einem NICHT-motorisierten Handschuhwechsel den Ziel-Orchestrator laedt
(A->IDF / IDF->SDF / SC->Post / I->SDF_post). Erinnert via Progressive-Disclosure
an den naechsten Pflicht-Schritt (k+1) + dessen Delegations-Vertrag.

Verdrahtet die fertigen Bausteine:
  C-1  handover_reminder_core.build_reminder(target, next_step, handoff_block)
  C-2  session_params_resolver.resolve_param("step_adherence_reminder")  (Toggle)
  C-3  handover_reminder_gate.modus_gate(modus, toggle)                    (Gate)

================ INVARIANTE "Reminder != Enforcement" (AK-12, FAIL-OPEN PFLICHT) =====
Dieser Hook hat KEINEN Block-, Abort- oder Veto-Pfad. Er gibt NIE {"continue": false}
aus, NIE exit!=0. Jede Exception / fehlender State / nicht ableitbarer Modus ->
still nichts (kein additionalContext), exit 0. Ein kaputter Reminder darf die Session
NICHT stoeren. Enforcement bleibt AUSSCHLIESSLICH bei geist9/geist9b (Default-BLOCK).
Zuverlaessigkeits-Ranking (einstimmig): Motor (BL-222) > Hook (geist9) > Reminder.

AK-13: dispatch_implement.js + guard_geist9* werden NICHT angefasst (rein additiv).
Dieser Hook importiert nur die read-only C-1/C-2/C-3-Bausteine.

AK-11 Scope: NUR die 4 nicht-motorisierten Ziel-Orchestratoren triggern. Motor-Pfade
(dispatch_implement-intern, 1-Step=1-agent) sind ausgeschlossen — sie laden keinen
dieser Ziel-Orchestrator-Skills, also feuert hier nichts.
"""
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent


# ---------------------------------------------------------------------------
# AK-4 / AK-11: Trigger-Liste = die nicht-motorisierten Ziel-Orchestratoren.
# Jeder Eintrag traegt den next_step (k+1 = der ERSTE Pflicht-Schritt des Ziels
# nach dem Handoff) als Delegations-Vertrag (AK-2 Progressive Disclosure: GENAU 1).
# Die Mappings spiegeln den jeweiligen Orchestrator-Vertrag (Phase 1 / Pre-Phase).
# ---------------------------------------------------------------------------
_TARGET_CONTRACT = {
    "_IDF_orchestrate": {
        "id": "IDF.1",
        "name": "Phase 1 — resumeGuard + init",
        "objective": "IDF-Resume-State pruefen + Pipeline initialisieren BEVOR "
                     "irgendein fachlicher Schritt; KEINE Phase ueberspringen.",
        "output_format": "_manifest.md (IDF_PIPELINE_STATE init/resume) via _IDF_berater_resumeGuard",
        "boundaries": "Kein Batch-Plan, kein SDF-Start — erst der vollstaendige "
                      "IDF-Phasenlauf (3.5 validator ... 8.0 finalSummary).",
    },
    "_SDF_orchestrate": {
        "id": "SDF.1.1",
        "name": "Phase 1.1 — modusEntscheidung (INV-MODUS-1/2)",
        "objective": "PRO Sub-Batch den Modus via _SDF_berater_modusEntscheidung "
                     "entscheiden (NICHT skippbar, auch nicht bei klarem Upstream).",
        "output_format": "DF_BATCH_STATE.batch_modes + modus_begruendung (set_by=_SDF_berater_modusEntscheidung)",
        "boundaries": "Nur SDF Phase 1.1 setzt modus (INV-MODUS-1). Kein Implement "
                      "vor modusEntscheidung; Dispatch laeuft via Workflow-Motor.",
    },
    "_Post_orchestrate": {
        "id": "POST.1",
        "name": "Post-Implementation Phase 1",
        "objective": "Post-Phasen-Kette nach SC/Implement vollstaendig durchziehen — "
                     "kein Schritt inline-improvisiert, keine Auslassung.",
        "output_format": "Post-Phase-Outputs gemaess _Post_orchestrate-Vertrag",
        "boundaries": "Kein direkter Commit / kein [ ]->[x] vor Abschluss der Post-Kette.",
    },
    "_SDF_orchestrate_post": {
        "id": "SDFPOST.3",
        "name": "Phase 3 — recalibrate/postItem/statusTransition/modelSync (INV-MODUS-7)",
        "objective": "Erzwungener Rueck-Handschuh nach I/SC: Phase 3 + Phase 4 "
                     "(loopDecision) nach JEDEM Batch-Implement — NIE uebersprungen, "
                     "NIE inline (INV-HANDOVER-1).",
        "output_format": "Phase-3.x-Berater-Outputs + loop_decision (persistiert vor naechster Round)",
        "boundaries": "Kein [ ]->[x] / completed_batches vor _SDF_orchestrate_post "
                      "(geist9b blockt das hart).",
    },
}


def _read_event():
    """Lies das PreToolUse-Event von stdin. Fail-open bei jedem Fehler -> None."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return None
        return json.loads(raw)
    except Exception:
        return None


def _resolve_toggle():
    """C-2: step_adherence_reminder via 3-Stufen-Inheritance.

    Test-Override OMNI_SAR_TEST_TOGGLE hat Vorrang (Unit-Test ohne Vault).
    Fail-open: jeder Fehler -> "off" (still, kein Reminder).
    """
    test_toggle = os.environ.get("OMNI_SAR_TEST_TOGGLE")
    if test_toggle is not None:
        return test_toggle
    try:
        if str(SCRIPT_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPT_DIR))
        from session_params_resolver import resolve_param

        bl_id = _detect_bl_id()
        val = resolve_param("step_adherence_reminder", bl_id=bl_id)
        return val if isinstance(val, str) else "off"
    except Exception:
        return "off"


def _detect_bl_id():
    """Best-effort BL-Id-Ableitung (fail-open -> None)."""
    try:
        if str(SCRIPT_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPT_DIR))
        from current_context import detect_bl_id, _git_branch

        return detect_bl_id(_git_branch())
    except Exception:
        return None


def _resolve_modus():
    """Lies den aktuellen DF_BATCH_STATE.modus (M1/M2/M3...) aus dem Manifest.

    Test-Override OMNI_SAR_TEST_MODUS hat Vorrang. Fail-open: nicht ableitbar -> "".
    AK-11/AK-12: ist der Modus nicht ableitbar, feuert nichts (modus_gate liefert
    "no-fire" fuer "" / unbekannt).
    """
    test_modus = os.environ.get("OMNI_SAR_TEST_MODUS")
    if test_modus is not None:
        return test_modus
    try:
        content = _read_manifest()
        if not content:
            return ""
        return _extract_current_modus(content)
    except Exception:
        return ""


def _read_manifest():
    """Read-only Manifest-Inhalt (per-BL-folder-aware). Fail-open -> ""."""
    try:
        if str(SCRIPT_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPT_DIR))
        from _manifest_resolver import read_active_manifest

        content, _ = read_active_manifest(SCRIPT_DIR, ROOT_DIR)
        return content or ""
    except Exception:
        return ""


def _extract_current_modus(content):
    """Extrahiere den Modus des AKTUELLEN (= letzten) DF_BATCH_STATE-Blocks.

    Sucht im letzten DF_BATCH_STATE-Scope nach `modus`/`mode`/`batch_modes`-Werten
    der Form M\\d. Fail-open: kein Match -> "".
    """
    headers = list(re.finditer(r"(?:^|\n)#{1,4}\s+DF_BATCH_STATE", content))
    scope = content[headers[-1].start():] if headers else content
    # Bevorzugt explizite modus/mode-Felder, sonst batch_modes-Werte (M1/M2/M3).
    m = re.search(r"(?:^|\n)\s*(?:modus|mode)\s*[:=]\s*[\"']?(M[0-9])[\"']?",
                  scope, re.MULTILINE)
    if m:
        return m.group(1)
    m = re.search(r"[\"']?(M[0-9])[\"']?", scope)
    return m.group(1) if m else ""


def _emit(result):
    """Gib genau ein JSON-Objekt aus. NIE continue=false (AK-12)."""
    if result.get("continue") is False:
        result["continue"] = True
    print(json.dumps(result))


def main():
    # --- FAIL-OPEN-Huelle: jeder Fehler -> {"continue": true}, exit 0 (AK-12) ---
    try:
        event = _read_event()
        if not isinstance(event, dict):
            _emit({"continue": True})
            return

        if event.get("tool_name") != "Skill":
            _emit({"continue": True})
            return

        tool_input = event.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            _emit({"continue": True})
            return

        skill = tool_input.get("skill", "")
        contract = _TARGET_CONTRACT.get(skill)
        if contract is None:
            # AK-11: non-orchestrator / motorisierter / nicht-getriggerter Skill.
            _emit({"continue": True})
            return

        # Toggle-Gate (C-2) + Modus-Gate (C-3).
        toggle = _resolve_toggle()
        modus = _resolve_modus()

        if str(SCRIPT_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPT_DIR))
        from handover_reminder_gate import modus_gate

        action = modus_gate(modus, toggle)  # "fire" / "optional" / "no-fire"
        if action == "no-fire":
            _emit({"continue": True})
            return
        # "optional" (M2): konservativ feuern (AK-9 "gemaess konfiguriertem
        # M2-Verhalten"); Reminder != Enforcement, also unschaedlich.

        # Reminder bauen (C-1). next_step = k+1 = ERSTER Pflicht-Schritt des Ziels.
        from handover_reminder_core import build_reminder

        handoff_block = (
            f"<handoff target=\"{skill}\" modus=\"{modus}\" "
            f"reminder-action=\"{action}\">Handschuhwechsel nach nicht-motorisiertem "
            f"Handoff. Reminder != Enforcement (kein Block).</handoff>"
        )
        injection = build_reminder(skill, contract, handoff_block)

        _emit({"continue": True, "additionalContext": injection})
    except Exception:
        # AK-12: nichts darf die Session stoeren.
        try:
            print(json.dumps({"continue": True}))
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            print(json.dumps({"continue": True}))
        except Exception:
            pass
    sys.exit(0)
