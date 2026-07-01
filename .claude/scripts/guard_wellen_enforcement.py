#!/usr/bin/env python3
"""
Claude Code Hook — Wellen Team Enforcement (BL-060)

PreToolUse auf Agent|TaskCreate|SendMessage. Manifest-State-basierter Guard.
Loest guard_wellen_reminder.py ab. Schichten (INV-BL060-5/8):
  1. Tool-Filter  2. Manifest lesen  3. SC_SYMBIOSE_I_ACTIVE Whitelist
  4. Amnestie (wellen_tracking_enabled=false)  5. enforceProcess lesen
  6. L1 active_team  7. L2 wellen_count (difficulty-first: easy=SKIP)
  L3: team_name WARN-only (niemals continue:false)
INV-BL060-1: top-level except -> continue:True. INV-BL060-7: ctx < 500 Zeichen.
DRY: _resolve_vault_path/read_enforce_process/append_guard_log/write_audit_entry
     via sys.path aus guard_post_gap_sequence.py (NFR-05 Form a).
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
LOG_FILE = ROOT_DIR / ".hook_debug.log"

# DRY-Import (NFR-05 Form a)
sys.path.insert(0, str(SCRIPT_DIR))
from guard_post_gap_sequence import (
    _resolve_vault_path, read_enforce_process, append_guard_log, write_audit_entry,
)

MANIFEST_FILE = _resolve_vault_path("manifest")


def read_manifest():
    if not MANIFEST_FILE or not MANIFEST_FILE.exists():
        return None
    return MANIFEST_FILE.read_text(encoding="utf-8")


def parse_pipeline_mode(content):
    m = re.search(r'pipeline_mode:\s*(\S+)', content)
    return m.group(1).strip('"\'') if m else None


def _yaml_val(val_str):
    if val_str == "true": return True
    if val_str == "false": return False
    if val_str == "null": return None
    return val_str


def parse_active_team(content):
    m = re.search(r'active_team:\s*\n((?:[ \t]+\S[^\n]*\n?)+)', content)
    if not m:
        return None
    block = m.group(1)
    result = {}
    for key in ("name", "created_at", "wellen_tracking_enabled"):
        km = re.search(rf'{key}:\s*(\S+)', block)
        if km:
            result[key] = _yaml_val(km.group(1).strip('"\''))
    return result if result else None


def parse_wellen_count(content, pipeline):
    state_key = "A_PIPELINE_STATE" if pipeline == "A" else "SC_PIPELINE_STATE"
    state_m = re.search(rf'{state_key}:(.*?)(?=\n[A-Z_]+_STATE:|\Z)', content, re.DOTALL)
    if not state_m:
        return None
    block = state_m.group(1)
    if re.search(r'wellen_count:\s*null', block):
        return None
    wc_m = re.search(r'wellen_count:(.*?)(?=\n  [a-zA-Z_]+:|\n[A-Z]|\Z)', block, re.DOTALL)
    if not wc_m:
        return None
    wc_block = wc_m.group(1)
    result = {}
    for key in ("cmd", "difficulty", "team_name", "wave_active", "violation"):
        km = re.search(rf'\b{key}:\s*(\S+)', wc_block)
        if km:
            result[key] = _yaml_val(km.group(1).strip('"\''))
    for sub in ("planned", "spawned"):
        sub_m = re.search(rf'{sub}:\s*\n((?:[ \t]+\S[^\n]+\n?)+)', wc_block)
        if sub_m:
            sub_dict = {}
            for sk in ("explorer", "drafter", "synthese", "total"):
                skm = re.search(rf'\b{sk}:\s*(\d+)', sub_m.group(1))
                if skm:
                    sub_dict[sk] = int(skm.group(1))
            result[sub] = sub_dict
    return result if result else None


def extract_prompt(tool_input):
    if isinstance(tool_input, dict):
        return (tool_input.get("prompt") or tool_input.get("description")
                or tool_input.get("message") or "")
    return str(tool_input) if tool_input else ""


def ts():
    return datetime.now().isoformat(timespec="seconds")


def log_error(e):
    try:
        with open(LOG_FILE, "a", encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] guard_wellen_enforcement Error: {e}\n")
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

        # Schicht 1: Tool-Filter
        if tool_name not in ["Agent", "TaskCreate", "SendMessage"]:
            print(json.dumps({"continue": True})); return

        prompt = extract_prompt(hook_data.get("tool_input", {}))

        # Schicht 2: Manifest lesen
        content = read_manifest()
        if not content:
            print(json.dumps({"continue": True})); return

        # Schicht 3: SC_SYMBIOSE_I_ACTIVE Whitelist (INV-BL060-5) VOR active_team
        if parse_pipeline_mode(content) == "SC_SYMBIOSE_I_ACTIVE":
            print(json.dumps({"continue": True})); return

        # Schicht 4: Amnestie wellen_tracking_enabled=false (INV-BL060-4)
        active_team = parse_active_team(content)
        if active_team and active_team.get("wellen_tracking_enabled") is False:
            write_audit_entry({"ts": ts(), "event": "ENFORCEMENT_BYPASS",
                               "reason": "wellen_tracking_enabled=false (Amnestie)"})
            print(json.dumps({"continue": True})); return

        # Schicht 5: enforceProcess (INV-BL060-2)
        enforce = read_enforce_process()

        # L3 vorberechnen (WARN-only, guard_log only — RF-03)
        l3_warning = None
        wc_a = parse_wellen_count(content, "A")
        wc_sc = parse_wellen_count(content, "SC")
        wave_active = (
            (wc_a and wc_a.get("wave_active") not in (None, "null"))
            or (wc_sc and wc_sc.get("wave_active") not in (None, "null"))
        )
        if wave_active and "team_name" not in (prompt or ""):
            l3_warning = "[Wellen-Guard L3 WARN] team_name fehlt im Prompt waehrend aktiver Welle."
            append_guard_log("L3_WARN", l3_warning, blocked=False)

        # Schicht 6: L1 active_team Check
        if not active_team or not active_team.get("name"):
            ctx = "[Wellen-Guard L1] kein active_team — TeamCreate ausfuehren."
            if enforce:
                append_guard_log("WELLEN_MISSING", "active_team fehlt — HARD GATE BLOCK", blocked=True)
                write_audit_entry({"ts": ts(), "event": "HARD_GATE_BLOCK",
                                   "reason": "active_team missing", "tool": tool_name})
                print(json.dumps({"continue": False, "additionalContext": ctx[:499]})); return
            else:
                write_audit_entry({"ts": ts(), "event": "ENFORCEMENT_BYPASS",
                                   "reason": "L1 active_team missing, enforceProcess=false"})
                ctx_full = (ctx + (" " + l3_warning if l3_warning else ""))[:499]
                print(json.dumps({"continue": True, "additionalContext": ctx_full})); return

        # Schicht 7: L2 wellen_count Check (difficulty-first: easy=SKIP)
        wc = wc_a or wc_sc
        if wc and wc.get("difficulty", "normal") != "easy":
            planned = wc.get("planned", {})
            spawned = wc.get("spawned", {})
            wave = wc.get("wave_active")
            problem = None
            if wave == "explorer":
                exp = planned.get("explorer", 0)
                if exp > 0 and spawned.get("explorer", 0) < exp:
                    problem = f"L2: Wave 1 explorer {spawned.get('explorer',0)}/{exp}"
            elif wave == "drafter":
                exp = planned.get("drafter", 0)
                if spawned.get("drafter", 0) < exp:
                    problem = f"L2: Wave 2 drafter {spawned.get('drafter',0)}/{exp}"
            if problem:
                ctx = f"[Wellen-Guard {problem}]"
                if enforce:
                    append_guard_log("L2_INCOMPLETE", problem, blocked=True)
                    write_audit_entry({"ts": ts(), "event": "L2_INCOMPLETE",
                                       "details": problem, "tool": tool_name})
                    print(json.dumps({"continue": False, "additionalContext": ctx[:499]})); return
                else:
                    write_audit_entry({"ts": ts(), "event": "ENFORCEMENT_BYPASS", "reason": problem})
                    print(json.dumps({"continue": True, "additionalContext": ctx[:499]})); return

        # Alle Checks bestanden
        if l3_warning:
            print(json.dumps({"continue": True, "additionalContext": l3_warning[:499]}))
        else:
            print(json.dumps({"continue": True}))

    except Exception as e:
        # INV-BL060-1: Fail-Safe — NIEMALS blockieren bei Exception
        log_error(e)
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
