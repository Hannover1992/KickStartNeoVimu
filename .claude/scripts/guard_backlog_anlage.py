#!/usr/bin/env python3
"""
guard_backlog_anlage.py  —  BL-306 AK-2 (Single-Writer-Enforcement, WARN-first)

PreToolUse-Guard: detektiert die Anlage einer NEUEN Backlog/BL-NNN-*.md-Datei via Write,
deren BL-ID NICHT im kanonischen Root-Index steht = Bypass des Single-Writers `/_backlog`
(die Wurzel des Dual-Index-Split-Brain, BL-306).

MODUS (GOAL enforce-process warn-first): WARN, NICHT BLOCK. Exit 0 + Hinweis ueber additionalContext.
Aktivierung auf BLOCK (exit 2) erst nachdem warn-Phase keine False-Positives zeigt (analog BL-165-Guards).

Registrierung (settings.json, deliberate — NICHT auto, BL-306 AK-2):
  "hooks": { "PreToolUse": [ { "matcher": "Write",
    "hooks": [{ "type": "command", "command": "python .claude/scripts/guard_backlog_anlage.py" }] } ] }

Liest Hook-JSON von stdin: { tool_name, tool_input: { file_path, content } }.
"""
import sys
import json
import os
import re

CANON = r"C:/Users/Administrator/Documents/OmniCommand/_backlog_index.md"
BL_FILE = re.compile(r"[/\\]Backlog[/\\](BL-\d+)-[^/\\]+\.md$", re.IGNORECASE)


def warn(msg):
    # WARN-Modus: additionalContext (non-blocking). Exit 0.
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": f"[BL-306 Anlage-Guard WARN] {msg}"
    }}))
    sys.exit(0)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # kein parsbarer Input -> nicht stoeren
    if data.get("tool_name") != "Write":
        sys.exit(0)
    fp = (data.get("tool_input") or {}).get("file_path", "") or ""
    m = BL_FILE.search(fp.replace("\\", "/"))
    if not m:
        sys.exit(0)
    bl_id = m.group(1)
    # Neue Datei? (Write auf existierende = Update, kein Anlage-Bypass)
    if os.path.exists(fp):
        sys.exit(0)
    # BL-ID schon im Kanon-Index? Dann ist es eine erwartete (z.B. /_backlog-vorbereitete) Anlage.
    try:
        with open(CANON, "r", encoding="utf-8") as f:
            canon = f.read()
    except Exception:
        canon = ""
    if re.search(r"^\|\s*" + re.escape(bl_id) + r"\s*\|", canon, re.MULTILINE):
        sys.exit(0)
    warn(
        f"NEUE Backlog-Datei {bl_id} wird direkt geschrieben, aber {bl_id} steht NICHT im Kanon-Index "
        f"({CANON}). Das umgeht den Single-Writer /_backlog (Dual-Index-Drift-Wurzel, BL-306). "
        f"RECOVERY: nutze `/_backlog` mode=create (schreibt Datei + Index-Append + Counter-Bump atomar), "
        f"ODER trage {bl_id} zeitnah selbst in den Root-Index ein + Counter-Bump. "
        f"(Guard im WARN-Modus — blockt nicht; BLOCK-Aktivierung nach warn-Phase.)"
    )


if __name__ == "__main__":
    main()
