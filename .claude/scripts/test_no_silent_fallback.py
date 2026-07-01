#!/usr/bin/env python3
"""BL-065 AK-13 / INV-02: Keine stillen Fallbacks im BL-Modus.

Test: Die 9 Write-Commands (5 I-Code + 4 Synthese) haben KEIN
`try/except FileNotFoundError: write_to_local(...)` Pattern und KEIN
`WARNING:` Block der einen stillen .claude/-Fallback erlaubt.
"""
import sys
import re
from pathlib import Path

WRITE_COMMANDS = [
    # 4 Synthese
    ".claude/commands/_model.md",
    ".claude/commands/_spec.md",
    ".claude/commands/_gap.md",
    ".claude/commands/_K_score.md",
    # 5 I-Code
    ".claude/commands/_I_codeAtomic.md",
    ".claude/commands/_I_codeIntegration.md",
    ".claude/commands/_I_codeSystem.md",
    ".claude/commands/_I_codeE2E.md",
    ".claude/commands/_I_codeFullSystem.md",
]

# Anti-Pattern: FALLBACK-Block der still nach .claude/ schreibt
SILENT_FALLBACK_PATTERN = re.compile(
    r'(WARNING[:\s]*.*?Fallback.*?\.claude|except\s+FileNotFoundError.*?\.claude/analysis)',
    re.DOTALL | re.IGNORECASE
)

def check_file(path):
    content = Path(path).read_text(encoding='utf-8')
    matches = SILENT_FALLBACK_PATTERN.findall(content)
    return len(matches), matches[:2]

def main():
    failures = 0
    for path in WRITE_COMMANDS:
        if not Path(path).exists():
            print(f"SKIP: {path} (nicht vorhanden)")
            continue
        count, samples = check_file(path)
        if count > 0:
            print(f"FAIL: {path}: {count} silent-fallback pattern(s)")
            for s in samples:
                print(f"  Sample: {s[:100]}")
            failures += 1
        else:
            print(f"PASS: {path}")
    if failures:
        print(f"\nFAIL: {failures}/{len(WRITE_COMMANDS)} files have silent-fallback pattern")
        sys.exit(1)
    print(f"\nPASS: {len(WRITE_COMMANDS)}/{len(WRITE_COMMANDS)} files clean")
    sys.exit(0)

if __name__ == "__main__":
    main()
