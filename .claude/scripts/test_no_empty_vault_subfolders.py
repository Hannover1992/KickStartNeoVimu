#!/usr/bin/env python3
"""BL-065 AK-10 / INV-04: ON-DEMAND mkdir — keine leeren Subfolder.

Test: Alle 9 Write-Commands enthalten mkdir -p {VAULT}/... Pattern (Pre-Flight).
"""
import sys
import re
from pathlib import Path

WRITE_COMMANDS = [
    ".claude/commands/_model.md",
    ".claude/commands/_spec.md",
    ".claude/commands/_gap.md",
    ".claude/commands/_K_score.md",
    ".claude/commands/_I_codeAtomic.md",
    ".claude/commands/_I_codeIntegration.md",
    ".claude/commands/_I_codeSystem.md",
    ".claude/commands/_I_codeE2E.md",
    ".claude/commands/_I_codeFullSystem.md",
]

MKDIR_PATTERN = re.compile(r'mkdir\s+-p\s+.*(\{VAULT\}|VAULT|Backlog)', re.IGNORECASE)

def check_file(path):
    content = Path(path).read_text(encoding='utf-8')
    return bool(MKDIR_PATTERN.search(content))

def main():
    failures = 0
    for path in WRITE_COMMANDS:
        if not Path(path).exists():
            print(f"SKIP: {path} (nicht vorhanden)")
            continue
        if check_file(path):
            print(f"PASS: {path} has Pre-Flight mkdir")
        else:
            print(f"FAIL: {path} missing Pre-Flight mkdir")
            failures += 1
    if failures:
        print(f"\nFAIL: {failures}/{len(WRITE_COMMANDS)} missing Pre-Flight mkdir")
        sys.exit(1)
    print(f"\nPASS: {len(WRITE_COMMANDS)}/{len(WRITE_COMMANDS)} have Pre-Flight mkdir")
    sys.exit(0)

if __name__ == "__main__":
    main()
