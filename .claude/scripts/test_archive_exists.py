#!/usr/bin/env python3
"""BL-065 AK-08 / INV-07: Obsolete W-Commands archiviert (nicht geloescht).

Tests:
1. Die 3 Dateien sind NICHT mehr am Original-Pfad
2. Die 3 Dateien SIND in _archive_BL-065/
3. _archive_BL-065/README.md existiert
4. README.md enthaelt alle 4 Pflichtfelder: Grund (BL-065), Baseline-SHA, Rollback-Befehl, Datum
5. _W_push_orchestrate.md hat deprecated: true (aus Commit 1)
"""
import sys
import re
from pathlib import Path

OBSOLETE_COMMANDS = [
    "_W_push_orchestrate.md",
    "_W_obsidianSync.md",
    "_W_fireTogether.md",
]

ORIGINAL_DIR = Path(".claude/commands")
ARCHIVE_DIR = Path(".claude/commands/_archive_BL-065")

def main():
    failures = 0

    # Test 1: Nicht mehr am Original
    for cmd in OBSOLETE_COMMANDS:
        orig = ORIGINAL_DIR / cmd
        if orig.exists():
            print(f"FAIL 1: {cmd} noch am Original-Pfad")
            failures += 1
        else:
            print(f"PASS 1: {cmd} nicht mehr am Original")

    # Test 2: In _archive_BL-065/
    for cmd in OBSOLETE_COMMANDS:
        archived = ARCHIVE_DIR / cmd
        if not archived.exists():
            print(f"FAIL 2: {cmd} nicht im Archive")
            failures += 1
        else:
            print(f"PASS 2: {cmd} archiviert")

    # Test 3: README.md existiert
    readme = ARCHIVE_DIR / "README.md"
    if not readme.exists():
        print(f"FAIL 3: README.md fehlt in {ARCHIVE_DIR}")
        failures += 1
    else:
        print(f"PASS 3: README.md vorhanden")

        # Test 4: README hat 4 Pflichtfelder
        content = readme.read_text(encoding='utf-8')
        required = {
            "BL-065": "Grund",
            "Baseline": "Baseline-SHA",
            "Rollback": "Rollback-Befehl",
            "2026-04": "Datum",
        }
        for key, label in required.items():
            if key not in content:
                print(f"FAIL 4: README.md fehlt '{label}' (Pattern '{key}')")
                failures += 1
            else:
                print(f"PASS 4: README.md hat {label}")

    # Test 5: _W_push_orchestrate.md hat deprecated: true (aus Commit 1)
    archived_push = ARCHIVE_DIR / "_W_push_orchestrate.md"
    if archived_push.exists():
        content = archived_push.read_text(encoding='utf-8')
        if re.search(r'^deprecated:\s*true\s*$', content, re.MULTILINE):
            print(f"PASS 5: _W_push_orchestrate.md hat deprecated: true")
        else:
            print(f"FAIL 5: _W_push_orchestrate.md fehlt deprecated: true")
            failures += 1

    if failures:
        print(f"\nFAIL: {failures} errors")
        sys.exit(1)
    print(f"\nPASS: 3/3 archived, README complete, deprecated: true preserved")
    sys.exit(0)

if __name__ == "__main__":
    main()
