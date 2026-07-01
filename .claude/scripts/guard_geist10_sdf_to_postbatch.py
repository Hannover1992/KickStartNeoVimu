#!/usr/bin/env python3
"""
Geist-Hook G#10: SDF Phase 4 loopDecision=TERMINATE → PostBatch (BL-213 enforcement).

Wenn `phase_4_loopDecision: TERMINATE` ins Manifest geschrieben wird, MUSS innerhalb
2 Tool-Calls Skill(_PostBatch_orchestrate) feuern. Sonst BLOCK.

State persistiert in .claude/temp/geist10_state.json.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
STATE_FILE = ROOT_DIR / ".claude" / "temp" / "geist10_state.json"
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

MAX_TOOL_CALLS_AFTER_TERMINATE = 2


def get_state_file():
    test_override = os.environ.get("OMNI_GEIST10_STATE_FILE")
    return Path(test_override) if test_override else STATE_FILE


def load_state():
    sf = get_state_file()
    if not sf.exists():
        return {"expected_postbatch": False, "last_terminate_ts": None, "tool_call_count": 0}
    try:
        return json.loads(sf.read_text(encoding="utf-8"))
    except Exception:
        return {"expected_postbatch": False, "last_terminate_ts": None, "tool_call_count": 0}


def save_state(state):
    sf = get_state_file()
    sf.parent.mkdir(parents=True, exist_ok=True)
    try:
        sf.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def read_enforce_process():
    if os.environ.get("OMNI_ENFORCE_GEIST10_GUARD") == "1":
        return True
    return os.environ.get("OMNI_GEIST10_ENFORCE", "false") == "true"


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **GEIST10_SDF_POSTBATCH** [{action}]: {msg}\n")
    except Exception:
        pass


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

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}
    state = load_state()

    # Trigger 1: Edit/Write writes "loopDecision: TERMINATE" → arm state
    if tool_name in ("Edit", "Write"):
        new_content = tool_input.get("new_string", "") or tool_input.get("content", "")
        if re.search(r"loopDecision\s*:\s*TERMINATE|phase_4_loopDecision\s*:\s*TERMINATE", new_content):
            state["expected_postbatch"] = True
            state["last_terminate_ts"] = datetime.now().isoformat()
            state["tool_call_count"] = 0
            save_state(state)
            print(json.dumps({"continue": True}))
            return

    # If armed: count tool calls until PostBatch
    if state["expected_postbatch"]:
        if tool_name == "Skill" and tool_input.get("skill") == "_PostBatch_orchestrate":
            state = {"expected_postbatch": False, "last_terminate_ts": None, "tool_call_count": 0}
            save_state(state)
            print(json.dumps({"continue": True}))
            return

        # AUTO-DISARM bei Stale-State (BL-RCA-Round14 Fix 2026-05-28):
        # Wenn ts > 30 Tool-Calls AND ts > 1h alt -> automatisch disarm + reset
        # Verhindert "lawiniert"-Spam wie 64x WARN in Round 14
        STALE_TOOL_CALLS_THRESHOLD = 30
        STALE_AGE_HOURS = 1
        try:
            ts_str = state.get("last_terminate_ts")
            if ts_str:
                ts = datetime.fromisoformat(ts_str)
                age_hours = (datetime.now() - ts).total_seconds() / 3600
                if state["tool_call_count"] > STALE_TOOL_CALLS_THRESHOLD and age_hours > STALE_AGE_HOURS:
                    # Stale → auto-reset (User hat wahrscheinlich neuen Lauf gestartet ohne PostBatch fertig)
                    state = {"expected_postbatch": False, "last_terminate_ts": None, "tool_call_count": 0}
                    save_state(state)
                    print(json.dumps({"continue": True}))
                    return
        except Exception:
            pass

        state["tool_call_count"] += 1
        save_state(state)
        if state["tool_call_count"] > MAX_TOOL_CALLS_AFTER_TERMINATE:
            enforce = read_enforce_process()
            msg = f"[GUARD-VIOLATION] GEIST10_SDF_POSTBATCH: loopDecision=TERMINATE seit {state['tool_call_count']} Tool-Calls aber kein Skill(_PostBatch_orchestrate)"
            append_guard_log(msg, enforce)
            print(json.dumps({
                "continue": not enforce,
                "message": msg + (" BLOCKED." if enforce else " WARNED.")
            }))
            return

    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_geist10 ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
