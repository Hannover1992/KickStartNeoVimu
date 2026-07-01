#!/usr/bin/env python3
"""
Claude Code Hook — Post-GAP Sequence Enforcement (BL-037)

PreToolUse Hook auf Skill-Calls: Erzwingt die Post-GAP Checklist-Sequenz
in SDF Pipelines. Nach GAP-Analyse muessen 6 Schritte in Reihenfolge
abgearbeitet werden bevor SDF DONE wird.

Checklist-Felder (in _manifest.md unter sdf_post_gap_checklist):
  bl_done         — BL/PL-Item Status-Update
  checks5         — 5 prozessbegleitende Checks
  testSearch      — /_I_testSearch {NAME}
  stage           — /_stage_orchestrate {NAME}
  regressionGuard — Regressions-Guard
  final           — SDF PHASE FINAL (Protokoll-Rollover, DONE→IDLE)

Zustaende pro Feld: OPEN | REQUIRED | DONE | ABORTED

enforceProcess=true (Default): BLOCKIERT wenn REQUIRED-Felder nicht DONE
enforceProcess=false: Injiziert additionalContext mit naechstem Schritt (BL-038)

Hook-Config fuer settings.json:
  {
    "hooks": [{
      "type": "preToolUse",
      "tool_name": "Skill",
      "script": ".claude/scripts/guard_post_gap_sequence.py"
    }]
  }
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"


def _resolve_vault_path(key):
    """Resolve process state file path from vault-routing.json."""
    routing_path = Path(__file__).parent.parent / "config" / "vault-routing.json"
    if routing_path.exists():
        try:
            with open(routing_path, encoding='utf-8') as f:
                routing = json.load(f)
            for rule in routing.get("detection", {}).get("rules", []):
                psf = rule.get("process_state_files", {})
                if key in psf:
                    return Path(psf[key])
        except Exception:
            pass
    # Fallback: alte lokale Pfade
    fallbacks = {
        "manifest": ROOT_DIR / ".claude" / "analysis" / "_manifest.md",
        "manifest_protokoll": ROOT_DIR / ".claude" / "analysis" / "_manifest_protokoll.md",
        "backlog_index": ROOT_DIR / ".claude" / "analysis" / "_backlog_index.md",
        "session_params": ROOT_DIR / ".claude" / "analysis" / "_session_params.md",
        "task": ROOT_DIR / ".claude" / "Task.md",
        "parking_lot": ROOT_DIR / ".claude" / "analysis" / "_parking-lot.md",
    }
    return fallbacks.get(key)


SESSION_PARAMS_FILE = _resolve_vault_path("session_params")
MANIFEST_FILE = _resolve_vault_path("manifest")
AUDIT_DIR = ROOT_DIR / ".claude" / "audit"
AUDIT_FILE = AUDIT_DIR / "audit.jsonl"
LOG_FILE = ROOT_DIR / ".hook_debug.log"

# Die 6 Checklist-Felder in sequentieller Reihenfolge
CHECKLIST_FIELDS = [
    "bl_done",
    "checks5",
    "testSearch",
    "stage",
    "regressionGuard",
    "final",
]

# Feld → Aktions-Nachricht (RF-03, AK-03-02)
FIELD_TO_COMMAND = {
    "bl_done": "BL/PL-Item Status-Update ausfuehren",
    "checks5": "5 prozessbegleitende Checks durchfuehren",
    "testSearch": "/_I_testSearch {NAME} ausfuehren",
    "stage": "/_stage_orchestrate {NAME} ausfuehren",
    "regressionGuard": "Regressions-Guard ausfuehren",
    "final": "SDF PHASE FINAL (Protokoll-Rollover, DONE→IDLE) abschliessen",
}

# SDF df_status-Werte bei denen Enforcement aktiv ist (AK-01-02)
SDF_ACTIVE_STATES = {"ITEM_LOOP", "ITEM_DONE", "ITEM_STAGE"}


def read_enforce_process():
    """Liest enforceProcess aus _session_params.md. Default: true."""
    try:
        if not SESSION_PARAMS_FILE.exists():
            return True  # Default: enforce
        content = SESSION_PARAMS_FILE.read_text(encoding="utf-8")
        match = re.search(r'\*\*enforceProcess:\*\*\s*(true|false)', content)
        if match:
            return match.group(1) == "true"
    except Exception:
        pass
    return True  # Default: enforce


def read_manifest():
    """Liest _manifest.md frisch ein (AK-03-03: kein Caching)."""
    if not MANIFEST_FILE.exists():
        return None
    return MANIFEST_FILE.read_text(encoding="utf-8")


def detect_sdf_active(content):
    """Prueft ob SDF aktiv ist: df_status IN SDF_ACTIVE_STATES (AK-01-02).

    WICHTIG: Es gibt zwei DF_PIPELINE_STATE Bloecke im Manifest —
    der erste gehoert zu abgeschlossenen Items, der zweite zum aktuellen SDF-Lauf.
    Wir suchen den LETZTEN df_status, da dieser den aktuellen Zustand widerspiegelt.
    """
    # Finde alle df_status Eintraege
    matches = re.findall(r'df_status:\s*(\w+)', content)
    if not matches:
        return False
    # Der letzte df_status ist der aktuelle SDF-Lauf
    current_status = matches[-1]
    return current_status in SDF_ACTIVE_STATES


def parse_checklist(content):
    """Parst sdf_post_gap_checklist aus Manifest (AK-01-01).

    Extrahiert 6 Felder mit Zustaenden OPEN/REQUIRED/DONE/ABORTED.
    Gibt dict zurueck oder None wenn Checklist nicht gefunden.
    """
    # Finde den sdf_post_gap_checklist Block
    match = re.search(r'sdf_post_gap_checklist:\s*\n((?:\s+\w+:\s*\w+\n?)+)', content)
    if not match:
        return None

    block = match.group(1)
    checklist = {}
    for field in CHECKLIST_FIELDS:
        field_match = re.search(rf'{field}:\s*(\w+)', block)
        if field_match:
            checklist[field] = field_match.group(1)
        else:
            checklist[field] = "OPEN"  # Default wenn nicht vorhanden

    return checklist


def find_next_required(checklist):
    """Identifiziert den naechsten REQUIRED-Schritt (AK-01-03).

    Gibt (field_name, state) des ersten Feldes mit state=REQUIRED zurueck,
    oder None wenn kein Feld REQUIRED ist.
    """
    for field in CHECKLIST_FIELDS:
        state = checklist.get(field, "OPEN")
        if state == "REQUIRED":
            return field, state
    return None, None


def get_missing_required_fields(checklist):
    """Gibt alle REQUIRED-Felder zurueck die NICHT DONE sind (AK-02-02)."""
    missing = []
    for field in CHECKLIST_FIELDS:
        state = checklist.get(field, "OPEN")
        if state == "REQUIRED":
            missing.append(field)
    return missing


def build_additional_context(checklist):
    """Baut die additionalContext-Nachricht fuer Warn-Modus (AK-03-01, AK-03-02)."""
    next_field, _ = find_next_required(checklist)
    if not next_field:
        return None

    missing = get_missing_required_fields(checklist)
    action = FIELD_TO_COMMAND.get(next_field, next_field)

    lines = [
        f"[Post-GAP Guard] Naechster Schritt: {action}",
        f"  Offene REQUIRED-Felder: {', '.join(missing)}",
    ]
    # Checklist-Snapshot fuer Transparenz
    snapshot_parts = []
    for field in CHECKLIST_FIELDS:
        state = checklist.get(field, "OPEN")
        marker = "x" if state == "DONE" else ("!" if state == "REQUIRED" else " ")
        snapshot_parts.append(f"[{marker}] {field}={state}")
    lines.append(f"  Checklist: {' | '.join(snapshot_parts)}")

    return "\n".join(lines)


def append_guard_log(violation_type, details, blocked):
    """Appende Violation an GUARD_LOG Datei (AK-02-03)."""
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = f"- [{timestamp}] **{violation_type}** [{action}]: {details}\n"
        with open(GUARD_LOG_FILE, "a", encoding='utf-8') as f:
            f.write(entry)
    except Exception:
        pass


def write_audit_entry(entry):
    """Schreibt 1 JSONL-Zeile in audit.jsonl (AK-04-01)."""
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def log_error(error):
    """Loggt Fehler in .hook_debug.log (AK-04-03)."""
    try:
        with open(LOG_FILE, "a", encoding='utf-8') as log:
            log.write(f"[{datetime.now()}] guard_post_gap_sequence Error: {error}\n")
    except Exception:
        pass


def main():
    # === Globaler Owner-Kill-Switch (BL-223): enforceProcess=false -> Guard aus ===
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
        hook_data = json.loads(sys.stdin.read())
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        # AK-05-02: Nur auf Skill-Aufrufe triggern
        if tool_name != "Skill":
            print(json.dumps({"continue": True}))
            return

        # Manifest frisch lesen (AK-03-03)
        content = read_manifest()
        if not content:
            print(json.dumps({"continue": True}))
            return

        # AK-01-02: Nur enforced wenn SDF aktiv
        if not detect_sdf_active(content):
            print(json.dumps({"continue": True}))
            return

        # AK-01-01: Checklist parsen
        checklist = parse_checklist(content)
        if not checklist:
            # Keine Checklist gefunden — kein Enforcement
            print(json.dumps({"continue": True}))
            return

        # Pruefe ob es REQUIRED-Felder gibt die nicht DONE sind
        missing = get_missing_required_fields(checklist)
        if not missing:
            # Alle REQUIRED sind DONE (oder nichts ist REQUIRED) — kein Enforcement
            # Audit-Event trotzdem loggen
            write_audit_entry({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "event": "SEQUENCE_CHECK",
                "step": "ALL_CLEAR",
                "state": "PASS",
                "checklist_snapshot": checklist,
            })
            print(json.dumps({"continue": True}))
            return

        # Es gibt offene REQUIRED-Felder
        next_field, _ = find_next_required(checklist)
        enforce = read_enforce_process()

        # AK-04-01: Audit-Event
        write_audit_entry({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "event": "SEQUENCE_CHECK",
            "step": next_field,
            "state": "REQUIRED",
            "checklist_snapshot": checklist,
            "enforce": enforce,
            "missing_fields": missing,
        })

        if enforce:
            # AK-02-02: Block-Modus
            field_actions = [f"{f} ({FIELD_TO_COMMAND.get(f, f)})" for f in missing]
            message = (
                f"Post-GAP-Sequenz nicht eingehalten. "
                f"Fehlende Schritte: {', '.join(field_actions)}"
            )
            print(json.dumps({
                "continue": False,
                "message": message,
            }))
            # AK-02-03: Guard-Log
            append_guard_log(
                "POST_GAP_SEQUENCE",
                f"Fehlende REQUIRED-Felder: {missing}",
                blocked=True,
            )
        else:
            # AK-03-01: Warn-Modus mit additionalContext
            additional = build_additional_context(checklist)
            result = {"continue": True}
            if additional:
                result["additionalContext"] = additional
            print(json.dumps(result))
            # Guard-Log (WARNED)
            append_guard_log(
                "POST_GAP_SEQUENCE",
                f"REQUIRED-Felder nicht DONE: {missing} (additionalContext injiziert)",
                blocked=False,
            )

    except Exception as e:
        # AK-04-02: Fail-safe — NIEMALS false-block bei Fehlern
        log_error(e)
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
