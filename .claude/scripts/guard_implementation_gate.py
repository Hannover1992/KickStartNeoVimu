#!/usr/bin/env python3
"""
Claude Code Hook — Implementation-Gate (CS8 Fix)

Pre-Hook auf Edit/Write Tool-Calls: BLOCKIERT Edits an .claude/commands/
WENN keine aktive I_PIPELINE_STATE oder SC_PIPELINE_STATE im Manifest.

CS8 (2026-04-07): SDF hat Agent() direkt gespawnt statt Skill(_I_orchestrate).
BL-041 (K=59) und BL-043 (K=41) wurden ohne I/SC-Pipeline implementiert.
Text-Invarianten (VERTRAG) werden unter Context-Druck ignoriert.
Nur technische Hooks verhindern Shortcuts.

Schuetzt gegen:
  CS3: BDF spawnt Agent() direkt (ohne SDF)
  CS8: SDF spawnt Agent() direkt (ohne I/SC)

enforceProcess=true: BLOCKIERT Violations (continue=false)
enforceProcess=false: NUR Warning mit additionalContext (continue=true)
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


MANIFEST_FILE = _resolve_vault_path("manifest")
SESSION_PARAMS_FILE = _resolve_vault_path("session_params")
AUDIT_LOG_FILE = ROOT_DIR / ".claude" / "audit" / "audit.jsonl"
LOG_FILE = ROOT_DIR / ".hook_debug.log"

# Geschuetzte Pfade: Edits hier brauchen aktive Pipeline
PROTECTED_PATHS = [
    ".claude/commands/",
    ".claude/meta/implementation/",
    ".claude/meta/codeKonvention/",
]

# AUSNAHMEN: Dateien die IMMER editiert werden duerfen (State-Management)
EXEMPT_FILES = [
    "_session_params.md",
    "_manifest.md",
    "_manifest_protokoll.md",
    "_guard_log.md",
    "_backlog_index.md",
    "_parking-lot.md",
    "audit.jsonl",
]

# BL-064 T1: Orchestrator-MD-Dateien sind Pre-Phase Team-Lead-Arbeit (RF-01, AK-02)
ORCHESTRATE_EXEMPT_PATTERN = re.compile(r'/_[A-Za-z_]+_orchestrate\.md$')


def read_enforce_process():
    """Liest enforceProcess aus _session_params.md. Default: true."""
    try:
        if not SESSION_PARAMS_FILE.exists():
            return True
        content = SESSION_PARAMS_FILE.read_text(encoding="utf-8")
        match = re.search(r'\*\*enforceProcess:\*\*\s*(true|false)', content)
        if match:
            return match.group(1) == "true"
    except Exception:
        pass
    return True


def is_pipeline_active():
    """Prueft ob I_PIPELINE_STATE oder SC_PIPELINE_STATE aktiv ist.
    Aktiv = i_status/sc_status IN [RUNNING, BLUEPRINT, CODE, VERIFY, ...]
    NICHT aktiv = DONE, IDLE, null, nicht vorhanden"""
    try:
        if not MANIFEST_FILE.exists():
            return False, "Manifest nicht gefunden"
        content = MANIFEST_FILE.read_text(encoding="utf-8")

        # I_PIPELINE_STATE pruefen
        # Terminal = DONE, IDLE, null, ABORTED* (inkl. ABORTED_HOOK_BLOCKING etc.)
        i_match = re.search(r'i_status:\s*(\S+)', content)
        if i_match:
            i_status = i_match.group(1)
            i_terminal = (i_status in ["DONE", "IDLE", "null"]
                         or i_status.startswith("ABORTED"))
            if not i_terminal:
                return True, f"I_PIPELINE aktiv (i_status={i_status})"

        # SC_PIPELINE_STATE pruefen
        sc_match = re.search(r'sc_status:\s*(\S+)', content)
        if sc_match:
            sc_status = sc_match.group(1)
            sc_terminal = (sc_status in ["DONE", "IDLE", "null",
                                         "DONE_DISCOVERY_ONLY"]
                          or sc_status.startswith("ABORTED"))
            if not sc_terminal:
                return True, f"SC_PIPELINE aktiv (sc_status={sc_status})"

        return False, "Keine aktive I/SC Pipeline"
    except Exception as e:
        return False, f"Manifest-Lese-Fehler: {e}"


def is_file_protected(file_path):
    """Prueft ob die Datei in einem geschuetzten Pfad liegt."""
    for exempt in EXEMPT_FILES:
        if exempt in file_path:
            return False

    # BL-064 T1: Orchestrator-MD-Whitelist (RF-01)
    if ORCHESTRATE_EXEMPT_PATTERN.search(file_path):
        return False

    for protected in PROTECTED_PATHS:
        if protected in file_path:
            return True

    return False


def append_guard_log(details, blocked):
    """Appende Violation an GUARD_LOG."""
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = f"- [{timestamp}] **CS8-IMPL-GATE** [{action}]: {details}\n"
        with open(GUARD_LOG_FILE, "a", encoding='utf-8') as f:
            f.write(entry)
    except Exception:
        pass


def append_audit_log(file_path, blocked):
    """Appende Unified GUARD_BLOCK/GUARD_WARN Event in audit.jsonl (BL-064 T5/RF-05)."""
    try:
        AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "event": "GUARD_BLOCK" if blocked else "GUARD_WARN",
            "level": "BLOCK" if blocked else "WARN",
            "violation": "CS8",
            "details": f"Edit an {file_path} ohne aktive I/SC Pipeline",
            "ctx": {"guard": "implementation_gate"}
        }
        with open(AUDIT_LOG_FILE, "a", encoding='utf-8') as f:
            f.write(json.dumps(event) + "\n")
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

        if tool_name not in ["Edit", "Write"]:
            print(json.dumps({"continue": True}))
            return

        file_path = ""
        if isinstance(tool_input, dict):
            file_path = tool_input.get("file_path", "")

        if not file_path:
            print(json.dumps({"continue": True}))
            return

        # Pruefe ob Datei geschuetzt ist
        if not is_file_protected(file_path):
            print(json.dumps({"continue": True}))
            return

        # Datei ist geschuetzt → Pipeline-Check
        pipeline_active, reason = is_pipeline_active()

        if pipeline_active:
            # Pipeline aktiv → Edit erlaubt
            print(json.dumps({"continue": True}))
            return

        # VIOLATION: Edit an geschuetzter Datei ohne aktive Pipeline
        enforce = read_enforce_process()

        short_path = file_path.split(".claude/")[-1] if ".claude/" in file_path else file_path

        # ═══ POSITIVE ENFORCEMENT (WP-Insight: nicht nur blockieren, sondern anleiten) ═══
        # Der Hook sagt: WAS ist falsch + WAS sollst du stattdessen tun + WIE genau
        guidance = (
            f"\n\n"
            f"=== CS8 IMPLEMENTATION-GATE ===\n"
            f"BLOCKIERT: Edit an '{short_path}' ohne aktive I/SC Pipeline.\n"
            f"GRUND: {reason}\n"
            f"\n"
            f"WAS DU TUN SOLLST (Positive Enforcement):\n"
            f"  1. STOPPE alle direkten Agent()-Edits an Command-Dateien\n"
            f"  2. Lade die I-Pipeline: Skill(skill=\"_I_orchestrate\", args=\"{{NAME}}\")\n"
            f"     ODER die SC-Pipeline: Skill(skill=\"_SC_orchestrate\", args=\"{{NAME}} ...\")\n"
            f"  3. I/SC setzt i_status=RUNNING im Manifest → dann sind Edits erlaubt\n"
            f"  4. I/SC spawnt eigene Worker die die Edits korrekt durchfuehren\n"
            f"\n"
            f"WARUM: Jede Implementation MUSS durch I/SC Pipeline laufen (CS8, INV-PM-1).\n"
            f"  Agent()-Bypass umgeht: Blueprint, Architect, testSearch, GAP-Check, Stage.\n"
            f"  Auch bei kleinen Aenderungen (M1) — der Overhead ist akzeptabel,\n"
            f"  der Shortcut bei schweren Items ist es NICHT.\n"
            f"\n"
            f"KONTEXT: CaseStudy CS8 (2026-04-07) — 4 Items ohne Pipeline implementiert.\n"
            f"  Dieser Hook verhindert Wiederholung.\n"
            f"=== ENDE IMPLEMENTATION-GATE ==="
        )

        append_guard_log(
            f"Edit '{short_path}' ohne Pipeline ({reason})",
            enforce
        )
        append_audit_log(file_path, enforce)

        if enforce:
            print(json.dumps({
                "continue": False,
                "reason": guidance
            }))
        else:
            print(json.dumps({
                "continue": True,
                "additionalContext": guidance
            }))

    except Exception as e:
        try:
            with open(LOG_FILE, "a", encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] guard_implementation_gate Error: {e}\n")
        except Exception:
            pass
        # Bei Fehler: nicht blockieren (Safety-First)
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
