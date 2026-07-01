#!/usr/bin/env python3
"""BL-065 AK-02 / INV-06: Hybrid-Marker nur mit echter Implementation.

Test: Der String 'Hybrid-Strategie (BL-050)' darf NICHT mehr in aktiven I-Code-Commands stehen.
Stattdessen: 'Vault-First (BL-065)' Marker (5x).
"""
import sys
import re
from pathlib import Path

I_CODE_COMMANDS = [
    ".claude/commands/_I_codeAtomic.md",
    ".claude/commands/_I_codeIntegration.md",
    ".claude/commands/_I_codeSystem.md",
    ".claude/commands/_I_codeE2E.md",
    ".claude/commands/_I_codeFullSystem.md",
]

OLD_MARKER = "Hybrid-Strategie (BL-050)"
NEW_MARKER = "Vault-First (BL-065)"

def main():
    failures = 0
    for path in I_CODE_COMMANDS:
        content = Path(path).read_text(encoding='utf-8')
        has_old = OLD_MARKER in content
        has_new = NEW_MARKER in content
        if has_old:
            print(f"FAIL: {path}: still has '{OLD_MARKER}'")
            failures += 1
        elif not has_new:
            print(f"FAIL: {path}: missing '{NEW_MARKER}'")
            failures += 1
        else:
            print(f"PASS: {path}")
    if failures:
        print(f"\nFAIL: {failures}/{len(I_CODE_COMMANDS)} commands not migrated")
        sys.exit(1)
    print(f"\nPASS: {len(I_CODE_COMMANDS)}/{len(I_CODE_COMMANDS)} commands migrated to Vault-First marker")
    sys.exit(0)

if __name__ == "__main__":
    main()
