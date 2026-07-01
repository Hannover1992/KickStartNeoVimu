#!/usr/bin/env python3
"""
guard_vertrag_read.py — PreToolUse-Hook fuer Vertrag-Lese-Disziplin (BL-153 V9, BL-154 PL-32).

Pruefung: Bei Skill/Agent-Spawn muss der Prompt VERTRAG-Block-Marker enthalten
oder mind. ein "VERTRAG:" / "║" Symbol — sonst WARNUNG (kein BLOCK, NON-BLOCKING).

Stdin: JSON-Event (PreToolUse)
Exit: 0 = OK, 0 = WARN-only (nicht blocking — User-Entscheidung)
"""
import json, sys

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
        event = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool = event.get("tool_name", "")
    if tool not in ("Skill", "Agent"):
        sys.exit(0)
    payload = json.dumps(event.get("tool_input", {}))
    has_vertrag = ("VERTRAG" in payload) or ("║" in payload) or ("VERTRAG-Block" in payload)
    if not has_vertrag:
        sys.stderr.write(
            "[VERTRAG-GUARD] WARNUNG: Spawn ohne VERTRAG-Marker im Prompt. "
            "BL-153 V9 KERN-PAIN — Worker kann Vertrag still ignorieren. "
            f"Tool={tool}\n"
        )
    sys.exit(0)

if __name__ == "__main__":
    main()
