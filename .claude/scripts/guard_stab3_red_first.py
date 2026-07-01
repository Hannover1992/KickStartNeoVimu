#!/usr/bin/env python3
"""
Stab S#3 RED-Test-First Hook (TDD-Invertier-Stop).

Bei Modus M3 (TDD): vor jedem Code-Edit muss eine Test-Datei in den letzten 5 Tool-Calls
modifiziert worden sein. Fixt das Round-11-Pattern (0 RED-Tests vor Code).
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
STATE_FILE = ROOT_DIR / ".claude" / "temp" / "stab3_red_state.json"
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

CODE_EXTS = (".ts", ".tsx", ".cs", ".py", ".js", ".jsx", ".java", ".go", ".rs")
TEST_PATTERNS = [".spec.ts", ".spec.tsx", ".test.ts", ".test.tsx", ".test.js", ".test.py",
                  "Test.cs", "_test.go", "_test.py", "Spec.cs", ".spec.cs"]


def get_state_file():
    return Path(os.environ.get("OMNI_STAB3_STATE_FILE", STATE_FILE))


def load_state():
    sf = get_state_file()
    if not sf.exists():
        return {"recent_edits": []}
    try:
        return json.loads(sf.read_text(encoding="utf-8"))
    except Exception:
        return {"recent_edits": []}


def save_state(state):
    sf = get_state_file()
    sf.parent.mkdir(parents=True, exist_ok=True)
    try:
        sf.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def read_enforce_process():
    if os.environ.get("OMNI_ENFORCE_STAB3_GUARD") == "1":
        return True
    return False


def get_current_modus():
    """Liest aktuellen Modus aus Manifest."""
    test_override = os.environ.get("OMNI_STAB3_MODUS_OVERRIDE")
    if test_override:
        return test_override
    # Pruefe manifest
    for name in ["_factory_manifest.md", "_manifest.md"]:
        p = ROOT_DIR / name
        if p.exists():
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                # Letzte modus: Mention
                matches = re.findall(r"modus\s*:\s*(M\d)", content)
                if matches:
                    return matches[-1]
            except Exception:
                pass
    return None


def is_test_file(path):
    p = path.lower()
    return any(pat in p for pat in TEST_PATTERNS)


def is_code_file(path):
    p = path.lower()
    if is_test_file(p):
        return False
    return any(p.endswith(ext) for ext in CODE_EXTS)


def has_pragmatik_override(content_or_manifest):
    test_path = os.environ.get("OMNI_STAB3_PRAGMATIK")
    if test_path == "1":
        return True
    # Manifest-Check
    for name in ["_factory_manifest.md", "_manifest.md"]:
        p = ROOT_DIR / name
        if p.exists():
            try:
                mc = p.read_text(encoding="utf-8", errors="replace")
                if re.search(r"tdd_pragmatik_reason\s*:", mc):
                    return True
            except Exception:
                pass
    return False


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **STAB3_RED_FIRST** [{action}]: {msg}\n")
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

    if event.get("tool_name") not in ("Edit", "Write"):
        print(json.dumps({"continue": True}))
        return

    tool_input = event.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "")

    state = load_state()
    state["recent_edits"] = (state.get("recent_edits") or [])[-9:]  # halte max 10

    # Track diesen Edit
    state["recent_edits"].append({"path": file_path, "ts": datetime.now().isoformat()})

    if not is_code_file(file_path):
        save_state(state)
        print(json.dumps({"continue": True}))
        return

    # Code-Edit: Check Modus
    modus = get_current_modus()
    if modus != "M3":
        save_state(state)
        print(json.dumps({"continue": True}))  # M3 ist Pflicht-TDD, andere Modi unangetastet
        return

    # M3-Mode: pruefe ob Test-Edit in letzten 5 Tool-Calls
    recent_5 = state["recent_edits"][-6:-1]  # die 5 vor dem aktuellen
    test_edit_present = any(is_test_file(e.get("path", "")) for e in recent_5)

    if test_edit_present:
        save_state(state)
        print(json.dumps({"continue": True}))
        return

    # Pragmatik-Override
    if has_pragmatik_override(""):
        msg = f"[GUARD-VIOLATION] STAB3_RED_FIRST: M3-Mode + Code-Edit ohne RED-Test (pragmatik_reason aktiv)"
        append_guard_log(msg, False)
        save_state(state)
        print(json.dumps({"continue": True, "message": msg + " WARN-only (pragmatik)."}))
        return

    enforce = read_enforce_process()
    msg = f"[GUARD-VIOLATION] STAB3_RED_FIRST: M3-Mode aber kein Test-Edit in den letzten 5 Tool-Calls vor Code-Edit ({file_path})"
    append_guard_log(msg, enforce)
    save_state(state)
    print(json.dumps({
        "continue": not enforce,
        "message": msg + (" BLOCKED." if enforce else " WARNED.")
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_stab3 ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
