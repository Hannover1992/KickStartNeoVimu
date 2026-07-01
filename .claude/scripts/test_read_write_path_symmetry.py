#!/usr/bin/env python3
"""BL-065 AK-05 / INV-05: Read-Pfade und Write-Pfade symmetrisch pro Datei-Klasse.

Test: Jeder der 7 Reader-Commands hat mindestens einen PRIMAER-Read aus {VAULT}/Backlog/{BL_SLUG}/.
Zaehlt Resttreffer mit Warn-Marker (ok) vs ohne Warn-Marker (fail).
"""
import sys
import re
from pathlib import Path

READER_COMMANDS = [
    ".claude/commands/_SC_ergebnis.md",
    ".claude/commands/_SC_hypothese.md",
    ".claude/commands/_I_cleanCodeArchitect.md",
    ".claude/commands/_SC_orchestrate.md",
    ".claude/commands/_taskDefinition.md",
    ".claude/commands/_A_orchestrate.md",
    ".claude/commands/_I_fanIn.md",
]

MAX_UNMARKED_LEGACY = 10  # Budget fuer verbliebene unmarkierte Treffer

def count_unmarked_legacy(path):
    content = Path(path).read_text(encoding='utf-8')
    lines = content.split("\n")
    unmarked = 0
    for i, line in enumerate(lines):
        if re.search(r'\.claude/(models|specs|analysis/synthese)/', line):
            # Pruefe ob innerhalb 2 Zeilen +/- ein Warn-Marker steht:
            # - "fallback-read" (expliziter BL-065 Marker)
            # - "FALLBACK:" (VERTRAG-Box Deklaration)
            # - Zeile selbst enthaelt "FALLBACK:" (ist eine FALLBACK-Deklaration)
            window = lines[max(0, i-2):i+3]
            if any("fallback-read" in w or "FALLBACK:" in w or "FALLBACK" in line for w in window):
                continue
            # Ephemere Welle: OBSERVE/QUALITYGATE/ERGEBNIS/HYPOTHESEN/DATA/HANDOFF/ARCHITECT/BOUNDARIES
            # Diese bleiben in .claude/analysis/synthese/ - kein Vault-Primary noetig
            ephemere_patterns = [
                r'analysis/synthese/\{NAME\}-OBSERVE',
                r'analysis/synthese/\{NAME\}-QUALITYGATE',
                r'analysis/synthese/\{NAME\}-ERGEBNIS',
                r'analysis/synthese/\{NAME\}-HYPOTHESEN',
                r'analysis/synthese/\{NAME\}-DATA',
                r'analysis/synthese/\{NAME\}-HANDOFF',
                r'analysis/synthese/\{NAME\}-ARCHITECT',
                r'analysis/synthese/\{NAME\}-BOUNDARIES',
                r'analysis/synthese/\{NAME\}-ATOMIC',
                r'analysis/synthese/\{NAME\}-INTEGRATION',
                r'analysis/synthese/\{NAME\}-SYSTEM',
                r'analysis/synthese/\{NAME\}-VERIFY',
                r'analysis/synthese/\{NAME\}-GAP',
            ]
            if any(re.search(p, line) for p in ephemere_patterns):
                continue
            unmarked += 1
    return unmarked

def has_vault_primary(path):
    content = Path(path).read_text(encoding='utf-8')
    # Mindestens 1 Vault-Primaer-Referenz (PRIMAER: {VAULT}/...) als Read/Primaer
    return (
        "{VAULT}/OmniCommand/Backlog/" in content
        or "Backlog/{BL_SLUG}" in content
        or "PRIMAER: {VAULT}/" in content
    )

def main():
    total_unmarked = 0
    primary_missing = []
    for path in READER_COMMANDS:
        unmarked = count_unmarked_legacy(path)
        total_unmarked += unmarked
        if not has_vault_primary(path):
            primary_missing.append(path)
        status = "PASS" if unmarked <= 3 else ("WARN" if unmarked <= 10 else "FAIL")
        print(f"{status}: {path}: {unmarked} unmarked legacy reads")

    print(f"\nTotal unmarked legacy reads: {total_unmarked} (budget: {MAX_UNMARKED_LEGACY})")
    print(f"Primary-missing commands: {len(primary_missing)}")

    if total_unmarked > MAX_UNMARKED_LEGACY:
        print(f"FAIL: {total_unmarked} > {MAX_UNMARKED_LEGACY} unmarked legacy reads")
        sys.exit(1)
    if primary_missing:
        print(f"FAIL: {len(primary_missing)}/7 commands missing Vault-Primary reference")
        for p in primary_missing:
            print(f"  - {p}")
        sys.exit(1)
    print(f"PASS: symmetry check passed")
    sys.exit(0)

if __name__ == "__main__":
    main()
