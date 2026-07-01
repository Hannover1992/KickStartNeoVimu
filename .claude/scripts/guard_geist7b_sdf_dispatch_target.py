#!/usr/bin/env python3
"""
guard_geist7b_sdf_dispatch_target.py — SDF Dispatch-Target-Bypass-Block (CRITICAL).

Schliesst die Luecke aus DCSRE-486 Round 16 (CaseStudy_DCSRE-486_Round16_DispatchBypass).

Problem:
  SDF Phase 2.1 EXECUTION DISPATCH soll pro Batch Skill(_I_orchestrate) (M2/M3) ODER
  Skill(_SC_orchestrate) (M4-M7) laden. In Round 16 spawnte SDF stattdessen direkt
  general-sonnet-Worker (b1-build-green, b2-multiselect, ...) = Mega-Worker pro Batch.

  guard_geist7 (Step-Count) konnte das NICHT fangen: es zaehlt _I_*-Steps NACH einem
  Skill(_I_orchestrate)-Load. Wenn _I_orchestrate NIE geladen wird, gibt es keinen
  Anker → kein Counting → kein Block. Drift verschob sich von "zu wenige Steps" auf
  "Skill gar nicht geladen".

Loesung — bewache den UEBERGANG, nicht nur das Ziel:
  PreToolUse auf Agent/Task-Spawn. WENN:
    - SDF-Execution-Kontext aktiv (df_status execution-ish ODER aktiver Skill _SDF_*)
    - UND seit letztem modusEntscheidung KEIN Skill(_I_orchestrate/_SC_orchestrate) geladen
    - UND der gespawnte Agent ist ein general-* Implementation-Worker
  → BLOCK: SDF muss erst Skill(_I_orchestrate) laden.

Detektion via audit.jsonl: scanne rueckwaerts. Finde letztes von:
  - SKILL_LOAD _I_orchestrate / _SC_orchestrate  → LEGIT (I-Pipeline-Worker folgen)
  - BERATER_OUTPUTS.modusEntscheidung / SKILL_LOAD _SDF_orchestrate → SDF-Execution-Kontext
  Wenn SDF-Kontext NACH letztem _I/_SC-Load → Dispatch-Bypass.

enforceProcess-Toggle. Override: OMNI_GEIST7B_OFF=1.
Test-Override: OMNI_GEIST7B_AUDIT (audit-path), OMNI_GEIST7B_ENFORCE=1.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
AUDIT_FILE = ROOT_DIR / ".claude" / "audit" / "audit.jsonl"
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# I-Pipeline / SC-Pipeline Entry-Skills (legitime Dispatch-Targets)
PIPELINE_ENTRY_SKILLS = {"_I_orchestrate", "_SC_orchestrate"}
# BL-440: ein frischer A/IDF-Pipeline-Start beendet den SDF-Dispatch-Kontext des VORIGEN BLs.
# Ohne diesen Reset blockt der Backward-Scan in Multi-BL-Sessions die A-Berater-Spawns des
# naechsten BLs (alte SDF-Marker im Audit). KEIN Weakening: die echte SDF->non-I-Violation
# (SDF-Marker juenger als JEDER A/IDF/I/SC-Load) wird weiter gefangen.
NEW_PIPELINE_RESET_SKILLS = {"_A_orchestrate", "_IDF_orchestrate"}

# Generische Implementation-Worker (verdaechtig wenn ohne Pipeline-Entry)
GENERIC_WORKER_TYPES = {"general-purpose", "general-sonnet", "general-opus", "general-haiku"}

# Marker fuer SDF-Execution-Kontext in audit
SDF_EXECUTION_MARKERS = ("_SDF_orchestrate", "modusEntscheidung", "_SDF_berater_executionDispatch")

# ── Mega-Worker-Diskriminator (BL-210, 2026-05-28) — model-agnostisch, prompt-intent ──
# Duplikat von guard_agent_prompt_validator (standalone Hook-Skripte). STRUKTURELL.
SINGLE_PHASE_COMMANDS = [
    "_I_cleanCodeSlice", "_I_cleanCodeArchitect", "_I_codeAtomic", "_I_codeSystem",
    "_I_blueprintArchitect", "_I_blueprintQG", "_I_goldDefine", "_I_diffAudit",
    "_I_verify", "_I_testSearch", "_TDD_red", "_TDD_green", "_TDD_refactor",
    "_TDD_execute", "_TDD_check", "_berater_",
]
_EXEC_GOVERNS_ORCH_RE = re.compile(
    r'\b(run|execute|fuehre|führe|ausfuehren|ausführen|starte|laufe|spawne)\s+'
    r'(?:den\s+|the\s+|das\s+|skill\(|/|_)*'
    r'(I_orchestrate|SC_orchestrate|SDF_orchestrate_post|SDF_orchestrate|A_orchestrate|'
    r'IDF_orchestrate|TDD_orchestrate|BDF_orchestrate|PostBatch_orchestrate)\b',
    re.IGNORECASE,
)
_DISPATCH_ROLE_MARKERS = [
    "dispatch-worker", "dispatch worker", "dispatch-agent", "dispatch agent",
    "dispatch-step", "phase-2-dispatch", "phase 2 dispatch", "phase-2 dispatch",
    "puppet-master", "puppet master",
]


def _coerce_text(val):
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        for k in ("text", "content", "prompt", "value", "message", "description"):
            if k in val:
                return _coerce_text(val[k])
        try:
            return json.dumps(val, ensure_ascii=False)[:20000]
        except Exception:
            return str(val)[:20000]
    if isinstance(val, (list, tuple)):
        return "\n".join(_coerce_text(v) for v in val)[:20000]
    return str(val)[:20000]


def _names_single_phase(prompt_text):
    low = (prompt_text or "").lower()
    return any(c.lower() in low for c in SINGLE_PHASE_COMMANDS)


def is_orchestrator_exec_contract(prompt_text):
    """True wenn der Spawn-Prompt einen Agent anweist einen ORCHESTRATOR
    auszufuehren (Mega-/Dispatch-Worker). Single-Phase-Command -> immer legit."""
    txt = prompt_text if isinstance(prompt_text, str) else _coerce_text(prompt_text)
    low = txt.lower()
    if any(c.lower() in low for c in SINGLE_PHASE_COMMANDS):
        return False
    if any(m in low for m in _DISPATCH_ROLE_MARKERS):
        return True
    if _EXEC_GOVERNS_ORCH_RE.search(txt):
        return True
    return False


def get_audit_path():
    return Path(os.environ.get("OMNI_GEIST7B_AUDIT", str(AUDIT_FILE)))


def read_enforce():
    if os.environ.get("OMNI_GEIST7B_ENFORCE") == "1":
        return True
    if os.environ.get("OMNI_GEIST7B_ENFORCE") == "0":
        return False
    # session_params lesen (vault-aware vereinfacht: default true)
    return True


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **GEIST7B_DISPATCH_TARGET** [{action}]: {msg}\n")
    except Exception:
        pass


def analyze_dispatch_context():
    """Scanne audit.jsonl rueckwaerts.

    Returns: (sdf_execution_active, pipeline_entry_since_modus)
      sdf_execution_active: bool — SDF-Execution-Kontext aktiv?
      pipeline_entry_since_modus: bool — _I/_SC_orchestrate seit letztem SDF-Marker geladen?
    """
    audit = get_audit_path()
    if not audit.exists():
        return False, True  # kein Trail → konservativ durchlassen
    try:
        lines = audit.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False, True

    # Scanne rueckwaerts. Finde:
    #   - letztes Pipeline-Entry (_I/_SC_orchestrate)  → pos_entry
    #   - letztes SDF-Execution-Marker               → pos_sdf
    pos_entry = -1
    pos_sdf = -1
    pos_reset = -1   # BL-440: letztes _A_/_IDF_orchestrate (neuer BL-Pipeline-Start)
    for i in range(len(lines) - 1, -1, -1):
        try:
            ev = json.loads(lines[i])
        except Exception:
            continue
        blob = json.dumps(ev)
        skill = ev.get("skill_name") or ev.get("skill") or ""

        if pos_entry == -1 and ev.get("event") == "SKILL_LOAD" and skill in PIPELINE_ENTRY_SKILLS:
            pos_entry = i
        if pos_reset == -1 and ev.get("event") == "SKILL_LOAD" and skill in NEW_PIPELINE_RESET_SKILLS:
            pos_reset = i
        if pos_sdf == -1 and any(m in blob for m in SDF_EXECUTION_MARKERS):
            pos_sdf = i
        if pos_entry != -1 and pos_sdf != -1 and pos_reset != -1:
            break

    sdf_execution_active = pos_sdf != -1
    # BL-440: frischer A/IDF-Pipeline-Start JUENGER als der letzte SDF-Marker -> der SDF-Dispatch-
    # Kontext des vorigen BLs ist abgeloest (neue Story-Analyse/Dekomposition, KEIN SDF->I-Dispatch).
    if pos_reset != -1 and pos_reset >= pos_sdf:
        sdf_execution_active = False
    # Pipeline-Entry seit SDF-Marker? entry muss SPAETER (groesserer Index) als sdf sein
    pipeline_entry_since_modus = pos_entry != -1 and pos_entry >= pos_sdf
    return sdf_execution_active, pipeline_entry_since_modus


def main():
    # === Globaler Owner-Kill-Switch (BL-210): enforceProcess=false -> Guard aus ===
    import os as _os, json as _json
    if _os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(_json.dumps({"continue": True}))
        return
    try:
        import sys as _sys
        from pathlib import Path as _P
        _sd = str(_P(__file__).parent.absolute())
        if _sd not in _sys.path:
            _sys.path.insert(0, _sd)
        from _enforce_gate import enforce_active
        if not enforce_active():
            print(_json.dumps({"continue": True}))
            return
    except Exception:
        pass
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    if os.environ.get("OMNI_GEIST7B_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    tool_name = event.get("tool_name", "")
    if tool_name not in ("Agent", "Task"):
        print(json.dumps({"continue": True}))
        return

    ti = event.get("tool_input", {}) or {}
    subagent_type = ti.get("subagent_type", "") or ti.get("subagent", "")
    prompt_text = (_coerce_text(ti.get("prompt"))
                   or _coerce_text(ti.get("description"))
                   or _coerce_text(ti.get("message")))

    # NEU (BL-210): model-agnostisch + prompt-intent. subagent_type ist KEIN
    # Freibrief mehr — ein "Opus Dispatch-Worker" / Custom-Type wird ueber den
    # PROMPT-INTENT geprueft, nicht ueber das Modell.
    if is_orchestrator_exec_contract(prompt_text):
        enforce = read_enforce()
        msg = (
            "[GUARD-VIOLATION] GEIST7B_DISPATCH_TARGET: Spawn-Prompt fuehrt einen "
            "ORCHESTRATOR aus (Mega-/Dispatch-Worker) — model-agnostisch erkannt.\n"
            "  -> STATTDESSEN Handschuh-Wechsel: der Team Lead laedt SELBST "
            "Skill(_I_orchestrate --stage=<X> --batch=<id>) (bzw. _SC_/_TDD_). "
            "SDF spawnt KEINEN Dispatch-Worker; I_orchestrate spawnt seine eigenen "
            "Single-Phase-Worker selbst. (INV-AO-CALLER / INV-PM-2 / INV-HW-1)\n"
            + ("BLOCKIERT." if enforce else "WARNED (enforceProcess=false).")
        )
        append_guard_log(f"orchestrator_runner spawn ('{prompt_text[:60]}')", enforce)
        print(json.dumps({"continue": not enforce, "message": msg}))
        return

    if _names_single_phase(prompt_text):
        # Legit: I_orchestrate/TDD spawnt seinen eigenen Single-Phase-Worker.
        print(json.dumps({"continue": True}))
        return

    # Residual (unknown prompt-intent): alte Heuristik — nur generische Worker verdaechtig
    if subagent_type not in GENERIC_WORKER_TYPES:
        print(json.dumps({"continue": True}))
        return

    sdf_active, pipeline_entry = analyze_dispatch_context()

    if not sdf_active:
        # Kein SDF-Execution-Kontext → general-sonnet-Spawn ist legit (andere Pipeline)
        print(json.dumps({"continue": True}))
        return

    if pipeline_entry:
        # _I/_SC_orchestrate wurde geladen → dieser Worker ist legit I-Pipeline-Step
        print(json.dumps({"continue": True}))
        return

    # SDF-Execution aktiv, ABER kein Skill(_I/_SC_orchestrate) seit modusEntscheidung
    # → Dispatch-Bypass (general-sonnet Mega-Worker statt I-Pipeline)
    enforce = read_enforce()
    desc = ti.get("description", "")[:50]
    msg = (
        f"[GUARD-VIOLATION] GEIST7B_DISPATCH_TARGET: SDF-Execution-Kontext aktiv, aber "
        f"KEIN Skill(_I_orchestrate/_SC_orchestrate) seit modusEntscheidung geladen. "
        f"Stattdessen direkter {subagent_type}-Spawn ('{desc}'). "
        f"SDF Phase 2.1 MUSS via Skill(_I_orchestrate) dispatchen (Mega-Worker-Bypass, "
        f"DCSRE-486 Round 16). "
        + ("BLOCKIERT." if enforce else "WARNED.")
    )
    append_guard_log(f"SDF→{subagent_type} ohne _I_orchestrate ('{desc}')", enforce)
    print(json.dumps({"continue": not enforce, "message": msg}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_geist7b ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
