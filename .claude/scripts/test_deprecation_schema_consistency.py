#!/usr/bin/env python3
"""BL-065 AK-06/AK-07: Alle 3 obsoleten W-Commands muessen deprecated: true im Frontmatter haben."""
import sys
import re
from pathlib import Path

# V12 (2026-05-08): Pfade aktualisiert nach _archive_BL-065/-Migration.
# Vorher zeigten die Pfade auf Original-Lokation; test_archive_exists hatte
# bereits bestaetigt, dass die Dateien nach Archive verschoben sind.
COMMANDS = [
    ".claude/commands/_archive_BL-065/_W_push_orchestrate.md",
    ".claude/commands/_archive_BL-065/_W_obsidianSync.md",
    ".claude/commands/_archive_BL-065/_W_fireTogether.md",
]

def has_deprecated_true(path):
    # V12 (2026-05-08): utf-8-sig statt utf-8 — strippt BOM falls vorhanden.
    # 2 Archive-Files (_W_push_orchestrate, _W_fireTogether) haben UTF-8 BOM.
    content = Path(path).read_text(encoding='utf-8-sig')
    # Frontmatter extract (first YAML block between ---)
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return False, "no frontmatter"
    fm = m.group(1)
    if re.search(r'^deprecated:\s*true\s*$', fm, re.MULTILINE):
        return True, "ok"
    return False, "deprecated not true"

def main():
    failures = []
    for cmd in COMMANDS:
        ok, reason = has_deprecated_true(cmd)
        status = "PASS" if ok else "FAIL"
        print(f"{status}: {cmd} ({reason})")
        if not ok:
            failures.append(cmd)
    if failures:
        print(f"\nFAIL: {len(failures)}/{len(COMMANDS)} commands missing deprecated: true")
        sys.exit(1)
    print(f"\nPASS: {len(COMMANDS)}/{len(COMMANDS)} commands have deprecated: true")
    sys.exit(0)

if __name__ == "__main__":
    main()
