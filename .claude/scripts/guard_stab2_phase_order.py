#!/usr/bin/env python3
"""
Stab S#2 Phase-Sequence-Order Hook.

Prueft dass Phasen in einer Pipeline in der vorgegebenen Reihenfolge geschrieben werden.
Special: SKIP-Marker erfordern `skip_reason:` (fixt Round-11-F10 Drift).
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"


# Phasen-Sequenz mit Alternativ-Namen pro Position (Tuple = "ODER")
PHASE_SEQUENCES = {
    "SDF_phase3": [
        ("phase_3_1_recalibrate",),
        ("phase_3_2_postBatch", "phase_3_2_postItem"),
        ("phase_3_3_statusTransition",),
        ("phase_3_5_modelSync",),
    ],
}


def read_enforce_process():
    if os.environ.get("OMNI_ENFORCE_STAB2_GUARD") == "1":
        return True
    return False


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **STAB2_PHASE_ORDER** [{action}]: {msg}\n")
    except Exception:
        pass


def check_phase_order(new_content):
    """Prueft: wenn phase_N geschrieben wird, muss phase_N-1 vorher im content sein."""
    violations = []

    for seq_name, phases in PHASE_SEQUENCES.items():
        present_indices = []
        for i, phase_alts in enumerate(phases):
            for ph in phase_alts:
                if re.search(rf"{ph}\s*:", new_content):
                    present_indices.append((i, ph))
                    break

        if not present_indices:
            continue

        for i, ph in present_indices:
            status_match = re.search(rf"{ph}\s*:\s*(\w+)", new_content)
            status = status_match.group(1) if status_match else "DONE"

            if i > 0:
                # Prev-Phase Check (alle Alternatives akzeptieren)
                prev_alts = phases[i - 1]
                prev_present = any(re.search(rf"{p}\s*:", new_content) for p in prev_alts)
                if not prev_present and status.upper() != "SKIP":
                    violations.append(f"{ph} ohne {'/'.join(prev_alts)} vorher")

            if status.upper() == "SKIP":
                ph_pos = new_content.find(ph)
                if ph_pos != -1:
                    window = new_content[ph_pos:ph_pos + 400]
                    if not re.search(r"skip_reason|modelSync_skip_reason|empty_reason", window):
                        violations.append(f"{ph}: SKIP ohne skip_reason")

    return violations


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
    if "_manifest.md" not in file_path:
        print(json.dumps({"continue": True}))
        return

    new_content = tool_input.get("new_string", "") or tool_input.get("content", "")
    violations = check_phase_order(new_content)

    if not violations:
        print(json.dumps({"continue": True}))
        return

    enforce = read_enforce_process()
    msg = f"[GUARD-VIOLATION] STAB2_PHASE_ORDER: {'; '.join(violations)}"
    append_guard_log(msg, enforce)
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
                log.write(f"[{datetime.now()}] guard_stab2 ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
