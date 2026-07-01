#!/usr/bin/env python3
"""
Claude Code Hook — Wellen-Reminder (Guard-Enforcement CS7)

Pre-Hook: Wenn difficulty=normal/hard und ein Pipeline-Command gestartet wird,
prueft ob Wellen-Pattern aktiv ist (mehrere Agents statt einer).

enforceProcess=true (Default): BLOCKIERT Violations (continue=false)
enforceProcess=false: NUR Warning (continue=true)
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
LOG_FILE = ROOT_DIR / ".hook_debug.log"

# Commands die bei normal/hard IMMER Wellen brauchen
WELLEN_COMMANDS = [
    "_W_fetch", "_taskDefinition", "_model", "_spec", "_gap", "_K_score",
]

EXPECTED_AGENTS_NORMAL = {"explorer": 5, "drafter": 3, "synthese": 1}
EXPECTED_AGENTS_HARD = {"explorer": 9, "drafter": 5, "synthese": 1}


def read_enforce_process():
    """Liest enforceProcess aus _session_params.md. Default: true.

    Aufloesung: OMNI_SESSION_PARAMS_WELLEN (Test-Override, BL-422 AK-2) >
    vault-resolved SESSION_PARAMS_FILE > Default true.
    """
    import os as _os
    _enforce_re = re.compile(r'\*\*enforceProcess:\*\*\s*(true|false)', re.IGNORECASE)
    # OMNI_SESSION_PARAMS_WELLEN env override (Test-Seam, analog OMNI_SESSION_PARAMS in guard_agent_prompt_validator)
    sp = _os.environ.get("OMNI_SESSION_PARAMS_WELLEN")
    if sp and Path(sp).exists():
        try:
            content = Path(sp).read_text(encoding="utf-8", errors="replace")
            m = _enforce_re.search(content)
            if m:
                return m.group(1).lower() == "true"
        except Exception:
            pass
        return True  # Temp-file vorhanden aber kein Match -> konservativ enforce
    try:
        if SESSION_PARAMS_FILE and SESSION_PARAMS_FILE.exists():
            content = SESSION_PARAMS_FILE.read_text(encoding="utf-8")
            match = re.search(r'\*\*enforceProcess:\*\*\s*(true|false)', content)
            if match:
                return match.group(1) == "true"
    except Exception:
        pass
    return True


def read_difficulty():
    """Liest difficulty primaer aus _session_params.md, Fallback Manifest.

    Aufloesung: OMNI_SESSION_PARAMS_WELLEN (Test-Override, BL-422 AK-2) >
    vault-resolved SESSION_PARAMS_FILE > Manifest > 'unknown'.
    """
    import os as _os
    _diff_re = re.compile(r'\*\*difficulty:\*\*\s*(easy|normal|hard)', re.IGNORECASE)
    # OMNI_SESSION_PARAMS_WELLEN env override
    sp = _os.environ.get("OMNI_SESSION_PARAMS_WELLEN")
    if sp and Path(sp).exists():
        try:
            content = Path(sp).read_text(encoding="utf-8", errors="replace")
            m = _diff_re.search(content)
            if m:
                return m.group(1)
        except Exception:
            pass
    try:
        if SESSION_PARAMS_FILE and SESSION_PARAMS_FILE.exists():
            content = SESSION_PARAMS_FILE.read_text(encoding="utf-8")
            match = re.search(r'\*\*difficulty:\*\*\s*(easy|normal|hard)', content)
            if match:
                return match.group(1)
        if MANIFEST_FILE and MANIFEST_FILE.exists():
            content = MANIFEST_FILE.read_text(encoding="utf-8")
            match = re.search(r'difficulty[=:]\s*(easy|normal|hard)', content)
            if match:
                return match.group(1)
    except Exception:
        pass
    return "unknown"


def is_wellen_worker_marker(prompt_text):
    """BL-064 T4 RF-04/RF-08: Case-insensitive Header-Suffix-Matcher.
    Identisch zu guard_agent_prompt_validator.py — INV-07 erlaubt Duplikation."""
    if not prompt_text:
        return False
    header = prompt_text[:200].lower()
    suffixes = ["-e0", "-d0", "-synthese", "explorer", "drafter",
                "synthese", "welle", "worker", "observe"]
    return any(suffix in header for suffix in suffixes)


def detect_single_agent_for_wellen_command(prompt_text):
    """Erkennt ob ein einzelner Agent einen Wellen-Command komplett ausfuehren soll.
    BL-064 T3 RF-03: 3-Schichten-Whitelist."""
    if not prompt_text:
        return False, None
    # BL-064 T3 RF-03 Schicht 1: Orchestrator-Whitelist
    if any(o in prompt_text for o in ['_I_orchestrate', '_A_orchestrate', '_SC_orchestrate']):
        return False, None
    # BL-064 T3 RF-03 Schicht 2: SC-Pipeline-Whitelist
    if any(sc in prompt_text for sc in ['_SC_observe', '_SC_hypothese',
                                         '_SC_implement', '_SC_ergebnis']):
        return False, None
    # BL-064 T3 Schicht 3: Header-basiertes case-insensitives Suffix-Matching
    for cmd in WELLEN_COMMANDS:
        if cmd in prompt_text:
            if not is_wellen_worker_marker(prompt_text):
                return True, cmd
    return False, None


def append_guard_log(violation_type, details, blocked):
    """Appende Violation an GUARD_LOG Datei."""
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = f"- [{timestamp}] **{violation_type}** [{action}]: {details}\n"
        with open(GUARD_LOG_FILE, "a", encoding='utf-8') as f:
            f.write(entry)
    except Exception:
        pass


def append_audit_event(violation_type, details, blocked, ctx=None):
    """BL-064 T5 RF-05: Unified Audit-Schema fuer alle Guards."""
    try:
        AUDIT_DIR = ROOT_DIR / ".claude" / "audit"
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        event = {
            "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "event": "GUARD_BLOCK" if blocked else "GUARD_WARN",
            "level": "BLOCK" if blocked else "WARN",
            "violation": violation_type,
            "details": details,
            "ctx": ctx or {"guard": "wellen_reminder"},
        }
        with open(AUDIT_DIR / "audit.jsonl", "a", encoding='utf-8') as f:
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

        if tool_name not in ["Agent", "TaskCreate", "SendMessage"]:
            print(json.dumps({"continue": True}))
            return

        prompt = ""
        if isinstance(tool_input, dict):
            prompt = tool_input.get("prompt", "") or tool_input.get("description", "") or tool_input.get("message", "")
        elif isinstance(tool_input, str):
            prompt = tool_input

        difficulty = read_difficulty()
        enforce = read_enforce_process()

        if difficulty in ["normal", "hard"]:
            is_single, cmd = detect_single_agent_for_wellen_command(prompt)
            if is_single:
                expected = EXPECTED_AGENTS_NORMAL if difficulty == "normal" else EXPECTED_AGENTS_HARD
                total = sum(expected.values())
                warning = (
                    f"[WELLEN-VIOLATION] {cmd} bei difficulty={difficulty} "
                    f"braucht Wellen-Pattern ({total} Agents: "
                    f"{expected['explorer']}E + {expected['drafter']}D + {expected['synthese']}S), "
                    f"aber nur 1 Agent erkannt! "
                    f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
                )
                print(json.dumps({
                    "continue": not enforce,
                    "message": warning
                }))
                append_guard_log(
                    "WELLEN_MISSING",
                    f"{cmd} bei difficulty={difficulty} ohne Wellen-Pattern",
                    enforce
                )
                append_audit_event(
                    "WELLEN_MISSING",
                    f"{cmd} bei difficulty={difficulty} ohne Wellen-Pattern",
                    enforce
                )
                return

        print(json.dumps({"continue": True}))

    except Exception as e:
        try:
            with open(LOG_FILE, "a", encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] guard_wellen_reminder Error: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
