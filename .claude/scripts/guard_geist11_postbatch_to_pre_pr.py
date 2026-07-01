#!/usr/bin/env python3
"""
Geist-Hook G#11: PostBatch → Pre_PR (Auto-Chain Enforcement, BL-213/214).

Wenn `POSTBATCH_PIPELINE_STATE.batch_done: true` AND `BDF_PIPELINE_STATE.bdf_all_items_done: true`
ins Manifest geschrieben werden, MUSS innerhalb 3 Tool-Calls Skill(_Pre_PR_orchestrate) feuern.

State persistiert in .claude/temp/geist11_state.json.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
STATE_FILE = ROOT_DIR / ".claude" / "temp" / "geist11_state.json"
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

MAX_TOOL_CALLS_AFTER_BATCH_DONE = 3


def get_state_file():
    test_override = os.environ.get("OMNI_GEIST11_STATE_FILE")
    return Path(test_override) if test_override else STATE_FILE


def load_state():
    sf = get_state_file()
    if not sf.exists():
        return {"expected_pre_pr": False, "last_batch_done_ts": None, "tool_call_count": 0}
    try:
        return json.loads(sf.read_text(encoding="utf-8"))
    except Exception:
        return {"expected_pre_pr": False, "last_batch_done_ts": None, "tool_call_count": 0}


def save_state(state):
    sf = get_state_file()
    sf.parent.mkdir(parents=True, exist_ok=True)
    try:
        sf.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def read_enforce_process():
    if os.environ.get("OMNI_ENFORCE_GEIST11_GUARD") == "1":
        return True
    return os.environ.get("OMNI_GEIST11_ENFORCE", "false") == "true"


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **GEIST11_POSTBATCH_PRE_PR** [{action}]: {msg}\n")
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

    # Trigger: Edit/Write writes "batch_done: true" AND "bdf_all_items_done: true"
    if tool_name in ("Edit", "Write"):
        new_content = tool_input.get("new_string", "") or tool_input.get("content", "")
        has_batch_done = re.search(r"batch_done\s*:\s*true", new_content)
        has_all_items_done = re.search(r"bdf_all_items_done\s*:\s*true", new_content)
        if has_batch_done and has_all_items_done:
            state["expected_pre_pr"] = True
            state["last_batch_done_ts"] = datetime.now().isoformat()
            state["tool_call_count"] = 0
            save_state(state)
            print(json.dumps({"continue": True}))
            return

    # If armed: count tool calls until Pre_PR
    if state["expected_pre_pr"]:
        if tool_name == "Skill" and tool_input.get("skill") == "_Pre_PR_orchestrate":
            state = {"expected_pre_pr": False, "last_batch_done_ts": None, "tool_call_count": 0}
            save_state(state)
            print(json.dumps({"continue": True}))
            return
        state["tool_call_count"] += 1
        save_state(state)
        if state["tool_call_count"] > MAX_TOOL_CALLS_AFTER_BATCH_DONE:
            enforce = read_enforce_process()
            msg = f"[GUARD-VIOLATION] GEIST11_POSTBATCH_PRE_PR: batch_done+all_items_done seit {state['tool_call_count']} Tool-Calls aber kein Skill(_Pre_PR_orchestrate)"
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
                log.write(f"[{datetime.now()}] guard_geist11 ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
