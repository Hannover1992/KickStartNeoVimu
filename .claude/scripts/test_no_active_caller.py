#!/usr/bin/env python3
"""BL-065 AK-04: _W_orchestrate und _SC_implement duerfen die 3 obsoleten W-Commands
NICHT mehr aktiv aufrufen. Historische Kommentare (beginnend mit # BL-065: removed)
sind erlaubt."""
import sys
import re
from pathlib import Path

OBSOLETE = ["_W_push_orchestrate", "_W_obsidianSync", "_W_fireTogether"]

# Aktive Treffer: Zeilen die nicht mit # BL-065: removed annotiert sind
def count_active_calls(path):
    content = Path(path).read_text(encoding='utf-8')
    lines = content.split("\n")
    active = []
    for i, line in enumerate(lines, 1):
        for obs in OBSOLETE:
            if obs in line:
                # Pruefe ob Zeile ein Kommentar mit "BL-065: removed" ist
                stripped = line.strip()
                if stripped.startswith("#") and "BL-065" in line and "removed" in line:
                    continue  # Historie-Kommentar erlaubt
                # Pruefe ob innerhalb eines Code-Blocks mit removed-Marker
                active.append((i, line.rstrip()))
    return active

def main():
    failures = 0
    for path in [".claude/commands/_W_orchestrate.md", ".claude/commands/_SC_implement.md"]:
        active = count_active_calls(path)
        if active:
            print(f"FAIL: {path} — {len(active)} active caller(s):")
            for lineno, line in active[:10]:  # max 10 Zeilen zeigen
                print(f"  Z.{lineno}: {line[:80]}")
            if len(active) > 10:
                print(f"  ... und {len(active) - 10} weitere")
            failures += 1
        else:
            print(f"PASS: {path}")
    if failures:
        print(f"\nFAIL: {failures}/2 files have active callers")
        sys.exit(1)
    print(f"\nPASS: 2/2 files clean (0 active callers)")
    sys.exit(0)

if __name__ == "__main__":
    main()
